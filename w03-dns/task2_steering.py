#!/usr/bin/env python3
"""Week 3 · Task 2 — Does DNS actually steer you? Measure it.

Textbook §2.4.3 (records) and §2.5 (CDNs).

The lecture claims two things:

    (a) most large sites are served by a CDN, reached through a CNAME chain
    (b) DNS steers each user to a *nearby* replica

Both are testable from your laptop, and one of them is harder to prove than
the slide makes it look. Your job is to produce the evidence and a number.

    python3 task2_steering.py --collect        # gather the raw data
    python3 task2_steering.py --report         # your analysis

What you have to build
----------------------
1.  For each hostname in SITES, follow the CNAME chain to its end and record
    every hop. `--collect` should leave the raw data in out/chains.json.

2.  Decide, for each site, whether it is served by a **third party**.
    This is the hard part and there is no single right answer:

      - `www.microsoft.com` ends at `akamaiedge.net`     - clearly third party
      - `www.netflix.com`   stops inside `netflix.com`   - own CDN, not third party
      - some sites have no CNAME at all and still sit behind a CDN (anycast)
      - `foo.cloudfront.net` and `foo.s3.amazonaws.com` are both Amazon,
        but they are not the same service

    Write down the rule you used and **defend it in observation.md**. A rule
    that just compares the last two labels will be wrong on at least one of
    the sites below; find which, and say so.

3.  Ask **two different resolvers** for the same name and compare the
    addresses you get back. If DNS really steers by location, a CDN-hosted
    name should answer differently to resolvers sitting in different places.

        RESOLVERS below has your system resolver and two public ones.

    Report: of N CDN-hosted sites, how many returned a different address set
    from a different resolver? Claim (b) predicts most of them. Check it.

Pass condition
--------------
There is no fixed answer. You pass by producing, in out/report.md:

  - the table: site | chain length | final zone | third party? | your rule's verdict
  - the steering number: "X of N sites answered differently to a different resolver"
  - at least one site where your classification rule was wrong, and why
"""
import argparse, json, os, subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dns_transport import normalize, query

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

SITES = [
    "www.microsoft.com",     # Akamai, multi-hop
    "www.netflix.com",       # own CDN
    "www.adobe.com",
    "www.cnn.com",
    "www.apple.com",
    "www.korea.ac.kr",       # no CDN at all
    "www.stanford.edu",
    "www.bbc.co.uk",
    "www.spotify.com",
    "www.github.com",
    "www.wikipedia.org",
    "www.nytimes.com",
]

RESOLVERS = {
    "system": None,          # whatever is in your resolv.conf
    "google": "8.8.8.8",
    "quad9":  "9.9.9.9",
}


def dig(name, rtype="A", server=None):
    """Raw lookup. Transport only - the thinking is yours."""
    result = query(name, server=server, rtype=rtype)
    if result["status"] != "NOERROR":
        raise RuntimeError(result["status"])
    return [rr["value"] for rr in result["answer"] if rr["type"] == rtype]


def collect(label):
    """Gather raw chains and per-resolver answers into out/chains.json.

    You write this. Roughly:
      for each site: follow CNAMEs to the end, then for each resolver in
      RESOLVERS record the A records it returns.
    """
    path = os.path.join(OUT, "chains.json")
    records = json.load(open(path)) if os.path.exists(path) else [
        {"site": site, "measurements": []} for site in SITES]
    by_site = {record["site"]: record for record in records}
    def measure(item):
        site, resolver = item
        chain, answers, responses = [site], [], []
        result = {"resolver": resolver, "server": RESOLVERS[resolver]}
        try:
            for _ in range(20):
                response = query(chain[-1], server=RESOLVERS[resolver])
                responses.append(response)
                if response["status"] != "NOERROR":
                    raise RuntimeError(response["status"])
                aliases = {rr["name"]: rr["value"] for rr in response["answer"]
                           if rr["type"] == "CNAME"}
                while chain[-1] in aliases:
                    target = aliases[chain[-1]]
                    if target in chain:
                        raise RuntimeError("CNAME cycle")
                    chain.append(target)
                    if len(chain) > 20:
                        raise RuntimeError("CNAME depth limit")
                answers = sorted({rr["value"] for rr in response["answer"]
                                  if rr["name"] == chain[-1] and rr["type"] == "A"})
                if answers:
                    break
                if chain[-1] not in [rr["value"] for rr in response["answer"]
                                      if rr["type"] == "CNAME"]:
                    raise RuntimeError("no A record")
            else:
                raise RuntimeError("query limit")
        except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
            result["error"] = str(exc)
        result.update(chain=chain, addresses=answers, responses=responses)
        return site, resolver, result
    measured = {site: {} for site in SITES}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for site, resolver, result in pool.map(measure, [
            (site, resolver) for site in SITES for resolver in RESOLVERS]):
            measured[site][resolver] = result
            print(site, resolver, result.get("error", result["addresses"]), flush=True)
    timestamp = datetime.now().astimezone().isoformat()
    for site in SITES:
        by_site[site]["measurements"].append(
            {"network": label, "when": timestamp, "resolvers": measured[site]})
    with open(path, "w") as file:
        json.dump(records, file, indent=2)
        file.write("\n")


CDN_SUFFIXES = ("akamaiedge.net", "edgekey.net", "edgesuite.net", "akamai.net",
                "akamaitech.net", "fastly.net", "netlifyglobalcdn.com", "cloudfront.net")


