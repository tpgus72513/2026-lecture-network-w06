#!/usr/bin/env python3
"""Week 6 · Task 2 B4/B5/C3 — one table of every timed event in out/runs/.

    python3 task2_summary.py > out/reconverge.txt

For each run: when each router's OSPF routes first and last changed after the
event (from task2_measure.sh's raw logs, 0.1 s polling, one shared clock).
"""
import glob, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "out", "runs")
ORDER = ["cut", "restore", "silent", "unsilent", "cost", "uncost"]
WHAT = {"cut": "r1 eth1 link down (scenario.sh cut)",
        "restore": "r1 eth1 link up (scenario.sh restore)",
        "silent": "r1 drops all packets on eth1, link stays up",
        "unsilent": "r1 stops dropping",
        "cost": "r1 eth0 cost 10 -> 100 (scenario.sh cost)",
        "uncost": "r1 eth0 cost 100 -> 10"}


def parse(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    t0, cur, out = float(lines[1].split()[1]), None, {}
    for l in lines[2:]:
        if l.startswith("== "):
            cur = l[3:]; out[cur] = []
        elif l.startswith("@ ") and float(l[2:]) > t0:
            out[cur].append(float(l[2:]) - t0)
    return out


conf = open(os.path.join(HERE, "topology", "r1", "frr.conf"), encoding="utf-8").read()
print("OSPF timers: frr.conf sets none, so FRR defaults apply; `show ip ospf interface`")
print("on all three routers reports: Hello 10s, Dead 40s, Wait 40s, Retransmit 5")
print("(timers set in frr.conf: " + (", ".join(re.findall(r"ip ospf \w+-interval \d+", conf))
                                      or "none") + ")\n")
print("seconds after the event fired; first/last time each router's routes changed")
print("first-settled: every router has made its first change; last-change: nobody moves after")
print(f"{'event':<9} {'run':>3}  {'r1':>13}  {'r2':>13}  {'r3':>13}  first-settled  last-change")
for ev in ORDER:
    for path in sorted(glob.glob(os.path.join(RUNS, f"raw-{ev}-*.log"))):
        run = path.rsplit("-", 1)[1][:-4]
        ch = parse(path)
        cells = [(f"{c[0]:.2f}/{c[-1]:.2f}" if c else "-") for c in (ch[r] for r in ("r1", "r2", "r3"))]
        last = max((c[-1] for c in ch.values() if c), default=0)
        first = max((c[0] for c in ch.values() if c), default=0)
        print(f"{ev:<9} {run:>3}  {cells[0]:>13}  {cells[1]:>13}  {cells[2]:>13}  "
              f"{first:11.2f} s  {last:9.2f} s")
    print(f"          ({WHAT[ev]})")

print("""
silent: the first change (first-settled 30.8-31.7 s) is the dead timer firing;
the tables are right from then. The second change (~35 s) is r1 - alone on net_b, interface still
up - advertising net_b as its own stub again, which puts r3's ECMP via r1 back.
That route is wrong (r1's packets on net_b are dropped) and stays wrong - see
out/route-after-silent.txt: OSPF learned that r2 went silent, not that the wire
itself is useless, and the interface is still up.

scenario.sh cut (run once, raw output in out/scenario/) reported "재수렴 감지: 2 초".
It compares raw `show ip route` text, whose uptime column changes every second,
so it fires on the first 1 s poll whether or not a route moved - here the route
had in fact moved within 0.14 s, but the script cannot tell it apart.""")
