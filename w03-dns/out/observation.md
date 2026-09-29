# Lab 3 observations

## Task 1
루트는 최종 호스트의 A 대신 담당 TLD의 NS와 glue를 반환했다. 실제 고려대 조회는 root→kr→권한 서버의 3회 질의였고, 저장한 5개 이름은 각각 3·3·6·6·10회 질의로 dig 결과와 일치했다(resolve.json).
glue가 없으면 NS 이름도 루트부터 별도로 해석하고 원래 질의를 재개한다. 이번 5개 실측에는 이 분기가 없었지만 fixture 테스트에서는 NS 주소 조회 1회가 추가되어 총 3회였다. 실제 비용은 해당 NS 이름의 위임 깊이에 따라 달라진다.
무응답 서버는 다음 후보로 넘어가고 CNAME은 새 이름으로 루트부터 재시작한다. 초기 구현이 cross-TLD glue를 지나치게 제한해 순환했으나 수정 후 5/5 통과했고, 순환·조회 예산·서버 대체를 별도로 검사했다.

## Task 2 · second network and delegation capture pending
공식 trace에서 질의/응답은 1·2번(ID 0x3c29), A 응답은 2번, 최대 DNS 응답은 10·14번의 127바이트(CNAME 2개+A 1개)였다. 이 trace에는 위임 패킷이 없어 A3는 미완료이며 실제 Task 1 응답에서는 root의 빈 answer+NS authority와 최종 A answer를 구분했다.
끝 두 label이 달라지면 제3자로 보는 규칙은 wikipedia.org→wikimedia.org를 오판했다. 같은 Wikimedia 운영임을 확인하고 제공자 suffix와 운영 주체를 구분했으며 CNAME 부재를 CDN 부재로 간주하지 않았다.
현재 네트워크에서 resolver(system·Google·Quad9)에 따라 전체 8/12, 명시적 제3자 CDN subset 7/8의 A 집합이 달랐다. 이는 선택 차이를 보여도 더 가까운 서버임을 입증하지 않으며 anycast·캐시·시간 변화가 섞인다. 두 번째 네트워크 비교는 대기 중이다.
