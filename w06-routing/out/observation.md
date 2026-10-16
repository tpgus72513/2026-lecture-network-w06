# Week 06 관찰

## Task 1 — Link state를 손으로
- 동률이면 이름이 앞서는 이웃을 first hop으로 고정한다. 실제 OSPF는 ECMP로 동률 hop을 모두 설치하고 flow hash로 나눈다.
- `u`→`w`의 next hop은 `x`다. 직통 `u-w`는 5지만 `u-x-y-w`가 3이라, 인접이 아니라 최단 경로를 따른다.
- `u-x`가 끊기면 w·x·y·z가 `x`→`v`로 바뀌고 `v`만 그대로다. `w`는 v·w가 5로 동률이라 규칙대로 `v`다.

## Task 2 — 실제 네트워크를 끊고 복구 시간 재기
- 학교 밖 경로(서울대·해외)는 hop 3(KU)→4(SK브로드밴드)에서 나가고 `korea.ac.kr`는 KU 망을 안 떠난다. 바다는 BBIX 오사카 40 ms→HE LA 148 ms 점프라 JUPITER 같은 일본–LA 케이블로 보인다. 1.1.1.1은 마지막 응답 hop 12가 Cloudflare(10 ms), colo=ICN인 서울 복제본이다. `* * *`는 라우터의 ICMP 미응답(뒤 hop은 답함)과 목적지의 probe 차단(끝까지 *)이다.
- 각 라우터는 직결 안 된 /16을 [110/20]으로 배웠다. 링크 down은 0.14 s 안(carrier로 즉시 앎), 패킷만 버리는 장애는 30.8–31.7 s로 Dead 40 s(Hello 10 s마다 리셋되니 30–40 s)와 맞는다.
- 복구는 8.4–9.5 s로 링크 down보다 늦다. 사라짐은 carrier 신호 하나면 되지만, 생김은 상대의 다음 Hello(≤10 s)를 기다린 뒤 2-Way와 DB 동기화를 거쳐야 한다. 비용 변경은 0.21 s로, 감지 없이 LSA flood와 SPF만 하면 된다.

## Task 3 — 세상을 다시 계산하지 않고 재수렴
- 노드별 거리 `dist`(400개, 약 24 KiB)를 보관한다. 그래프 사본(약 129 KiB)의 1/5이고, full SPF 때 같이 구하는 비용 패스가 한 번 더 든다.
- 안 쓰던 링크 down·비싸짐은 무시, 동률 대체가 있으면 hop만 다시 읽고, 좋아짐은 짧아진 노드만 고친다. 마지막 최단 경로를 잃는 down·비싸짐만 full SPF다(82% 절감).
- bench wall은 1.13 s로 baseline 0.80 s보다 느리지만, harness가 매 이벤트 검증 SPF까지 같이 재서다(빼면 더 빠름). 라우터는 SPF가 이어지면 hold time(50 ms→5 s)이 붙어 SPF 횟수가 곧 수렴 지연이라 옳다.
