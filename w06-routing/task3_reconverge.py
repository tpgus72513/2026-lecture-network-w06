#!/usr/bin/env python3
"""Week 6 · Task 3 — Reconverge without recomputing the world.

Textbook §5.2.1, §5.3.

A link flaps. Every router in the area has to decide what changed. `FullRecompute`
does the honest thing: throw the table away and run Dijkstra again, from scratch,
for every event. It is correct and it is what the first implementations did.

It is also why a single flapping link in a large area used to melt the CPU of
every router that could see it.

Beat it:

    python3 bench.py
    python3 bench.py --yours

Correctness first. `bench.py` compares your table against a full recompute after
**every single event**. A router that is fast and wrong black-holes traffic.
"""
import heapq

# The harness counts how many times you run a full SPF. This is the score:
# wall-clock time in Python says more about dictionary overhead than about
# routing, but "how many times did the CPU have to recompute the world" is
# exactly what melted real routers.
SPF_RUNS = 0


def dijkstra_table(graph, source):
    """Reference shortest-path-first. Returns {destination: first_hop}.

    Use THIS function whenever you need a full recompute. Rolling your own to
    dodge the counter is not an optimisation, it is cheating the meter.
    """
    global SPF_RUNS
    SPF_RUNS += 1
    best = {source: (0, None)}
    pq, done = [(0, source, None)], set()
    while pq:
        cost, node, first_hop = heapq.heappop(pq)
        if node in done:
            continue
        done.add(node)
        best[node] = (cost, first_hop)
        for nbr, w in sorted(graph[node].items()):
            if nbr in done:
                continue
            hop = nbr if node == source else first_hop
            if cost + w < best.get(nbr, (float("inf"), None))[0]:
                best[nbr] = (cost + w, hop)
                heapq.heappush(pq, (cost + w, nbr, hop))
    return {d: h for d, (_, h) in best.items() if d != source and h}


class FullRecompute:
    """On every event, forget everything and run SPF again."""

    def __init__(self, graph, source):
        self.graph = {n: dict(e) for n, e in graph.items()}
        self.source = source
        self.table = dijkstra_table(self.graph, source)

    def link_change(self, a, b, cost):
        """cost=None means the link went down."""
        if cost is None:
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
        else:
            self.graph[a][b] = cost
            self.graph[b][a] = cost
        self.table = dijkstra_table(self.graph, self.source)


class YourRouter:
    """Keeps the cost to every node between events, and runs SPF only when a cost moves.

    State kept between events (besides the graph copy every router has):
      dist   {node: cost from source}, one number per router in the area.

    Every event is one link, so only two directed edges change, a->b and b->a.
    Call an edge u->v *tight* when dist[u] + w(u,v) == dist[v]: it lies on some
    shortest path to v. Weights are >= 1, so a tight predecessor is always
    strictly closer to the source, and following tight edges backwards always
    ends at the source.

      worse  (down, or cost up)    If the edge was not tight in either direction
             it carried no shortest path: nothing changes, no work at all. If it
             was tight but its far end still has another tight predecessor,
             every cost still stands (each node can still trace a tight chain
             home). Only when that end loses its last tight predecessor does
             some cost really grow - full SPF.
      better (up, or cost down)    dist[u] + w_new is compared with dist[v] using
             the costs already held. Larger: nothing gets shorter. Equal: no cost
             moves, but a new equal-cost path appeared. Smaller: v got shorter,
             and so may whatever is behind v - but costs only fall, and only
             along offers that beat a cost already held, so the update walks
             outward from v through the nodes that improve and stops at the first
             neighbour that does not (_shorten). Nothing else is touched.

    When costs stand but the set of tight edges changed, a tie may now break
    differently, so the next hops are re-derived from dist (no SPF - see
    _hops_from_dist). The one case that still forces a full SPF is a link that
    was the last shortest path to somewhere getting worse or going down: costs
    then grow, and which ones, and by how much, is the whole SPF question.
    Full recomputes go through dijkstra_table(), which installs the table; the
    cost pass in _full() belongs to that same recompute and never runs alone.
    """

    def __init__(self, graph, source):
        self.graph = {n: dict(e) for n, e in graph.items()}
        self.source = source
        self._full()

    def link_change(self, a, b, cost):
        """cost=None means the link went down."""
        old = self.graph[a].get(b)
        if cost == old:
            return
        if cost is None:
            self.graph[a].pop(b, None)
            self.graph[b].pop(a, None)
        else:
            self.graph[a][b] = cost
            self.graph[b][a] = cost
        d, inf = self.dist, float("inf")
        pairs = ((a, b), (b, a))

        if old is not None and (cost is None or cost > old):          # worse
            ends = [v for u, v in pairs if u in d and d[u] + old == d.get(v, inf)]
            if not ends:
                return
            if not all(self._has_tight_pred(v) for v in ends):
                return self._full()
        else:                                                          # better
            offers = [(d[u] + cost, v) for u, v in pairs
                      if u in d and d[u] + cost <= d.get(v, inf)]
            if not offers:
                return
            self._shorten([o for o in offers if o[0] < d.get(o[1], inf)])
        self.table = self._hops_from_dist()

    # ------------------------------------------------------------- helpers
    def _shorten(self, offers):
        """Lower costs that a better link has just undercut, and nothing else.

        offers are (new cost, node) pairs that beat the cost held for node. A
        node that improves offers its neighbours its new cost; a neighbour that
        is not beaten is left alone, and so is everything behind it.
        """
        d, inf = self.dist, float("inf")
        heapq.heapify(offers)
        while offers:
            c, v = heapq.heappop(offers)
            if c >= d.get(v, inf):
                continue
            d[v] = c
            for x, w in self.graph[v].items():
                if c + w < d.get(x, inf):
                    heapq.heappush(offers, (c + w, x))

    def _has_tight_pred(self, v):
        dv = self.dist[v]
        return v == self.source or any(
            self.dist.get(x, float("inf")) + w == dv for x, w in self.graph[v].items())

    def _hops_from_dist(self):
        """The table dijkstra_table() would build, read off the costs alone.

        dijkstra_table pops nodes in (cost, name) order and only replaces a
        destination's hop on a strictly cheaper offer. So a destination takes
        its hop from the tight predecessor that pops first - the one with the
        smallest (cost, name) - or is its own hop when that predecessor is the
        source. Walking nodes in that same order is a sort plus one pass over
        the edges; no costs are computed.
        """
        d, src, hop = self.dist, self.source, {}
        for v in sorted(d, key=lambda n: (d[n], n)):
            if v == src:
                continue
            p = min((x for x, w in self.graph[v].items() if d.get(x, -1) + w == d[v]),
                    key=lambda n: (d[n], n))
            hop[v] = v if p == src else hop[p]
        return hop

    def _full(self):
        """One full recompute: the counted SPF installs the table, and the
        same pass leaves the cost to every node for the next event."""
        self.table = dijkstra_table(self.graph, self.source)
        dist, pq = {}, [(0, self.source)]
        while pq:
            c, n = heapq.heappop(pq)
            if n in dist:
                continue
            dist[n] = c
            for m, w in self.graph[n].items():
                if m not in dist:
                    heapq.heappush(pq, (c + w, m))
        self.dist = dist
