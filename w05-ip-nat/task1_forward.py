#!/usr/bin/env python3
"""Week 5 · Task 1 — Subnets and longest-prefix match.

Textbook §4.3.2 (IPv4 addressing, CIDR) and §4.3.3 (forwarding).

Two things a router does with every packet: work out which prefixes the
destination falls inside, and pick the longest one. The second is the whole
of "longest prefix match", and it is the reason the internet's routing table
can hold a million entries and still be answerable.

You build both, from integers up. No `ipaddress` module - that library is
exactly the thing you are supposed to understand this week.

    python3 task1_forward.py --verify
"""
import argparse


def ipv4_int(address):
    """Convert dotted decimal to an unsigned 32-bit integer."""
    parts = address.split(".")
    if len(parts) != 4:
        raise ValueError("IPv4 requires four octets")
    result = 0
    for part in parts:
        if not part.isascii() or not part.isdecimal() or not 0 <= int(part) <= 255:
            raise ValueError("invalid IPv4 octet")
        result = (result << 8) | int(part)
    return result


def ipv4_text(address):
    return ".".join(str((address >> shift) & 255) for shift in (24, 16, 8, 0))


def prefix_mask(length):
    return (0xFFFFFFFF << (32 - length)) & 0xFFFFFFFF


def parse_cidr(cidr):
    """'163.152.6.0/24' -> (network as int, prefix length).

    Requirements: reject a prefix length outside 0-32, and reject an address
    whose host bits are set when they should not be (163.152.6.5/24 is a
    common way to write a host, but it is not a network).
    """
    address, length = cidr.split("/")
    if not length.isascii() or not length.isdecimal() or not 0 <= int(length) <= 32:
        raise ValueError("prefix length must be 0 through 32")
    length = int(length)
    network = ipv4_int(address)
    if network & prefix_mask(length) != network:
        raise ValueError("network address has host bits set")
    return network, length


def network_range(cidr):
    """'163.152.6.0/24' -> (first usable, last usable, broadcast) as strings.

    Careful at the edges. /31 and /32 do not have a usable host range in the
    ordinary sense - decide what you return and say so in observation.md.
    """
    network, length = parse_cidr(cidr)
    last = network | (0xFFFFFFFF ^ prefix_mask(length))
    # /31: both endpoints usable; /32: the single host. The third value
    # remains the numerical block end, not a directed broadcast on /31-/32.
    first_usable, last_usable = (network, last) if length >= 31 else (network + 1, last - 1)
    return tuple(ipv4_text(value) for value in (first_usable, last_usable, last))


class ForwardingTable:
    """Longest-prefix-match forwarding.

    add(cidr, next_hop)  ·  lookup(address) -> next_hop or None

    The default route 0.0.0.0/0 matches everything and is the shortest prefix,
    so it must lose to any other match. If two entries have the same prefix
    length, the table is malformed - say what you do.
    """

    def __init__(self):
        self.entries = []

    def add(self, cidr, next_hop):
        network, length = parse_cidr(cidr)
        self.entries.append((network, length, next_hop))

    def lookup(self, address):
        address = ipv4_int(address)
        best_length, best_hop = -1, None
        for network, length, hop in self.entries:
            if address & prefix_mask(length) == network and length > best_length:
                best_length, best_hop = length, hop
        # Strict comparison keeps the first inserted route on an exact tie.
        return best_hop


# ------------------------------------------------------------------- harness
RANGE_CASES = [
    ("192.168.0.0/24",  "192.168.0.1",   "192.168.0.254",  "192.168.0.255"),
    ("10.0.0.0/8",      "10.0.0.1",      "10.255.255.254", "10.255.255.255"),
    ("172.16.32.0/20",  "172.16.32.1",   "172.16.47.254",  "172.16.47.255"),
    ("203.0.113.64/26", "203.0.113.65",  "203.0.113.126",  "203.0.113.127"),
]

TABLE = [
    ("0.0.0.0/0",       "default-gw"),
    ("10.0.0.0/8",      "campus"),
    ("10.20.0.0/16",    "eng-building"),
    ("10.20.30.0/24",   "lab-floor"),
    ("10.20.30.64/26",  "lab-rack-2"),
    ("192.168.1.0/24",  "home"),
]

LOOKUP_CASES = [
    ("10.20.30.70",   "lab-rack-2"),     # inside all four 10.x entries
    ("10.20.30.10",   "lab-floor"),
    ("10.20.99.1",    "eng-building"),
    ("10.99.0.1",     "campus"),
    ("8.8.8.8",       "default-gw"),
    ("192.168.1.77",  "home"),
]


def verify():
    fails = 0
    for cidr, first, last, bcast in RANGE_CASES:
        try:
            got = network_range(cidr)
        except NotImplementedError:
            print("  network_range is still a stub"); return 1
        except Exception as e:
            print(f"  FAIL  {cidr:<18} raised {e!r}"); fails += 1; continue
        ok = tuple(got) == (first, last, bcast)
        print(f"  {'ok  ' if ok else 'FAIL'}  {cidr:<18} {got}")
        fails += not ok

    t = ForwardingTable()
    try:
        for cidr, hop in TABLE:
            t.add(cidr, hop)
    except NotImplementedError:
        print("  ForwardingTable is still a stub"); return 1

    for addr, expect in LOOKUP_CASES:
        got = t.lookup(addr)
        ok = got == expect
        print(f"  {'ok  ' if ok else 'FAIL'}  {addr:<16} -> {got}  (want {expect})")
        fails += not ok

    print(f"\n  {len(RANGE_CASES) + len(LOOKUP_CASES) - fails}"
          f"/{len(RANGE_CASES) + len(LOOKUP_CASES)} ok")
    return 1 if fails else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    raise SystemExit(verify() if a.verify else p.print_help())
