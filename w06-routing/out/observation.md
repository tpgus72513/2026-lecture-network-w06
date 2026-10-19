# Week 06 관찰

## Task 1 — Link state를 손으로
- 동률이면 이름이 앞서는 이웃을 first hop으로 고정한다. 실제 OSPF는 ECMP로 동률 hop을 모두 설치하고 flow hash로 나눈다.
- `u`→`w`의 next hop은 `x`다. 직통 `u-w`는 5지만 `u-x-y-w`가 3이라, 인접이 아니라 최단 경로를 따른다.
- `u-x`가 끊기면 w·x·y·z가 `x`→`v`로 바뀌고 `v`만 그대로다. `w`는 직통 `u-w`(5)와 `u-v-w`(5)가 동률이라 규칙대로 `v`다.

## Task 2 — 실제 네트워크를 끊고 복구 시간 재기
- 캠퍼스 출구는 hop 3 `163.152.233.129`다. SNU·Stanford·1.1.1.1은 여기서 SK브로드밴드로, `korea.ac.kr`은 KU 자체 망(`163.152.205.206`)으로 나간다. 바다는 오사카 40 ms→LA 148 ms(JUPITER 추정)이고, 1.1.1.1은 목적지 응답 없이 12번째 hop Cloudflare(`colo=ICN`)라 서울 복제본이다.
- `* * *`는 ICMP를 안 주는 라우터(뒤 hop은 답함)와 probe를 막는 목적지(끝까지 *) 두 경우다. 각 라우터는 직결 안 된 /16을 OSPF로 배웠다.
- 설정은 Hello 10 s/Dead 40 s다. `scenario.sh cut`(인터페이스 down)은 r1이 carrier 손실을 즉시 알아 LSA flood+SPF만으로 0.08–0.14 s다. 링크를 살린 채 패킷만 버리면 Dead 만료를 기다려 31 s인데, Dead는 마지막 hello부터 세니 장애 후 30–40 s라 설정과 일치한다. 복구 9 s는 상대 Hello(최대 10 s)와 adjacency 협상을 기다려서, 비용 변경 0.2 s는 감지할 게 없어 flood+SPF만 남아서다.

## Task 3 — 세상을 다시 계산하지 않고 재수렴
- 노드별 거리 `dist`(400개, 약 24 KiB, 그래프 사본의 1/5)를 이벤트 사이에 보관한다. `dist`는 full SPF 때 한 번 더 도는 비계측 패스로 구하므로, 이를 세면 177회가 아니라 354회(65% 절감)다(`report.md`).
- 안 쓰던 링크 down은 무시, 좋아짐은 짧아진 노드만 고친다. 마지막 최단 경로를 잃은 down·비싸짐만 full SPF다.
- wall이 느린 건 bench가 검증 SPF까지 재서다. 라우터는 SPF가 연달아 돌면 hold time이 50 ms→최대 5 s로 늘어 횟수가 곧 지연이다. Python에선 dict 연산이 비싸지만, 라우터에선 flap 중 제어평면 CPU와 수렴 시간이 모자란 자원이다.
