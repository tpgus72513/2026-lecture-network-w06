# Week 06 Routing · Reconvergence — 측정 보고서

관찰 요약은 [`observation.md`](observation.md)에 있다(Task별 3줄). 이 문서는 Task 2의 A1–A5, B1–B5, C1–C3에 하나씩 답한다. 또 observation의 근거와 모든 숫자가 어느 파일에서 나왔는지 밝힌다.

## 재현

```bash
cd w06-routing
python3 task1_linkstate.py --verify          # -> out/task1-verify.txt
python3 task1_ties.py > out/task1-ties.txt
python3 task2_traceroute.py > out/traceroute.txt
python3 task2_hops.py > out/hop-evidence.txt      # RDAP 소유자, 1.1.1.1 colo, ping
bash scenario.sh up
bash task2_measure.sh snapshot out/route-before.txt
bash task2_measure.sh cut 15                 # 이벤트마다 1회, raw 로그는 out/runs/에 보관
bash task2_measure.sh snapshot out/route-after.txt
bash task2_measure.sh restore 70             # silent, unsilent, cost, uncost도 같은 방식
python3 task2_summary.py > out/reconverge.txt
python3 bench.py --yours > out/bench.txt
python3 task3_experiments.py > out/task3-experiments.txt
python3 test_tasks.py                        # -> out/tests.txt
python3 ../check.py w06
```

`bench.py`, `test_tasks.py`, `scenario.sh`, `topology/`, `compose.yml`, `task1_linkstate.py`의 harness 부분, `dijkstra_table`, `FullRecompute`는 수정하지 않았다. 내가 추가한 보조 스크립트는 다음과 같다.

- `task1_ties.py`: 표와 동률 hop을 출력한다.
- `task2_traceroute.py`: tracert 출력을 UTF-8로 저장한다.
- `task2_hops.py`: 주요 hop의 RDAP 소유자, 1.1.1.1에 답한 Cloudflare 사이트, ping 결과를 저장한다.
- `task2_measure.sh`와 `task2_timeline.py`: 이벤트 하나의 시간을 잰다.
- `task2_summary.py`: 모든 측정을 하나의 표로 정리한다.
- `task3_experiments.py`: Task 3 분석을 출력한다.

### 교수님 harness를 그대로 돌릴 때 생긴 문제 두 가지

1. **이미지가 없음.** `compose.yml`의 `frrouting/frr:v9.1.0`은 Docker Hub에 없다. Hub의 태그는 `v8.4.1`이 마지막이다. FRR 프로젝트는 같은 9.1.0 릴리스를 `quay.io/frrouting/frr:9.1.0`으로 배포한다. 저장소 루트에 `compose.override.yml`을 추가해 이미지만 바꿨다. Docker Compose가 이 파일을 자동으로 합치므로 `compose.yml`과 `scenario.sh`는 손대지 않았다.
2. **줄 끝 CRLF.** Windows에서 `core.autocrlf=true`로 받으면 `topology/*/daemons`가 CRLF가 된다. 그러면 `ospfd_options="  -A 127.0.0.1\r"`가 되어 ospfd가 `getaddrinfo failed: Name does not resolve`를 내고 죽는다. 작업 사본을 LF로 바꾸고 `core.autocrlf=false`로 커밋했다.

## Task 1 · `task1_linkstate.py`

- **구현 방식.**
  - `_spf()`가 heap에 `(cost, first_hop, node)`를 넣고 꺼낸다. 처음 꺼낸 노드를 확정하고, first hop은 source의 이웃에서 정해진 뒤 그대로 물려받는다.
  - `dijkstra()`와 `forwarding_table()`은 이 결과의 cost와 hop을 각각 돌려준다. source와 도달할 수 없는 노드는 넣지 않는다(R1, R2, R4). `networkx`는 쓰지 않았다(R6).
  - `--verify`는 10개 검사를 모두 통과한다(`out/task1-verify.txt`).
