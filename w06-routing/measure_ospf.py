#!/usr/bin/env python3
"""Measure actual FRR routes, not display ages. Run via scenario.sh measure.

All mutations are confined to the three Compose lab routers. Address/interface
mapping is discovered, and all six remote loopback routes must match before an
event is declared converged. Raw snapshots and polling evidence go to out/.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "w06-routing" / "out"
DC = ["docker", "compose", "--profile", "routing"]
ROUTERS = ("r1", "r2", "r3")
PREFIX = {r: f"10.255.0.{i}/32" for i, r in enumerate(ROUTERS, 1)}


def command(args):
    return subprocess.run(args, cwd=ROOT, check=True, text=True,
                          capture_output=True, timeout=15).stdout


def execute(router, *args):
    return command(DC + ["exec", "-T", router, *args])


def vty(router, *commands):
    args = ["vtysh"]
    for cmd in commands:
        args += ["-c", cmd]
    return execute(router, *args)


def parallel(fn):
    with ThreadPoolExecutor(max_workers=3) as pool:
        return dict(zip(ROUTERS, pool.map(fn, ROUTERS)))


def discover():
    addresses = parallel(lambda r: json.loads(execute(r, "ip", "-j", "-4", "addr")))
    interfaces = {}
    for router, entries in addresses.items():
        interfaces[router] = {}
        for entry in entries:
            if entry["ifname"] == "lo":
                continue
            for addr in entry["addr_info"]:
                network = str(ipaddress.ip_interface(
                    f"{addr['local']}/{addr['prefixlen']}").network)
                interfaces[router][network] = (entry["ifname"], addr["local"])
    links = {}
    for a in ROUTERS:
        for b in ROUTERS:
            if a == b:
                continue
            shared = set(interfaces[a]) & set(interfaces[b])
            if len(shared) != 1:
                raise RuntimeError(f"Expected one shared subnet for {a}-{b}: {shared}")
            network = shared.pop()
            links[a, b] = {"interface": interfaces[a][network][0],
                           "gateway": interfaces[b][network][1]}
    return links


def routes():
    return parallel(lambda r: json.loads(vty(r, "show ip route ospf json")))


def expected(links, event="normal"):
    result = {}
    for a in ROUTERS:
        result[a] = {}
        for b in ROUTERS:
            if a == b:
                continue
            via, metric = b, 10
            if event == "cut" and {a, b} == {"r1", "r2"}:
                via, metric = "r3", 20
            if event == "cost" and (a, b) == ("r1", "r3"):
                via, metric = "r2", 20
            result[a][PREFIX[b]] = {**links[a, via], "metric": metric}
    return result


def matches(tables, target):
    for router, destinations in target.items():
        for prefix, want in destinations.items():
            records = tables[router].get(prefix, [])
            active = [r for r in records if r.get("selected")
                      and r.get("metric") == want["metric"]]
            installed = {(h.get("ip"), h.get("interfaceName"))
                         for r in active for h in r.get("nexthops", [])
                         if h.get("fib") and h.get("active")}
            if installed != {(want["gateway"], want["interface"])}:
                return False
    return True


def compact(tables):
    return {r: {p: [{"metric": e["metric"], "selected": e.get("selected", False),
                     "nexthops": [{k: h.get(k) for k in
                                   ("ip", "interfaceName", "active", "fib")}
                                  for h in e.get("nexthops", [])]}
                    for e in entries]
                for p, entries in table.items() if p in PREFIX.values()}
            for r, table in tables.items()}


def await_routes(target, start=None, timeout=100):
    start = time.monotonic() if start is None else start
    samples, consecutive, first_match = [], 0, None
    while time.monotonic() - start < timeout:
        tables = routes()
        elapsed = time.monotonic() - start
        ok = matches(tables, target)
        samples.append({"seconds": round(elapsed, 6), "matches": ok,
                        "routes": compact(tables)})
        if ok:
            if not consecutive:
                first_match = elapsed
            consecutive += 1
            if consecutive == 2:
                return {"first_match_seconds": round(first_match, 6),
                        "confirmed_seconds": round(elapsed, 6),
                        "expected": target, "samples": samples}
        else:
            consecutive, first_match = 0, None
        time.sleep(0.5)
    raise RuntimeError("Routes failed to converge: " + json.dumps(samples[-1]))


def snapshot(name):
    text = "".join(f"===== {r} =====\n" + vty(r, "show ip route ospf",
                   "show ip ospf neighbor", "show ip ospf interface") + "\n"
                   for r in ROUTERS)
    (OUT / name).write_text(text.rstrip() + "\n", encoding="utf-8")


def cost(links, value):
    vty("r1", "configure terminal", f"interface {links['r1', 'r3']['interface']}",
        f"ip ospf cost {value}")


def physical(links, state):
    execute("r1", "ip", "link", "set", links["r1", "r2"]["interface"], state)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("wait", "routes", "measure",
                                          "cut", "restore", "cost"))
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    if args.action == "routes":
        for router in ROUTERS:
            print(f"===== {router} =====\n" + vty(router, "show ip route ospf"))
        return
    links = discover()
    if args.action in ("cut", "restore", "cost"):
        before = "cut" if args.action == "restore" else "normal"
        await_routes(expected(links, before))
        names = {"cut": ("route-before.txt", "route-after.txt"),
                 "restore": ("route-restore-before.txt", "route-restored.txt"),
                 "cost": ("route-cost-before.txt", "route-cost-after.txt")}
        first, last = names[args.action]
        snapshot(first)
        start = time.monotonic()
        if args.action == "cost":
            cost(links, 100)
        else:
            physical(links, "down" if args.action == "cut" else "up")
        after = {"cut": "cut", "restore": "normal", "cost": "cost"}[args.action]
        result = await_routes(expected(links, after), start)
        snapshot(last)
        (OUT / f"ospf-{args.action}.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
        line = (f"{args.action}: first_correct={result['first_match_seconds']:.6f}s "
                f"confirmed={result['confirmed_seconds']:.6f}s\n")
        with (OUT / "reconverge.txt").open("a", encoding="utf-8") as output:
            output.write(line)
        print(line, end="")
        return
    print("Waiting for all six remote loopback routes...", flush=True)
    await_routes(expected(links))
    if args.action == "wait":
        print("All routers converged.")
        return
    results = {"method": "monotonic wall time before mutation; 0.5s polling plus Docker "
               "overhead; six selected FIB routes must match twice; single trial",
               "links": {f"{a}-{b}": v for (a, b), v in links.items()}, "events": {}}
    snapshot("route-before.txt")

    def event(name, mutate, target, filename):
        print(f"Starting {name}...", flush=True)
        start = time.monotonic()
        mutate()
        result = await_routes(target, start)
        results["events"][name] = result
        (OUT / "ospf-measurements.json").write_text(
            json.dumps(results, indent=2) + "\n", encoding="utf-8")
        snapshot(filename)
        print(f"{name}: first correct {result['first_match_seconds']:.3f}s, "
              f"confirmed {result['confirmed_seconds']:.3f}s", flush=True)

    dropped = []
    try:
        event("interface_down", lambda: physical(links, "down"),
              expected(links, "cut"), "route-after.txt")
        event("interface_restore", lambda: physical(links, "up"),
              expected(links), "route-restored.txt")
        snapshot("route-cost-before.txt")
        event("cost_10_to_100", lambda: cost(links, 100),
              expected(links, "cost"), "route-cost-after.txt")
        cost(links, 10)
        await_routes(expected(links))
        snapshot("route-silent-before.txt")

        def silence():
            for a, b in (("r1", "r2"), ("r2", "r1")):
                iface = links[a, b]["interface"]
                # add fails rather than replacing any pre-existing root qdisc.
                execute(a, "tc", "qdisc", "add", "dev", iface,
                        "root", "netem", "loss", "100%")
                dropped.append((a, iface))

        def unsilence():
            while dropped:
                a, iface = dropped[-1]
                execute(a, "tc", "qdisc", "del", "dev", iface, "root")
                dropped.pop()

        event("silent_packet_loss", silence, expected(links, "cut"),
              "route-silent-after.txt")
        event("silent_restore", unsilence, expected(links),
              "route-silent-restored.txt")
    finally:
        for a, iface in reversed(dropped):
            execute(a, "tc", "qdisc", "del", "dev", iface, "root")
        physical(links, "up")
        cost(links, 10)

    lines = [results["method"],
             "Hello=10s, Dead=40s, Wait=40s (raw interface output in route snapshots).",
             "Timing begins before Docker mutation commands; includes command/poll overhead.",
             "first_match is an upper bound on when the six routes became correct, not an exact outage.",
             "The three routers' JSON queries are concurrent, not an atomic network snapshot.",
             "No packet-delivery outage duration was measured; these are routing/FIB observations.",
             "interface_down: only r1's r1-r2 interface is administratively down.",
             "silent_packet_loss: tc netem drops 100% of egress on BOTH r1-r2 endpoints; carrier stays up.",
             "cost_10_to_100: only r1's r1-r3 outgoing OSPF cost is raised.", ""]
    for name, result in results["events"].items():
        lines.append(f"{name}: first_correct={result['first_match_seconds']:.6f}s "
                     f"confirmed={result['confirmed_seconds']:.6f}s")
    (OUT / "reconverge.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("All five experiments recorded; lab interfaces and costs restored.")


if __name__ == "__main__":
    main()
