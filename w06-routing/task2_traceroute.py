#!/usr/bin/env python3
"""Week 6 · Task 2 Part A — the three traceroutes, saved as UTF-8.

    python3 task2_traceroute.py > out/traceroute.txt
    python3 task2_traceroute.py www.snu.ac.kr >> out/traceroute.txt   # only these

Windows tracert prints in the console code page (cp949 here), so `| tee` would
save mojibake; this runs it and decodes. Hostnames are kept (no -d): the city
names in them are how A3's ocean crossing is read.

www.stanford.edu resolves to AWS Global Accelerator (itself anycast), so the
"overseas" path to it may end at a nearby edge. web.stanford.edu is in
Stanford's own 171.64.0.0/14 and is traced as well, to see a real crossing.
"""
import datetime, platform, socket, subprocess, sys

TARGETS = [("domestic", "www.korea.ac.kr"),
           ("overseas, as given", "www.stanford.edu"),
           ("overseas, Stanford's own network", "web.stanford.edu"),
           ("anycast", "1.1.1.1"),
           ("domestic, outside KU", "www.snu.ac.kr")]


def run(*cmd):
    out = subprocess.run(cmd, capture_output=True, timeout=600).stdout
    for enc in ("utf-8", "cp949"):
        try:
            return out.decode(enc)
        except UnicodeDecodeError:
            pass
    return out.decode("latin-1")


print(f"# {datetime.datetime.now():%Y-%m-%d %H:%M}  from campus Wi-Fi (KUWIFI)")
for label, host in [t for t in TARGETS if not sys.argv[1:] or t[1] in sys.argv[1:]]:
    addrs = sorted({a[4][0] for a in socket.getaddrinfo(host, 80, socket.AF_INET)})
    print(f"\n===== {label}: {host}  resolves to {', '.join(addrs)}")
    if platform.system() == "Windows":
        print(run("tracert", "-4", "-h", "30", "-w", "1500", host).strip())
    else:
        print(run("traceroute", "-4", "-m", "30", "-w", "2", host).strip())