- **동률 규칙.**
  - cost가 같으면 heap이 `first_hop`을 비교하므로, 이름이 앞서는 이웃이 first hop이 된다. 같은 지도는 언제나 같은 표를 만들고, 동률 뒤의 목적지는 인터페이스 하나에 고정된다.
  - 실제 OSPF 라우터는 동률 경로를 ECMP로 모두 설치하고(FRR 기본값), 패킷을 flow hash로 나눠 보낸다.
  - Task 2의 FRR 표가 그 예다. `r1`은 `172.19.0.0/16`을 `via 172.20.0.3`과 `via 172.22.0.2` 두 개로 설치했다(`out/route-before.txt`).
- **`u`→`w`.** next hop은 `x`이고 cost는 3이다. 직통 `u-w`는 5인데 `u-x-y-w`는 1+1+1=3이다. 표는 인접이 아니라 최단 경로의 첫 hop을 따른다(`out/task1-ties.txt`).
- **`u-x`가 끊긴 뒤.**
  - w, x, y, z의 hop이 `x`에서 `v`로 바뀌었고, `v`만 그대로다.
  - `w`는 `u-w`(5)와 `u-v-w`(2+3=5)가 동률이다. `task1_ties.py`가 이것을 `v, w <- tie`로 표시하고, 규칙에 따라 `v`가 설치됐다.
  - ECMP 라우터였다면 `w`로 가는 트래픽을 `v`와 `w` 두 인터페이스로 나눴을 것이다.

## Task 2 · 측정 환경

- 2026-10-16 14시, 고려대 세종캠퍼스 Wi-Fi(`KUWIFI`), Windows 11 `tracert`(ICMP echo)
- Docker Desktop 29.6.1, FRR 9.1.0 컨테이너 3대

### Part A · `out/traceroute.txt`

**A1 · 대상.**

| 구분 | 대상 | 비고 |
|---|---|---|
| 국내 | `www.korea.ac.kr` (163.152.6.10) | |
| 해외 | `www.stanford.edu` | 과제가 지정한 대상 |
| 해외 | `web.stanford.edu` | 추가 |
| anycast | `1.1.1.1` | |
| 국내, KU 밖 | `www.snu.ac.kr` (147.46.10.129) | 추가 |

`www.stanford.edu`는 `stanford.netlifyglobalcdn.com`, 곧 AWS Global Accelerator의 anycast 주소 `3.33.186.135`와 `15.197.167.90`으로 풀린다. 추적은 hop 7(9 ms)에서 끊겨 바다를 건너지 않는다. 그래서 Stanford 자체 망(171.64.0.0/14)에 있는 `web.stanford.edu`(171.67.215.200)도 추적했다.

**A2 · 캠퍼스를 나가는 곳.** 다음 표의 소유자는 RDAP 조회 결과다(`out/hop-evidence.txt`).

| hop | 주소 | 소유자 |
|---|---|---|
| 1 | 172.16.0.2 | 사설 |
| 2 | 192.168.98.132 | 사설 |
| 3 | 163.152.233.129 | Korea University, KUCCNET |
| 4 | 175.121.235.141 | SK Broadband |

학교 밖으로 가는 경로(서울대, Stanford, 1.1.1.1)는 모두 hop 3에서 hop 4로 넘어갈 때 학교 망을 떠난다. 그 hop 3이 캠퍼스 경계 라우터다. 서울대 경로는 hop 4–10이 SK브로드밴드(10.x 내부 주소와 211.108.22.106)이고, hop 11 `147.46.254.187`(Seoul National University)에서 8 ms로 서울대 망에 들어간다. 반면 과제가 지정한 국내 대상 `www.korea.ac.kr`는 학교를 떠나지 않는다. 경로는 hop 3 다음에 SK브로드밴드가 아니라 163.152.205.206과 163.152.4.140/150으로 간다. 모두 KU 주소이고, hop 4에서 RTT가 약 +7 ms 늘어난다. 대상이 KU 자기 대역(163.152.0.0/16)이라 경로가 학교 망 안에서 끝난다.

**A3 · 바다를 건너는 곳.** `web.stanford.edu` 경로는 다음과 같다.

