#!/usr/bin/env python3
"""Week 6 · Task 1 — what the table at u looks like, and where it hides a tie.

    python3 task1_ties.py > out/task1-ties.txt

For each destination: the cost, the hop my rule installs, and every neighbour
that also starts a shortest path (what an ECMP router would install instead).
"""
from task1_linkstate import TOPOLOGY, dijkstra, forwarding_table, link_down


def equal_cost_hops(graph, source, dest):
    """Neighbours n of source with cost(source,n) + dist(n,dest) == dist(source,dest)."""
    best = dijkstra(graph, source)[dest]
    return sorted(n for n, w in graph[source].items()
                  if w + ({n: 0} | dijkstra(graph, n)).get(dest, float("inf")) == best)


def show(graph, title):
    cost, table = dijkstra(graph, "u"), forwarding_table(graph, "u")
    print(f"== {title}")
    print(f"  {'dest':<5} {'cost':>4}  {'installed':<9}  all equal-cost first hops")
    for d in sorted(table):
        hops = equal_cost_hops(graph, "u", d)
        print(f"  {d:<5} {cost[d]:>4}  {table[d]:<9}  {', '.join(hops)}"
              + ("   <- tie" if len(hops) > 1 else ""))
    print()
    return table


before = show(TOPOLOGY, "intact topology, router u")
print(f"  direct link u-w costs {TOPOLOGY['u']['w']}; "
      f"u-x-y-w costs {TOPOLOGY['u']['x'] + TOPOLOGY['x']['y'] + TOPOLOGY['y']['w']}\n")
after = show(link_down(TOPOLOGY, "u", "x"), "after u-x fails, router u")
print("== hop changes at u")
for d in sorted(before):
    print(f"  {d}: {before[d]} -> {after[d]}" + ("" if before[d] != after[d] else "   (unchanged)"))
