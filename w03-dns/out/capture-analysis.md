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
