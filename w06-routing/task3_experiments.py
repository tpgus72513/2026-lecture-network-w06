#!/usr/bin/env python3
"""Week 6 · Task 3 — what YourRouter avoids, what still costs a full SPF, and
whether it stays right on areas it was not tuned on.

    python3 task3_experiments.py > out/task3-experiments.txt
"""
import io, statistics, sys, time
from collections import Counter
from contextlib import redirect_stdout

import bench
import task3_reconverge as T


def kind(old, new):
    if new == old:
        return "no-op (same cost)"
    if new is None:
        return "down"
    if old is None:
        return "up"
    return "cost down" if new < old else "cost up"


# 1. every event of the graded run, by type: how many forced a full SPF
graph, events = bench.build()
src = sorted(graph)[0]
T.SPF_RUNS = 0
r = T.YourRouter(graph, src)
seen, full, moved, rederive = Counter(), Counter(), Counter(), 0
for a, b, c in events:
    k, spf0, d0, t0 = kind(r.graph[a].get(b), c), T.SPF_RUNS, dict(r.dist), dict(r.table)
    r.link_change(a, b, c)
    seen[k] += 1
    full[k] += T.SPF_RUNS > spf0
    moved[k] += sum(d0.get(n) != r.dist.get(n) for n in set(d0) | set(r.dist))
print("== 1. graded run (seed 246): 1,000 events by type")
print(f"  {'event':<18} {'count':>5} {'full SPF':>9} {'avoided':>8}  costs moved per event")
for k in ("down", "cost up", "up", "cost down", "no-op (same cost)"):
    print(f"  {k:<18} {seen[k]:>5} {full[k]:>9} {seen[k] - full[k]:>8}  {moved[k] / seen[k]:.2f}")
print(f"  {'total':<18} {sum(seen.values()):>5} {sum(full.values()):>9} "
      f"{sum(seen.values()) - sum(full.values()):>8}   (+1 SPF at start-up)")

# 2. what is kept between events
print("\n== 2. state kept between events")
dist_bytes = sys.getsizeof(r.dist) + sum(sys.getsizeof(v) for v in r.dist.values())
graph_bytes = sum(sys.getsizeof(e) for e in r.graph.values()) + sys.getsizeof(r.graph)
print(f"  dist: {len(r.dist)} entries, about {dist_bytes / 1024:.0f} KiB "
      f"(the graph copy every router already holds: about {graph_bytes / 1024:.0f} KiB)")

# 3. correctness and savings on areas it was never run on
print("\n== 3. other seeds (same size), table checked after every event")
saved = []
for seed in range(1, 21):
    g, ev = bench.build(seed)
    with redirect_stdout(io.StringIO()):
        base = bench.run(T.FullRecompute, "baseline", g, ev)
        mine = bench.run(T.YourRouter, "yours", g, ev, check=True)
    saved.append(1 - mine["spf"] / base["spf"])
    print(f"  seed {seed:>2}: wrong {mine['wrong']}, SPF {mine['spf']:>4}/{base['spf']}, "
          f"avoided {saved[-1]:.0%}, wall {mine['time']:.2f}s vs {base['time']:.2f}s")
print(f"  avoided: min {min(saved):.0%}, median {statistics.median(saved):.0%}, max {max(saved):.0%}")

# 4. wall time per event, split by what the event cost
print("\n== 4. where the wall time goes (graded run, mean per event)")
r = T.YourRouter(graph, src)
spent = Counter(); count = Counter()
for a, b, c in events:
    spf0, t0 = T.SPF_RUNS, time.perf_counter()
    r.link_change(a, b, c)
    k = "full SPF" if T.SPF_RUNS > spf0 else "no SPF"
    spent[k] += time.perf_counter() - t0; count[k] += 1
t0 = time.perf_counter(); T.dijkstra_table(graph, src); spf_t = time.perf_counter() - t0
for k in ("no SPF", "full SPF"):
    print(f"  {k:<9} {count[k]:>4} events  {spent[k] / count[k] * 1e3:6.2f} ms each")
print(f"  one bare dijkstra_table(): {spf_t * 1e3:.2f} ms")

# 5. bench.py's wall clock for "yours" includes its own check - one reference
#    dijkstra_table() per event, run inside the timed loop. Without the check:
print("\n== 5. wall time with and without bench.py's per-event check (best of 3)")
with redirect_stdout(io.StringIO()):
    rows = {lbl: min(bench.run(cls, lbl, graph, events, check=chk)["time"] for _ in range(3))
            for lbl, cls, chk in [("baseline", T.FullRecompute, False),
                                  ("yours, checked", T.YourRouter, True),
                                  ("yours, unchecked", T.YourRouter, False)]}
for lbl, t in rows.items():
    print(f"  {lbl:<17} {t:5.2f} s")

# 6. how far _shorten reaches: nodes whose cost it lowers, per call
print("\n== 6. _shorten (cost falls, no SPF): nodes lowered per call")
for seed in (246, 1):
    g, ev = bench.build(seed)
    r = T.YourRouter(g, sorted(g)[0])
    sizes, orig = [], r._shorten

    def counted(offers, orig=orig, r=r):
        before = dict(r.dist)
        orig(offers)
        sizes.append(sum(before.get(n) != c for n, c in r.dist.items()))
    r._shorten = counted
    for a, b, c in ev:
        r.link_change(a, b, c)
    print(f"  seed {seed:>3}: {len(sizes)} calls, mean {statistics.mean(sizes):.1f}, "
          f"max {max(sizes)} of {len(g)} nodes")

# 7. small random areas, including ones that split in two: every event checked
print("\n== 7. fuzz: 3,000 small random areas x 40 events (partitions included)")
import random
rng, events_n, wrong, crashed = random.Random(7), 0, 0, 0
for _ in range(3000):
    n = rng.randint(2, 9)
    names = [f"n{i}" for i in range(n)]
    g = {x: {} for x in names}
    for _ in range(rng.randint(0, 2 * n)):
        a, b = rng.sample(names, 2)
        g[a][b] = g[b][a] = rng.randint(1, 4)
    try:
        r = T.YourRouter(g, names[0])
        for _ in range(40):
            a, b = rng.sample(names, 2)
            r.link_change(a, b, None if rng.random() < 0.4 else rng.randint(1, 4))
            events_n += 1
            wrong += r.table != T.dijkstra_table(r.graph, names[0])
    except Exception:
        crashed += 1
print(f"  {events_n:,} events, wrong tables {wrong}, crashed runs {crashed}")
