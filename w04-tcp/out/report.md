# Lab 4 · Measurement report

Status: both real networks measured (five transfers each); handshake analysis uses the permitted official-trace path B.

Privacy: network identifiers and precise measurement times are redacted in the published copy. Throughput and timing durations are unchanged.

## Part A · Official TCP trace (path B)

The earlier local DHCP capture attempt failed with `/dev/bpf0: Permission denied`. TCP capture uses the same macOS BPF access, so the permitted official trace alternative is used here. This is not a capture of the student's connection and is separate from the live measurements below.

Source: https://www-net.cs.umass.edu/wireshark-labs/wireshark-traces-9e.zip

Member: `tcp-wireshark-trace1-1.pcapng`. `out/tcp.pcapng` retains TCP stream 0; frame numbers below were checked against this submitted file.

| Packet | Meaning | Raw sequence | Raw acknowledgement |
| --- | --- | --- | --- |
| 1 | SYN: 192.168.86.68 → 128.119.245.12 | 4236649187 | 0 (ACK flag unset) |
| 2 | SYN-ACK: server → client | 1068969752 | 4236649188 |
| 3 | ACK: client → server | 4236649188 | 1068969753 |

Each SYN consumes one sequence number. Wireshark's relative 0/1 display is not the raw initial sequence number. Independent nonconstant ISNs help distinguish connection incarnations and make sequence prediction harder; they are not required to equal one another.

Client SYN: MSS 1460, window scale shift 6 (factor 64), SACK permitted. Server SYN-ACK: MSS 1460, shift 7 (factor 128), SACK permitted. SYN window fields themselves are not scaled. Client packet 3 advertises 2058 × 64 = 131712 bytes. The client is uploading, so the relevant receive window for that data is the server's window: packet 7 advertises 249 × 128 = 31872 bytes, growing later. At packet 145 the maximum observed bytes in flight is 75296; the latest preceding server advertisement (packet 143) is 173824 bytes. The receive window is not full at this maximum.

The trace is consistent with startup congestion-window/ACK-clock growth and a short, application-sized transfer, rather than a full receive-window bottleneck. It does not expose the sender's congestion window or prove a unique limiting cause. No retransmissions were marked by tshark in this trace.

Whose transfer: the capture identifies an HTTP POST from 192.168.86.68 to gaia.cs.umass.edu (128.119.245.12), with `/wireshark-labs/lab3-1-reply.htm` visible in packet 153. This establishes endpoints and activity, not the human operator's identity. The authorship/source of the published trace comes from the distribution site; a person's identity cannot be determined from these packets alone.

## Part B · Live Mac measurement

Measured on 2026-09-29 during the recorded measurement session, on en0 with default gateway 172.16.[masked].1. Label: `Network A` (anonymized network label).

Target unchanged: `https://speed.cloudflare.com/__down?bytes=5000000`. Five fresh curl processes each downloaded exactly 5,000,000 bytes, one second apart. The script now requests HTTP/1.1 to ensure TCP, rejects HTTP errors and incomplete payloads, and bounds connection/transfer timeouts. These changes prevent error responses from counting as successful throughput measurements.

| Metric | First network |
| --- | --- |
| Throughput samples (Mbps) | 77.55, 77.44, 155.70, 174.89, 47.52 |
| Median | 77.55 Mbps |
| Min–max | 47.52–174.89 Mbps |
| Absolute spread | 127.38 Mbps |
| (max−min)/median | 164.3% |
| Median TCP connect estimate | 17.636 ms |

Throughput here is payload bits divided by total curl time, including DNS/connection/TLS/HTTP overhead, not a pure link-capacity measurement. `time_connect - time_namelookup` is a practical connection estimate, not a direct packet-level RTT measurement. The post-connect TTFB field also includes TLS setup.

The spread may reflect Wi-Fi contention, route/server load, queueing, and connection startup; these five end-to-end runs alone cannot identify the contribution of each. A larger RTT delays ACK feedback and slow-start growth, and reduces the approximate cwnd/RTT rate for a fixed congestion window. That can hurt short-transfer throughput even at equal physical capacity, but other changes can dominate; a strict per-run monotonic relationship is not expected.

## Network B (hotspot) comparison

After switching networks, the interface used en0 address 10.[masked].[masked].113 with gateway 10.[masked].[masked].85 and external IPv4 [public-IP-B]. The same target, payload size and measurement script were used on 2026-09-29 during the recorded measurement session.

| Metric | First network | Network B (hotspot) |
| --- | --- | --- |
| Runs | 5 | 5 |
| Mbps samples | 77.55, 77.44, 155.70, 174.89, 47.52 | 38.04, 41.98, 41.18, 40.78, 23.35 |
| Median Mbps | 77.55 | 40.78 |
| Min–max Mbps | 47.52–174.89 | 23.35–41.98 |
| Absolute spread Mbps | 127.38 | 18.63 |
| Relative spread (max−min)/median | 164.3% | 45.7% |
| Median TCP connect estimate | 17.636 ms | 33.191 ms |

The hotspot's median throughput was about 47.4% lower and connect time about 1.88× longer. That is consistent with slower ACK feedback/slow-start growth contributing to lower short-transfer throughput, but mobile radio, queueing, server selection, and the elapsed time also differ; it does not isolate RTT as the sole cause. The fifth hotspot sample was lower than the first four, demonstrating within-network variation too. DNS collection ran concurrently with the start of this small-transfer experiment; its traffic was low but is another uncontrolled factor. These are end-to-end observations, not a controlled capacity benchmark.

## Attribution

Wireshark lab trace files from J.F. Kurose and K.W. Ross,
*Computer Networking: A Top-Down Approach*, 9th ed.
https://gaia.cs.umass.edu/kurose_ross/
Copyright 1996-2025 J.F. Kurose, K.W. Ross. All Rights Reserved.
