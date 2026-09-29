# Lab 5 · Address study

Status: INCOMPLETE — a second real network measurement and comparison are still required.

## Part A · Network A (2026-09-29)

Collected using `python3 task2_myaddr.py --collect "Network A"` on the Mac, not inside Docker. Network labels are anonymized. Published JSON retains relevant raw output excerpts; unrelated interface, MAC/IPv6 and DNS metadata are omitted. Unabridged output remains local and uncommitted.

| Item | Observed value |
| --- | --- |
| Interface | en0 |
| IPv4 | 172.16.[masked].109 |
| Mask | 0xffffff00 = 255.255.255.0 = /24 |
| Default gateway | 172.16.[masked].1 |
| Public IPv4 (api.ipify.org) | [public-IP-A] |

### A2 · Manual subnet calculation, then code verification

The mask fixes the first 24 bits and leaves 8 host bits: 2^8 = 256 total addresses. In the last octet, 109 AND 0 = 0, so the network is 172.16.[masked].0/24. Setting all 8 host bits gives broadcast 172.16.[masked].255. Excluding network and broadcast leaves usable addresses 172.16.[masked].1–172.16.[masked].254 (254 hosts).

`network_range("172.16.[masked].0/24")` returned `('172.16.[masked].1', '172.16.[masked].254', '172.16.[masked].255')`, agreeing with this derivation. 

### A3 · Gateway

172.16.[masked].1 lies inside the usable range. On this ordinary Ethernet/Wi-Fi subnet the gateway must be reachable on-link so the host can resolve its MAC address and send off-subnet packets to it. Point-to-point links and explicit on-link routes are exceptions to the general same-subnet rule.

### A4–A5 · Public address and NAT evidence

172.16.[masked].109 belongs to RFC 1918's 172.16.0.0/12 private range. The external IPv4 service returned [public-IP-A], a different, non-private address. Under normal direct IPv4 access this demonstrates at least one NAT stage; these two endpoints alone do not establish whether there is one NAT or multiple stages. Proxy/VPN routing is another reason not to infer an exact count from address differences alone.

To distinguish one versus two NATs, inspect the first router's WAN address and upstream translation configuration: a private/shared WAN address plus a further upstream NAT is evidence of an additional stage. Traceroute alone is not a reliable NAT counter. A 100.64.0.0/10 address indicates shared address space associated with CGN, not by itself proof of exactly two NAT stages.

## Part B · Second network — pending

Only one network has been measured. After the user connects this Mac to a hotspot or another real network, collect the second record, derive its range, check its gateway, and compare private IP, mask, gateway and public IP. No second label or fabricated measurement has been added.

## Part C · Official DHCP trace (path B)

Local capture was attempted with `dumpcap -i en0 -f 'udp port 67 or udp port 68'`; macOS rejected access to `/dev/bpf0` (permission denied). Therefore this section uses the permitted official trace, not a capture of the student's network.

Source archive: https://www-net.cs.umass.edu/wireshark-labs/wireshark-traces-9e.zip

Member: `dhcp-wireshark-trace1-1.pcapng`. `out/dhcp.pcapng` contains only its six DHCP packets, selected with `tshark -Y dhcp`; unrelated traffic is excluded. All six share transaction ID `0x56f415ed`.

| Original frames | Message | Source → destination |
| --- | --- | --- |
| 5, 9 | Discover | 0.0.0.0 → 255.255.255.255 |
| 12, 13 | Offer | 192.168.86.1 → 192.168.86.65 |
| 16 | Request | 0.0.0.0 → 255.255.255.255 |
| 17 | Ack | 192.168.86.1 → 192.168.86.65 |

### C2 · Discover addresses

The client has no assigned IPv4 address yet, so its IPv4 source is 0.0.0.0. It does not yet know a DHCP server's address and broadcasts to 255.255.255.255 to reach servers on the local link (or a relay).

### C3 · Server lease and renewal

Offer and Ack specify option 51 = 86400 seconds (24 hours). The Discover contains the client's requested 7776000 seconds, which is not the lease granted by the server. Option 58 gives T1 = 43200 seconds (12 hours); at this halfway point the client normally enters RENEWING and unicasts DHCPREQUEST to the original server. Option 59 gives T2 = 75600 seconds (21 hours), when an unanswered renewal moves to broadcast rebinding. If the lease expires without renewal, the client must stop using the leased address.

### C4 · Why Ack can be unicast

The trace's Ack is sent to the offered address 192.168.86.65. By then the server knows the selected address and client's link-layer address, allowing unicast delivery if the client can receive it before configuration completes. This does not imply that a client can use an arbitrary offered address before Ack; clients needing broadcast delivery signal it with the broadcast flag. Even the Offer is unicast in this trace.

### Attribution

Wireshark lab trace files from J.F. Kurose and K.W. Ross,
*Computer Networking: A Top-Down Approach*, 9th ed.
https://gaia.cs.umass.edu/kurose_ross/
Copyright 1996-2025 J.F. Kurose, K.W. Ross. All Rights Reserved.
