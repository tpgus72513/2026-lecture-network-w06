#!/usr/bin/env bash
# Week 6 · Task 2 B/C — time a routing event to 0.1 s, on all three routers.
#
#   bash w06-routing/task2_measure.sh snapshot FILE    all three OSPF tables -> FILE
#   bash w06-routing/task2_measure.sh EVENT [SECONDS]  run one event and time it
#
# EVENT is one of
#   cut      r1 eth1 (net_b) link down        - what scenario.sh cut does
#   restore  r1 eth1 link up                  - what scenario.sh restore does
#   silent   r1 drops every packet on eth1, link stays up (a dead fibre, a hung box)
#   unsilent stop dropping
#   cost     r1 eth0 (net_a) cost 10 -> 100   - what scenario.sh cost does
#   uncost   r1 eth0 cost back to 10
#
# scenario.sh polls r1 alone, once a second, and compares raw `show ip route`
# output - which contains each route's uptime, so it "changes" every second
# whether or not a route moved. This script instead runs a poller inside every
# router every 0.1 s, strips the uptime column, and logs a timestamp only when a
# route really changes. The routers share one kernel, so /proc/uptime is one
# clock for all three; the event's own timestamp is read from it inside r1, in
# the same command that fires the event.
set -u
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.." || exit 1
DC="docker compose --profile routing"
OUT=w06-routing/out; mkdir -p "$OUT"

routes='vtysh -c "show ip route ospf" 2>/dev/null | sed -n "/^\$/,\$p" | sed "/^\$/d"'
key="$routes"' | sed -E "s/, [^,]+\$//"'

snapshot() {
  for r in r1 r2 r3; do
    echo "===== $r ====="
    $DC exec -T $r sh -c "$routes"
  done
}

[ "${1:-}" = snapshot ] && { snapshot > "$2"; cat "$2"; exit 0; }

EVENT=${1:?event}; SECS=${2:-20}
case $EVENT in
  cut)      ACT="ip link set eth1 down" ;;
  restore)  ACT="ip link set eth1 up" ;;
  silent)   ACT="iptables -A INPUT -i eth1 -j DROP && iptables -A OUTPUT -o eth1 -j DROP" ;;
  unsilent) ACT="iptables -D INPUT -i eth1 -j DROP && iptables -D OUTPUT -o eth1 -j DROP" ;;
  cost)     ACT="vtysh -c 'configure terminal' -c 'interface eth0' -c 'ip ospf cost 100'" ;;
  uncost)   ACT="vtysh -c 'configure terminal' -c 'interface eth0' -c 'ip ospf cost 10'" ;;
  *) echo "unknown event $EVENT"; exit 1 ;;
esac

LOOP='end=$(( $(date +%s) + '$((SECS + 3))' )); prev=""
while [ $(date +%s) -lt $end ]; do
  cur=$('"$key"')
  if [ "$cur" != "$prev" ]; then echo "@ $(cut -d" " -f1 /proc/uptime)"; echo "$cur"; prev=$cur; fi
  sleep 0.1
done; echo "@end"'
for r in r1 r2 r3; do $DC exec -T -d $r sh -c "{ $LOOP
} > /tmp/poll.log 2>&1"; done
sleep 2
T0=$($DC exec -T r1 sh -c "cut -d\" \" -f1 /proc/uptime; $ACT >/dev/null")
sleep $((SECS + 2))
{
  echo "event $EVENT on r1: $ACT"
  echo "t0 $T0"
  for r in r1 r2 r3; do echo "== $r"; $DC exec -T $r cat /tmp/poll.log; done
} > "$OUT/raw-$EVENT.log"
python3 w06-routing/task2_timeline.py "$OUT/raw-$EVENT.log" 2>/dev/null \
  || python w06-routing/task2_timeline.py "$OUT/raw-$EVENT.log"