| hop | 주소 | RTT |
|---|---|---|
| 7 | 10.222.1.79 | 6 ms |
| 8 | 10.222.3.163 | 33 ms |
| 9 | 218.100.9.26 (BBIX Osaka, RDAP) | 40 ms |
| 10–12 | `* * *` | |
| 13 | `be41.core3.lax1.he.net` | 148 ms |
| 14–16 | `sjc2`, `pao1`(Palo Alto) | |
| 17 | `campus-east-rtr-vl1018.SUNet` | 142 ms |

- hop 7→8의 +27 ms는 한국에서 일본으로 넘어가는 구간이다.
- hop 9→13의 **+108 ms 점프**가 태평양 횡단이다. 오사카 IX에서 Hurricane Electric의 Los Angeles 코어로 바로 이어진다.
- 그러니 일본과 LA를 잇는 태평양 해저 케이블이다. 오사카 근처 시마(Shima)와 LA 허모사 비치에 상륙하는 JUPITER가 가장 잘 맞는다. 다만 traceroute만으로 케이블 이름까지 확정할 수는 없다.

**A4 · anycast 1.1.1.1.**

- Cloudflare 주소 `141.101.82.17`이 hop 12에서 RTT 7–10 ms로 나타났다. 그 뒤로는 응답이 없다.
- 추적이 목적지 자체에 닿지는 않았다. 마지막으로 응답한 hop이 12의 Cloudflare 주소다. `ping 1.1.1.1`도 이 네트워크에서는 100% 손실이다. 반면 `https://1.1.1.1/cdn-cgi/trace`는 `colo=ICN loc=KR`을 돌려준다(둘 다 `out/hop-evidence.txt`).
- 그러니 복제본은 서울(인천 공항 코드 ICN)에 있다. hop 12까지의 최소 RTT가 모두 10 ms 이하라 국내를 벗어나지 않았다.
- 같은 주소인데 Stanford 경로의 1/15 RTT다. anycast는 BGP가 가장 가까운 사본으로 보내는 것이지, 1.1.1.1이 한 곳에 있다는 뜻이 아니다.

**A5 · `* * *`의 두 가지 이유.**

1. **라우터가 패킷은 전달하지만 ICMP Time Exceeded를 보내지 않는다.** 정책 때문일 수도, control-plane rate limit 때문일 수도 있다. `web.stanford.edu`의 hop 10–12가 `*`인데 hop 13이 다시 답한다. 그러니 패킷은 그 라우터들을 지나갔다. `korea.ac.kr` hop 5도 같다.
2. **probe나 응답이 그 지점부터 실제로 버려진다.** 목적지나 방화벽이 ICMP echo를 막는 경우다. 그러면 그 뒤로는 끝까지 `*`다. `1.1.1.1`(ping 100% 손실, HTTPS는 됨), `korea.ac.kr`의 hop 8–30, `web.stanford.edu`의 hop 18–30이 그렇다.

첫째는 보이지 않을 뿐 경로가 살아 있고, 둘째는 측정 수단이 막힌 것이다.

### Part B · `out/route-before.txt`, `out/route-after.txt`, `out/reconverge.txt`

네트워크와 인터페이스는 다음과 같이 대응한다(`docker network inspect`).

| 네트워크 | 대역 | 라우터 |
|---|---|---|
| net_a | 172.20/16 | r1 eth0, r3 eth1 |
| net_b | 172.22/16 | r1 eth1, r2 eth1 |
| net_c | 172.19/16 | r2 eth0, r3 eth0 |

r2의 eth0/eth1은 `frr.conf`의 description과 반대로 붙었다. 비용이 모두 10이라 결과에는 영향이 없다. `cut`과 `cost`가 건드리는 r1은 description과 일치한다.

**B1, B2.** 세 라우터 모두 직접 붙지 않은 /16 하나를 `O>* [110/20]`으로 배웠다. 두 이웃으로 가는 ECMP 2개다.

| 라우터 | 배운 경로 |
|---|---|
| r1 | 172.19/16 (net_c) |
| r2 | 172.20/16 (net_a) |
| r3 | 172.22/16 (net_b) |

**B3.** r1 eth1이 down된 뒤의 표다.

