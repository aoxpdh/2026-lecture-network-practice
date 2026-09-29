#!/usr/bin/env python3
"""Week 3 · Task 1 — Build your own iterative resolver.

Textbook §2.4.2 - §2.4.3.

`dig +trace` walks root -> TLD -> authoritative for you. In this task you do
that walk yourself: start at a root server, read the delegation it returns,
ask the next server, and keep going until somebody answers authoritatively.

You may shell out to `dig` for the transport, or use a DNS library
(`dnspython` is in the container). Either is fine - what matters is that
*you* follow the delegations rather than letting a tool do it.

    python3 task1_resolve.py www.korea.ac.kr
    python3 task1_resolve.py --verify        # check yourself against dig

Pass condition
--------------
`--verify` resolves five names with your resolver and with `dig`, and the
addresses must agree. A name behind a CDN may legitimately return a different
address each time; the harness compares the *set of authoritative nameservers*
you ended at for those, not the address.
"""
import argparse, subprocess, sys
from dns_transport import normalize, query

# Root servers. Everything starts here; there is no earlier step.
ROOT_SERVERS = [
    "198.41.0.4",       # a.root-servers.net
    "199.9.14.201",     # b.root-servers.net
    "192.33.4.12",      # c.root-servers.net
]

# (name, kind).  "stable" names must match dig exactly.  "cdn" names are served
# from many replicas and may legitimately give you a different address than dig
# got a second earlier - for those we only require that you reached an answer.
VERIFY_NAMES = [
    ("www.korea.ac.kr", "stable"),
    ("dns.google", "stable"),
    ("en.wikipedia.org", "stable"),
    ("www.stanford.edu", "stable"),
    ("www.microsoft.com", "cdn"),
]


class Resolver:
    """Your iterative resolver.

    The whole point is that you never ask a server to recurse for you.
    You ask one server, it says "not mine, ask over there", and you go there.

    Suggested shape - but it is yours to design:

        resolve(name) -> (address, path)
            address : the A record you ended up with, as a string
            path    : the servers you asked, in order, so you can show your work

    Things you will hit, in roughly this order:

    1.  A delegation gives you NS *names*, sometimes with glue A records and
        sometimes without. No glue means you have to resolve that nameserver's
        name first - which is another walk. Decide what you do there.
    2.  A server may not answer. Try the next one rather than giving up.
    3.  CNAMEs. The answer you get back may be a different name than the one
        you asked for, and you have to start again with that name.
    4.  Loops. Cap your depth.

    If you shell out to dig, the flag you want is `+norecurse`, so that the
    server you ask replies with a delegation instead of doing the work:

        dig @198.41.0.4 www.korea.ac.kr +norecurse
    """

    def __init__(self, transport=query, max_depth=24, max_queries=100):
        self.transport = transport
        self.max_depth, self.max_queries = max_depth, max_queries

    def resolve(self, name):
        self.path, self.events, self.visited = [], [], set()
        address = self._walk(normalize(name), ROOT_SERVERS, 0, set())
        return address, self.path

    def _walk(self, name, servers, depth, active):
        if depth >= self.max_depth or len(self.path) >= self.max_queries:
            raise RuntimeError("DNS walk depth/query limit reached")
        errors = []
        for server in servers:
            if (name, server) in self.visited:
                continue
            if len(self.path) >= self.max_queries:
                raise RuntimeError("DNS query budget exhausted")
            self.visited.add((name, server))
            self.path.append(server)
            event = {"name": name, "server": server}
            self.events.append(event)
            try:
                response = self.transport(name, server=server, recursive=False)
                event["response"] = response
                if response["status"] != "NOERROR":
                    raise RuntimeError(response["status"])
                if response["aa"]:
                    for rr in response["answer"]:
                        if rr["name"] == name and rr["type"] == "A":
                            return rr["value"]
                    for rr in response["answer"]:
                        if rr["name"] == name and rr["type"] == "CNAME":
                            target = rr["value"]
                            if target in active | {name}:
                                raise RuntimeError("CNAME loop")
                            return self._walk(target, ROOT_SERVERS, depth + 1, active | {name})
                referrals = [rr for rr in response["authority"] if rr["type"] == "NS"
                             and (name == rr["name"] or name.endswith("." + rr["name"]))]
                if not referrals:
                    raise RuntimeError("no authoritative A/CNAME or delegation")
                zone = max((rr["name"] for rr in referrals), key=len)
                names = list(dict.fromkeys(rr["value"] for rr in referrals if rr["name"] == zone))
                # Use only additional A records naming the referred NS.
                # Root referrals include cross-TLD glue (e.g. com -> *.net).
                # This educational resolver does not implement DNSSEC validation.
                glued = {}
                for rr in response["additional"]:
                    if rr["type"] == "A" and rr["name"] in names:
                        glued.setdefault(rr["name"], []).append(rr["value"])
                addresses = [ip for ns in names for ip in glued.get(ns, [])]
                if addresses:
                    try:
                        return self._walk(name, addresses, depth + 1, active)
                    except RuntimeError as exc:
                        errors.append(str(exc))
                for ns in names:
                    if ns in glued or ns in active | {name}:
                        continue
                    try:
                        ip = self._walk(ns, ROOT_SERVERS, depth + 1, active | {name})
                        return self._walk(name, [ip], depth + 1, active)
                    except RuntimeError as exc:
                        errors.append(str(exc))
                raise RuntimeError("delegated servers exhausted")
            except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
                event["error"] = str(exc)
                errors.append(str(exc))
        raise RuntimeError(f"resolution failed for {name}: " + "; ".join(errors[-3:]))


# ------------------------------------------------------------------- harness
def dig_answer(name):
    """What the system resolver says, for comparison."""
    out = subprocess.run(["dig", "+short", name, "A"],
                         capture_output=True, text=True).stdout
    return [l for l in out.split() if l and l[0].isdigit()]


def verify():
    r, failures = Resolver(), 0
    for name, kind in VERIFY_NAMES:
        try:
            addr, path = r.resolve(name)
        except NotImplementedError:
            print("Nothing implemented yet - write Resolver.resolve first.")
            return 1
        except Exception as e:
            print(f"  FAIL  {name:<22} your resolver raised {e!r}")
            failures += 1
            continue
        expected = dig_answer(name)
        if addr in expected:
            note = ""
        elif kind == "cdn":
            note = "  <- differs, but this name is CDN-hosted. Explain it."
        else:
            note = "  <- should have matched"
            failures += 1
        print(f"  {'FAIL' if note.endswith('matched') else 'ok  '}  {name:<22} "
              f"you={addr:<16} dig={','.join(expected) or '-'}   "
              f"hops={len(path)}{note}")
    print(f"\n  {len(VERIFY_NAMES) - failures}/{len(VERIFY_NAMES)} ok")
    return 1 if failures else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name", nargs="?", default="www.korea.ac.kr")
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()

    if a.verify:
        sys.exit(verify())

    addr, path = Resolver().resolve(a.name)
    for i, server in enumerate(path, 1):
        print(f"  {i}. asked {server}")
    print(f"\n  {a.name} -> {addr}")


if __name__ == "__main__":
    main()
