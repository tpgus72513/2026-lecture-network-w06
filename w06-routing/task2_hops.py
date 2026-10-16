#!/usr/bin/env python3
"""Week 6 · Task 2 Part A — evidence behind the hop names used in the report.

    python3 task2_hops.py > out/hop-evidence.txt

tracert -d style addresses carry no city names here, so each key hop's owner
is looked up in RDAP (rdap.org). Also: which Cloudflare site answers 1.1.1.1
(its /cdn-cgi/trace page), and whether 1.1.1.1 answers ping from this network.
"""
import datetime, json, platform, subprocess, urllib.request

HOPS = ["163.152.233.129", "163.152.205.206", "175.121.235.141", "39.120.4.162",
        "211.45.68.29", "211.56.189.162", "141.101.82.17", "218.100.9.26",
        "184.104.197.109", "171.64.255.228", "211.108.22.106", "147.46.254.187"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "w06-lab"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")


def sh(*cmd):
    out = subprocess.run(cmd, capture_output=True, timeout=120).stdout
    for enc in ("utf-8", "cp949"):
        try:
            return out.decode(enc)
        except UnicodeDecodeError:
            pass
    return out.decode("latin-1")


print(f"# {datetime.datetime.now():%Y-%m-%d %H:%M}  from campus Wi-Fi (KUWIFI)\n")
print("== RDAP owner of each hop")
for ip in HOPS:
    try:
        d = json.loads(get(f"https://rdap.org/ip/{ip}"))
        desc = "; ".join(" ".join(r.get("description", [])) for r in d.get("remarks", []))[:60]
        print(f"  {ip:<16} {d.get('name')!s:<16} {d.get('country')!s:<3} "
              f"{d.get('startAddress')} - {d.get('endAddress')}  {desc}")
    except Exception as e:
        print(f"  {ip:<16} lookup failed: {e!r}")

print("\n== https://1.1.1.1/cdn-cgi/trace (which Cloudflare site answered)")
for line in get("https://1.1.1.1/cdn-cgi/trace").splitlines():
    if line.split("=")[0] in ("colo", "loc", "http", "tls"):
        print("  " + line)

print("\n== ping 1.1.1.1")
n = "-n" if platform.system() == "Windows" else "-c"
print(sh("ping", n, "4", "1.1.1.1").strip())