| 라우터 | 표 |
|---|---|
| r1 | `172.22/16 [110/30] via 172.20.0.3`(r3, 두 hop 우회). 172.19/16은 r3로만 간다 |
| r2 | 172.20/16을 r3로만 보낸다 |
| r3 | 172.22/16을 r2로만 보낸다. 모두 r1–r2 링크를 쓰던 ECMP가 하나로 줄었다 |

**B4 · 재수렴 시간 측정 방법.** `task2_measure.sh`는 다음처럼 잰다.

- 세 라우터 안에서 0.1 s마다 `show ip route ospf`를 읽는다. uptime 열을 지우고, 경로가 실제로 바뀔 때만 시각을 남긴다.
- 컨테이너들은 커널 하나를 공유하므로 `/proc/uptime` 하나가 세 라우터의 공통 시계가 된다.
- 이벤트 시각도 r1 안에서 이벤트를 일으키는 같은 명령으로 읽는다.

결과는 각 3회 측정했다. 원본 로그는 `out/runs/`에 있다.

| 이벤트 | 마지막 표 변화 |
|---|---|
| 링크 down(`scenario.sh cut`과 같음) | 0.08 / 0.12 / 0.14 s |
| 링크는 up인 채 패킷만 drop(`iptables`) | 31.7 / 30.8 / 31.2 s (세 라우터가 모두 첫 변화를 마친 시각) |

- `frr.conf`에는 타이머 설정이 없다. 세 라우터의 `show ip ospf interface`는 **Hello 10 s, Dead 40 s**를 보고한다.
- 링크 down은 r1 커널이 carrier 손실을 바로 알린다. 그래서 타이머 없이 LSA flood와 SPF만으로 끝나 Dead 40 s와 무관하다.
- 패킷 drop은 hello가 끊길 뿐이라 Dead 타이머가 만료되어야 안다. 타이머는 hello를 받을 때마다 40 s로 리셋되고 hello는 10 s마다 온다. 그러니 감지 시각은 장애 후 30–40 s여야 하고, 측정값 30.8–31.7 s가 이 범위 안에 있다.
- 관찰 한 가지: 약 35 s에 r1이 혼자 남은 net_b를 다시 자기 stub로 광고한다. 그러자 r3가 r1을 거치는 net_b ECMP를 되살렸다(`out/route-after-silent.txt`). 이 경로는 r1이 net_b로 보내는 패킷이 버려지므로 틀렸고, 그대로 남는다. OSPF가 아는 것은 r2가 조용해졌다는 사실뿐이고, 그 선이 못 쓰게 되었다는 것은 모른다.
- `scenario.sh cut` 자체는 `재수렴 감지: 2 초`를 출력했다(`out/scenario/`). 이 스크립트는 uptime이 포함된 raw 출력을 1 s마다 비교한다. 그래서 경로가 바뀌지 않아도 첫 poll에서 "변화"를 감지한다. 실제 변화는 0.14 s 안에 있었다.

**B5 · 복구.**

| 이벤트 | 마지막 표 변화 |
|---|---|
| 링크 up | 8.4 / 9.0 / 9.5 s |
| drop 해제 | 9.5 / 13.8 / 16.0 s |

- 링크 up 직후 0.1 s 안에 r1은 net_b를 다시 자기 stub로 광고하고, r3는 r1을 거치는 ECMP를 즉시 되찾는다.
- 하지만 r2가 r1 경로를 되찾는 데는 8–10 s가 걸린다. 인접을 만드는 순서는 다음과 같다.
  1. 상대의 hello에 자기 Router ID가 실린 것을 봐야 2-Way가 된다. r2의 다음 hello는 최대 10 s 뒤에 온다.
  2. 그 뒤 DR/BDR를 정하고 DD 교환을 시작한다(ExStart → Exchange → Loading).
  3. LSA를 맞추고 Full이 된 다음에야 SPF가 그 링크를 쓴다.
