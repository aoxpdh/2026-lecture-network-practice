# Week 06 진행 상태

Task 1과 Task 3은 구현·검증 완료. Task 2 Part A는 현재 Mac 네트워크에서 실측하여 traceroute.txt에 저장했다. OSPF 실험이 남아 아직 제출 가능한 상태가 아니다.
결과를 얻지 않은 route-before.txt, route-after.txt, reconverge.txt는 생성하지 않았다.

## 구현과 검증

- Task 1: heap 기반 Dijkstra, first-hop 전달, 도달 불가능 노드와 source 제외.
- Task 3: 제공된 dijkstra_table의 선택 순서와 카운터를 유지하며 선택적 state 인수로 거리·부모를 함께 반환한다. 별도 SPF를 숨겨 실행하지 않는다.
- bench.py, test_tasks.py와 check.py는 수정하지 않았다.
- python3 task1_linkstate.py --verify: all ok.
- python3 -m unittest test_routing_edges: 3개 테스트 통과. 단절, 복구, 동률 및 20 seeds × 300 events를 기준 구현과 비교했다.
- 공식 벤치마크: 1,000개 이벤트 모두 일치, SPF 363/1,001회, good.
- bench.txt의 추가 시간 비교는 동일 그래프·이벤트에 bench.run의 check=False를 양쪽 모두 적용했다.

## Task 2 재개 조건과 측정 주의점

사용자의 외부 접근 허용 및 실측 지시에 따라 2026-10-06 현재 네트워크에서 세 대상의 traceroute를 실행했다. Docker 27.4.0은 앞선 점검에서 응답했으며 FRR 이미지는 당시 로컬 목록에 없었다. OSPF 실험에는 FRR 이미지 준비가 필요하다.
과거 제출과 같이 개인 주소·기기 정보는 공개본에서 마스킹하고 실습 대상 주소와 측정치는 유지한다.

### 현재 네트워크 실측

각 TTL에 한 번, 응답 대기 1초, 최대 24홉으로 측정했다. 역방향 DNS는 껐고 UDP 세 번 및 ICMP 두 번을 수행했다. 전체 응답과 timeout을 traceroute.txt에 기록했다. 개인 사설 주소의 네트워크 부분만 마스킹했으며 RTT는 실측 그대로다.

- 고려대: UDP 4홉 이후 응답 없음. ICMP는 5홉 timeout 이후 6·7홉이 응답했다. 중간 별표가 반드시 이후 전달 실패를 뜻하지 않음을 관측했다. 두 방식 모두 목적지 도달 미확인.
- 학교 밖으로 나가는 지점: 국내 대상은 응답 구간이 163.152 대역 안에 있어 캠퍼스 이탈을 확인하지 못했다. 외부 두 대상은 3홉 163.152.233.129에서 4홉 175.121.235.141로 바뀌므로 출구 경계 후보이나 주소 소유권과 물리적 위치를 확인하지는 않았다.
- Stanford: www.stanford.edu는 stanford.netlifyglobalcdn.com의 3.33.186.135로 해석되었다. UDP·ICMP 모두 7홉 이후 응답이 없어 목적지 도달과 해저 구간은 미확인이다. 해외 기관의 사이트라는 사실이 해외 서버까지 이동했다는 증거는 아니다.
- Anycast: 1.1.1.1에 13홉, 11.295ms로 도달했다. 낮은 RTT는 가까운 서비스 지점을 시사하지만 홉 수/RTT만으로 도시·국가를 특정할 수 없다.
- 홉당 한 번의 측정으로 안정적인 평균·분산이나 손실률을 추정할 수 없다. 별표만으로 응답 필터링, rate limit, 실제 손실을 구분할 수 없다.

제공 scenario.sh를 그대로 사용하면 다음 측정 문제가 있다.

- cut은 r1만 저장하므로 세 라우터 모두의 수렴된 표를 별도로 수집해야 한다.
- show ip route ospf의 문자열 전체 비교는 경로 age 변화도 감지한다. prefix, next hop, interface, metric 등 실제 경로 필드로 수렴 여부를 확인해야 한다.
- eth0/eth1이 주석의 네트워크와 일치하는지 실제 주소와 Docker 네트워크 연결을 확인해야 한다.
- ip link set down은 로컬 장애 알림을 주므로 dead interval만큼 기다리는 무응답 장애와 구별해야 한다. 필요하면 hello 손실 실험을 별도로 측정한다.
- 설정 파일에는 hello/dead interval이 명시되어 있지 않다. 실행 중 show ip ospf interface에서 실제 값을 확인해야 한다.
- restore와 cost는 시간을 기록하지 않으므로 단절·복구·비용 변경을 각각 monotonic clock과 명시적인 기대 경로로 측정해야 한다.
- 비용 변경은 링크가 유지된 상태에서 before/after 경로를 저장해야 한다.
- compose up은 r1 r2 r3를 명시해 공통 lab 서비스가 함께 빌드되지 않도록 한다.

출구 라우터, 해저 구간과 케이블 이름은 실제 관측이 뒷받침하는 범위에서만 기록한다. CDN·응답 필터링 등으로 확인되지 않으면 미확인으로 남긴다.