def suffix(name):
    # Deliberately naive rule, evaluated against ownership below.
    return ".".join(name.split(".")[-2:])


def classify(site, chain):
    if any(host == domain or host.endswith("." + domain)
           for host in chain for domain in CDN_SUFFIXES):
        return "third-party CDN (hostname evidence)", True
    if site.endswith("wikipedia.org") and chain[-1].endswith("wikimedia.org"):
        return "same operator: Wikimedia", False
    if site.endswith("netflix.com"):
        return "own-domain service; course identifies own CDN", False
    return "no third-party CNAME evidence; CDN status unknown", False


def report():
    """Read out/chains.json and produce out/report.md.

    You write this too - including the classification rule that decides
    whether a site is on a third-party CDN.
    """
    records = json.load(open(os.path.join(OUT, "chains.json")))
    networks = sorted({m["network"] for r in records for m in r["measurements"]})
    lines = [
        "# Lab 3 · DNS steering report", "",
        "Measured networks: " + ", ".join(networks) + ".",
        "INCOMPLETE: second-network comparison remains pending." if len(networks) < 2
        else "Two or more network labels recorded; verify they represent distinct real networks.",
        "",
        "## Rule and scope",
        "The naive rule flags a third party when the last two labels differ. "
        "The revised rule recognizes provider hostname suffixes and the known "
        "Wikipedia/Wikimedia ownership relationship; other cases remain uncertain. "
        "No CNAME is not proof of no CDN. Final zone below means a displayed "
        "hostname suffix, not a measured SOA zone or Public Suffix List result.",
        "",
        "Wikipedia is a concrete false positive: wikipedia.org → wikimedia.org "
        "changes the suffix but not the operator. [Wikimedia Foundation](https://wikimediafoundation.org/who-we-are/) "
        "identifies itself as Wikipedia's operator. co.uk/ac.kr also show why "
        "two-label splitting is not general registrable-domain parsing.",
        "",
        "## Per-site table (latest measurement per site; system resolver chain)",
        "| Site | Network | Chain length (CNAME edges) | Final zone/suffix | Naive third party? | Revised verdict | Resolver address sets differ? |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    changed = eligible = cdn_changed = cdn_eligible = 0
    all_cdn_sets, all_site_sets = {}, {}
    for record in records:
        site = record["site"]
        latest = record["measurements"][-1]
        result = latest["resolvers"]["system"]
        chain = result["chain"]
        verdict, cdn = classify(site, chain)
        valid = [tuple(r["addresses"]) for r in latest["resolvers"].values()
                 if not r.get("error") and r["addresses"]]
        differs = len(set(valid)) > 1
        if len(valid) >= 2:
            eligible += 1
            changed += differs
            if cdn:
                cdn_eligible += 1
                cdn_changed += differs
        lines.append(f"| {site} | {latest['network']} | {len(chain)-1} | {suffix(chain[-1])} | "
                     f"{suffix(site) != suffix(chain[-1])} | {verdict} | "
                     f"{differs if len(valid) >= 2 else 'insufficient responses'} |")
        for measurement in record["measurements"]:
            for answer in measurement["resolvers"].values():
                if not answer.get("error") and answer["addresses"]:
                    value = tuple(answer["addresses"])
                    all_site_sets.setdefault(site, []).append(value)
                    if classify(site, answer["chain"])[1]:
                        all_cdn_sets.setdefault(site, []).append(value)
    lines += [
        "", "## Resolver steering counts",
        f"Latest per-site measurements: {changed} of {eligible} sites returned different IPv4 "
        f"sets across resolvers. In the explicitly identified third-party CDN subset: "
        f"**{cdn_changed} of {cdn_eligible}**.",
        "CDN denominator uses the provider signatures above; Netflix's own CDN "
        "is excluded from this narrower subset. This is not a claim that other sites have no CDN.",
        "Resolvers: system, Google 8.8.8.8, Quad9 9.9.9.9. Public resolver names/IPs "
        "do not establish geographic distance: anycast may place them nearby. "
        "Different sets support resolver-dependent selection, but cache age, rotation and time "
        "can also explain differences. They do not prove the selected replica is nearer. "
        "No second-network result is inferred from these three resolvers.",
        "", "## Raw measurement evidence",
        "Every collected CNAME hop, A-address set, parsed response, network label and "
        "timestamp is preserved in chains.json; collection appends measurements rather than replacing them.",
        "Fastly documents map.fastly.net in its [routing documentation]"
        "(https://www.fastly.com/documentation/guides/concepts/routing-traffic-to-fastly/). "
        "Other provider suffix classifications are hostname-based evidence, not an independent IP-ownership audit.",
    ]
    if len(networks) >= 2:
        pool = [values for values in all_cdn_sets.values() if len(values) >= 2]
        lines += ["", f"Across all recorded networks/resolvers: {sum(len(set(v)) > 1 for v in pool)} "
                  f"of {len(pool)} provider-signature CDN sites differed (includes temporal variation)."]
    capture = os.path.join(OUT, "capture-analysis.md")
    if os.path.exists(capture):
        lines += ["", open(capture).read()]
    with open(os.path.join(OUT, "report.md"), "w") as file:
        file.write("\n".join(lines) + "\n")
    print(f"all sites {changed}/{eligible}; third-party CDN subset {cdn_changed}/{cdn_eligible}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--collect", action="store_true")
    p.add_argument("--report", action="store_true")
    p.add_argument("--label", default="Network A")
    a = p.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.collect:
        collect(a.label)
    elif a.report:
        report()
    else:
        p.print_help()