- 사라짐은 부정적인 신호 하나로 안다. carrier가 꺼지거나 hello가 오지 않으면 된다. 생김은 양쪽이 서로를 확인하고 데이터베이스를 맞추는 협상이라 비대칭이다. 단, 패킷 drop 장애에서는 그 "안 옴"을 Dead 동안 기다려야 한다. 그래서 사라짐(30.8–31.7 s)이 생김(9.5–16 s)보다 오히려 늦었다.
- 고장을 늦게 아는 것은 dead 타이머가 대기한 시간이고, 복구가 늦는 것은 hello 주기와 adjacency FSM 때문이다.

### Part C · `out/route-cost-before.txt`, `out/route-cost-after.txt`

**C1, C2.** r1 eth0(net_a)의 비용을 10에서 100으로 올렸다(`scenario.sh cost`와 같은 명령). 링크는 내리지 않았다.

| 라우터 | 바뀐 경로 |
|---|---|
| r1 | 172.19/16(net_c)을 ECMP 대신 r2로만 보낸다. net_a(172.20/16)의 OSPF 경로도 `[110/30] via 172.22.0.2`(r2→r3)로 바뀌었지만 선택(`>*`)되지 않았다. 직결(connected) 경로가 이기므로 net_a 트래픽은 우회하지 않는다 |
| r2 | 172.20/16에서 r1 경유 ECMP를 버리고 r3로만 간다 |
| r3 | 바뀌지 않았다. OSPF 비용은 나가는 인터페이스 쪽에만 붙으므로 r3→net_a는 여전히 10이다 |

**C3 · 걸린 시간.** 0.18–0.21 s(되돌리기도 0.21 s)였다.

- 감지할 것이 없다. r1이 새 router-LSA를 즉시 만들어 flood하고, 받은 쪽은 SPF만 돌린다. FRR SPF throttle의 첫 지연은 0 ms다(`out/frr-spf-timers.txt`).
- 패킷 drop 고장(30.8–31.7 s)보다 약 150배 빠르다. 그 차이는 전부 "고장을 알아차리는 시간", 즉 Dead interval이다.
- carrier가 꺼진 링크 down(0.08–0.14 s)과는 같은 수준이다. 그 경우는 커널이 알아차림을 대신해 주었기 때문이다.

## Task 3 · `task3_reconverge.py`

`out/bench.txt` 결과: 오답 0, SPF 177회(baseline 1001회), **82% 절감, strong**.

**이벤트 사이에 보관하는 것.**

- 각 노드까지의 비용 `dist` 하나다. 400개 항목, 약 24 KiB다. 라우터가 원래 갖는 그래프 사본(약 129 KiB)의 1/5 정도다(`out/task3-experiments.txt` §2).
- `dist`는 full recompute를 할 때마다 `dijkstra_table()`이 표를 설치한 직후 같은 `_full()` 안에서 함께 구한다. `dijkstra_table()`은 hop만 돌려주므로, 비용을 얻으려면 이 패스가 필요하다. 이 패스는 계측되지 않는다. 그러니 full recompute 한 번에 실제로는 SPF 두 번 분량의 일을 한다. 이것까지 세면 177회가 아니라 354회이고, 절감률은 65%다. 이 패스는 계측되는 호출을 대신하지 않고, 혼자 돌지도 않는다.
- 비용이 내려갈 때 쓰는 `_shorten`도 계측되지 않는 부분 갱신이다. 범위는 좁다. 한 번에 낮추는 노드는 seed 246에서 평균 2.5개, 최대 33개다(400개 중). seed 1에서는 평균 4.0개, 최대 95개다(§6).

**세 경우.**

간선 u→v가 *tight*하다는 것은 `dist[u] + w == dist[v]`라는 뜻이다. 가중치가 1 이상이므로 tight 선행자는 항상 source에 더 가깝다.

1. **down 또는 비싸짐, 안 쓰던 링크.** 어느 방향도 tight가 아니면 아무것도 하지 않는다.
2. **down 또는 비싸짐, 쓰던 링크.**
   - 끝점에 다른 tight 선행자가 있으면 모든 비용이 그대로다. hop만 `dist`에서 다시 읽는다(`_hops_from_dist`).
   - 마지막 tight 선행자를 잃은 경우에만 full SPF를 돌린다.
