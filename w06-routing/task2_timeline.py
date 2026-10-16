#!/usr/bin/env python3
"""Week 6 · Task 2 — read a raw-EVENT.log from task2_measure.sh, print the timeline.

For each router: every moment its OSPF routes changed, in seconds after the
event fired, and the routes it ended up with. "Converged" is the last change on
any router - after that, nobody's table moves again in the window.
"""
import sys

lines = open(sys.argv[1], encoding="utf-8").read().splitlines()
event, t0 = lines[0], float(lines[1].split()[1])
logs, cur = {}, None
for l in lines[2:]:
    if l.startswith("== "):
        cur = l[3:]; logs[cur] = []
    elif l.startswith("@ "):
        logs[cur].append([float(l[2:]), []])
    elif l != "@end" and logs[cur]:
        logs[cur][-1][1].append(l)

print(event)
last = 0.0
for r, snaps in logs.items():
    changes = [(t - t0, rt) for t, rt in snaps if t > t0]
    final = snaps[-1][1] if snaps else []
    when = ", ".join(f"+{dt:.2f}s" for dt, _ in changes) or "no change"
    print(f"  {r}: routes changed at {when}")
    for rt in final:
        print(f"      {rt}")
    if changes:
        last = max(last, changes[-1][0])
print(f"  converged: last table change {last:.2f} s after the event")
