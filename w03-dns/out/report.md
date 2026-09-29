# Lab 3 · DNS steering report

Privacy: network labels and precise timestamps are anonymized in the published measurement data.
Measured networks: Network A, Network B (hotspot).
Two or more network labels recorded; verify they represent distinct real networks.

## Rule and scope
The naive rule flags a third party when the last two labels differ. The revised rule recognizes provider hostname suffixes and the known Wikipedia/Wikimedia ownership relationship; other cases remain uncertain. No CNAME is not proof of no CDN. Final zone below means a displayed hostname suffix, not a measured SOA zone or Public Suffix List result.

Wikipedia is a concrete false positive: wikipedia.org → wikimedia.org changes the suffix but not the operator. [Wikimedia Foundation](https://wikimediafoundation.org/who-we-are/) identifies itself as Wikipedia's operator. co.uk/ac.kr also show why two-label splitting is not general registrable-domain parsing.

## Per-site table (latest measurement per site; system resolver chain)
| Site | Network | Chain length (CNAME edges) | Final zone/suffix | Naive third party? | Revised verdict | Resolver address sets differ? |
| --- | --- | --- | --- | --- | --- | --- |
| www.microsoft.com | Network B (hotspot) | 2 | akamaiedge.net | True | third-party CDN (hostname evidence) | True |
| www.netflix.com | Network B (hotspot) | 1 | netflix.com | False | own-domain service; course identifies own CDN | False |
| www.adobe.com | Network B (hotspot) | 2 | akamai.net | True | third-party CDN (hostname evidence) | True |
| www.cnn.com | Network B (hotspot) | 1 | fastly.net | True | third-party CDN (hostname evidence) | True |
| www.apple.com | Network B (hotspot) | 3 | akamaiedge.net | True | third-party CDN (hostname evidence) | True |
| www.korea.ac.kr | Network B (hotspot) | 0 | ac.kr | False | no third-party CNAME evidence; CDN status unknown | False |
| www.stanford.edu | Network B (hotspot) | 1 | netlifyglobalcdn.com | True | third-party CDN (hostname evidence) | False |
| www.bbc.co.uk | Network B (hotspot) | 2 | fastly.net | True | third-party CDN (hostname evidence) | True |
| www.spotify.com | Network B (hotspot) | 1 | fastly.net | True | third-party CDN (hostname evidence) | True |
| www.github.com | Network B (hotspot) | 1 | github.com | False | no third-party CNAME evidence; CDN status unknown | True |
| www.wikipedia.org | Network B (hotspot) | 1 | wikimedia.org | True | same operator: Wikimedia | False |
| www.nytimes.com | Network B (hotspot) | 3 | fastly.net | True | third-party CDN (hostname evidence) | True |

## Resolver steering counts
Latest per-site measurements: 8 of 12 sites returned different IPv4 sets across resolvers. In the explicitly identified third-party CDN subset: **7 of 8**.
CDN denominator uses the provider signatures above; Netflix's own CDN is excluded from this narrower subset. This is not a claim that other sites have no CDN.
Resolvers: system, Google 8.8.8.8, Quad9 9.9.9.9. Public resolver names/IPs do not establish geographic distance: anycast may place them nearby. Different sets support resolver-dependent selection, but cache age, rotation and time can also explain differences. They do not prove the selected replica is nearer. No second-network result is inferred from these three resolvers.

## Raw measurement evidence
Every collected CNAME hop, A-address set, parsed response, network label and timestamp is preserved in chains.json; collection appends measurements rather than replacing them.
Fastly documents map.fastly.net in its [routing documentation](https://www.fastly.com/documentation/guides/concepts/routing-traffic-to-fastly/). Other provider suffix classifications are hostname-based evidence, not an independent IP-ownership audit.

Across all recorded networks/resolvers: 7 of 8 provider-signature CDN sites differed (includes temporal variation).

## Same-resolver comparison between first and last networks
| Site | First network | Last network | Resolvers with changed A sets |
| --- | --- | --- | --- |
| www.microsoft.com | Network A | Network B (hotspot) | google, quad9 |
| www.netflix.com | Network A | Network B (hotspot) | none |
| www.adobe.com | Network A | Network B (hotspot) | system, google, quad9 |
| www.cnn.com | Network A | Network B (hotspot) | none |
| www.apple.com | Network A | Network B (hotspot) | google, quad9 |
| www.korea.ac.kr | Network A | Network B (hotspot) | none |
| www.stanford.edu | Network A | Network B (hotspot) | none |
| www.bbc.co.uk | Network A | Network B (hotspot) | none |
| www.spotify.com | Network A | Network B (hotspot) | none |
| www.github.com | Network A | Network B (hotspot) | none |
| www.wikipedia.org | Network A | Network B (hotspot) | none |
| www.nytimes.com | Network A | Network B (hotspot) | none |
Among the provider-signature CDN subset, 3/8 changed across networks with at least one resolver held fixed. Time and cache state still differ, so this is not proof of geographic proximity.

## Part A · Official trace alternative, with a remaining coverage gap

Mac BPF access was denied in the preceding capture attempt, so this uses path B:
the DNS packets from `dns-wireshark-trace1-1.pcapng` in the official
[9th-edition archive](https://www-net.cs.umass.edu/wireshark-labs/wireshark-traces-9e.zip).
`out/dns.pcapng` retains only DNS packets, not unrelated HTTP traffic.
Numbers below refer to this filtered, submitted capture.

- Query frame 1 and response frame 2 both have transaction ID `0x3c29`.
  The client is 10.0.0.44 and its recursive resolver is 75.75.75.75.
  These identify the observed host and resolver, not the human owner's identity;
  this is the textbook author's supplied trace, not traffic from the student's Mac.
- Frame 2 is an answer: ANCOUNT 1, A = 128.119.245.12 for gaia.cs.umass.edu.
- Largest DNS messages are frames 10 and 14, each **127 DNS bytes**:
  UDP length 135 minus the 8-byte UDP header. Each captured Ethernet frame is
  169 bytes. Both responses carry two CNAMEs and one A, increasing answer size.
- **No delegation response is present in this selected trace** (all response
  authority counts are zero). Do not label an NS answer as a referral.
  Consequently A3's pair of captured delegation/answer packet numbers is not
  fully satisfied. A permitted local capture or a trace containing a genuine
  referral is still needed to close this gap.

The live Task 1 evidence in `resolve.json` separately shows the distinction:
the first root response for www.korea.ac.kr has no answers and kr NS records in
authority; the final response contains an authoritative A answer. That is a
real parsed response observation, but it is not a packet-number substitute.

Wireshark lab trace files from J.F. Kurose and K.W. Ross,
*Computer Networking: A Top-Down Approach*, 9th ed.
https://gaia.cs.umass.edu/kurose_ross/
Copyright 1996-2025 J.F. Kurose, K.W. Ross. All Rights Reserved.