3. **up 또는 싸짐.** 보관한 `dist`로 `dist[u] + w_new`를 `dist[v]`와 비교한다.
   - 크면 무시한다.
   - 같으면 hop만 다시 읽는다.
   - 작으면 짧아진 노드에서 시작해 밖으로 퍼지며 비용을 낮춘다(`_shorten`). 기존 비용을 이기지 못하는 이웃에서 멈추므로, 줄어드는 노드만 건드린다.

hop을 다시 읽을 수 있는 이유가 있다. `dijkstra_table`은 노드를 `(cost, 이름)` 순서로 꺼내고, 더 싼 제안만 받아들인다. 그러니 각 목적지의 hop은 tight 선행자 중 `(cost, 이름)`이 가장 작은 것에서 온다. 비용만 알면 SPF 없이 정렬과 간선 한 번 순회로 같은 표가 나온다.

**아직 full SPF를 강제하는 이벤트.** 어떤 노드의 마지막 최단 경로였던 링크가 down되거나 비싸지는 경우다. 비용이 늘어나는데, 누가 얼마나 늘어나는지가 곧 SPF가 푸는 문제다.

그래프 run 1,000개 이벤트의 내역이다.

| 이벤트 | 횟수 | full SPF |
|---|---|---|
| down | 371 | 78 |
| 비싸짐 | 237 | 98 |
| up | 70 | 0 |
| 싸짐 | 245 | 0 |
| 비용 같음 | 77 | 0 |

**일반화.** 튜닝에 쓰지 않은 seed 1–20에서도 1,000개 이벤트마다 표를 검증했다. 오답은 0이었고, 절감률은 80–84%(중앙값 82%)였다(§3). 2–9개 노드짜리 작은 area 3,000개에서도 40개 이벤트마다 검사했다. 둘로 갈라지는 경우까지 포함해 120,000개 이벤트에서 오답 0, 크래시 0이었다(§7). 이 퍼징에서 분할된 쪽 링크 이벤트가 `KeyError`를 내는 버그를 찾아 고쳤다.

**R5 · wall time.**

- `bench.py`에서 내 쪽은 1.13 s로 baseline 0.80 s보다 느리다(`out/bench.txt`). 실행마다 ±30% 정도 흔들린다.
- 그런데 `bench.py`는 내 라우터에만 매 이벤트 검증용 `dijkstra_table()`을 돌리고, 그 시간을 같은 타이머에 넣는다.
- 검증을 빼고 재면 0.52 s로 baseline 1.17 s보다 빠르다(§5, best of 3, 같은 실행 안에서 비교).
- 순수한 비용 차이도 있다. 이벤트 하나에 SPF가 필요 없으면 0.12 ms, full SPF는 2.03 ms다(§4). full SPF 쪽은 `dist`를 함께 구하느라 bare SPF(1.30 ms)보다 비싸다. SPF를 피한 이벤트도 hop 재도출에 정렬 한 번과 간선 순회 한 번이 든다. Python에서는 이런 dict 연산 하나하나가 비싸다.
- 그래도 라우터에서는 옳은 선택이다. 라우터에 부족한 것은 연산 속도가 아니라 수렴 시간이다.
  - FRR은 SPF를 연달아 돌리면 hold time을 50 ms에서 시작해 최대 5 s까지 늘린다(`out/frr-spf-timers.txt`).
  - 링크 하나가 flap할 때 SPF를 매번 돌리면 그 대기가 쌓여 표가 수 초씩 늦어진다. 그 사이 area 안 모든 라우터의 control-plane CPU가 함께 묶인다.
  - SPF 횟수가 곧 지연이므로, 장부 비용을 조금 더 내고 SPF의 82%를 피하는 쪽이 맞다.

## 개인정보

- `traceroute.txt`의 출발 주소는 캠퍼스 공유 주소다. 사설 hop과 학교 및 ISP 라우터 주소만 있다.
- 컨테이너 주소는 모두 Docker 내부 대역이다.
- MAC, 호스트 이름, 집 주소는 이번 제출물에 없다.
