"""Step 4: the quote branch of graph A. The core case reproduces slide 7:

    T1 = 50 TB, window 09:00–15:00; ledger: only 40 Gbps left before 12:00, fully free 100 Gbps after.
    a1 09:00 @ 40 Gbps → 11:46:40   (slide says 13:47; the arithmetic gives 11:47, see PLAN open items)
    a2 12:00 @ 100 Gbps → 13:06:40  (slide 13:07)
    a3 09:00 @ 20 Gbps → 14:33:20   (slide 14:34)
"""

from datetime import timedelta

import pytest

from ..config import load_config
from ..context import AgentContext
from ..estimate import IdealRateModel
from ..graphs.protocol import build_quote_graph
from ..ledger import CapacityLedger
from ..schemas import QuoteRequest, RateSegment, TimeWindow, TransferRequest
from ..sim import MockNetwork
from ..telemetry import MockTelemetry
from ..topology import Topology
from .helpers import CFG, DST, L2, MAIN, SRC, TOPO, t


class CountingTelemetry(MockTelemetry):
    calls = 0

    def link_samples(self, *args, **kwargs):
        self.calls += 1
        return super().link_samples(*args, **kwargs)


def make_net(foreign_gbps=60):
    """The slide-7 network: before 12:00 others use foreign_gbps on L2 (default 60, leaving 40 Gbps)."""
    n = MockNetwork(Topology.from_dict(TOPO))
    n.add_foreign(L2, t(9), t(12), foreign_gbps)
    return n


def make_ctx(net):
    cfg = load_config(CFG)
    return AgentContext(cfg=cfg, topology=net.topology, ledger=CapacityLedger(net.topology, cfg, origin=t(9)),
                        telemetry=CountingTelemetry(net, validity_seconds=300), rate_model=IdealRateModel())


@pytest.fixture
def net():
    return make_net()


@pytest.fixture
def ctx(net):
    return make_ctx(net)


@pytest.fixture
def graph():
    return build_quote_graph()


def tr(id="T1", src=SRC, dst=DST, nbytes=50 * 10**12, window=(t(9), t(15)), **over):
    return TransferRequest(id=id, workflow_id="WF-1", priority=1, src=src, dst=dst, bytes=nbytes,
                           is_estimate=False, divisible=False,
                           window=TimeWindow(earliest_start=window[0], latest_finish=window[1]), **over)


def quote(graph, ctx, *transfers, mode="all_or_nothing", now=t(9)):
    raw = QuoteRequest(quote_id="q1", bundle=list(transfers), mode=mode).model_dump()
    return graph.invoke({"raw": raw, "now": now}, context=ctx)


def summary(offer):
    seg = offer.rate_profile[0]
    return seg.start, seg.gbps, offer.predicted_finish_p50


# ── slide 7 ──────────────────────────────────────────────────────────────

def test_slide7_three_offers(graph, ctx):
    resp = quote(graph, ctx, tr())["response"]
    assert resp.admissible
    offers = resp.results[0].offers
    assert [summary(o) for o in offers] == [
        (t(9), 40, t(11, 46) + timedelta(seconds=40)),
        (t(12), 100, t(13, 6) + timedelta(seconds=40)),
        (t(9), 20, t(14, 33) + timedelta(seconds=20)),
    ]
    assert [o.blocked_by for o in offers] == ["foreign_traffic", None, None]
    assert [o.offer_id for o in offers] == ["q1/T1/1", "q1/T1/2", "q1/T1/3"]


def test_offers_are_kept_for_reserve(graph, ctx):
    quote(graph, ctx, tr())
    assert set(ctx.offer_book) == {"q1/T1/1", "q1/T1/2", "q1/T1/3"}
    assert ctx.offer_book["q1/T1/2"].path == MAIN


# ── refresh_if_stale ─────────────────────────────────────────────────────

def test_refresh_pulls_telemetry_into_ledger(graph, ctx):
    assert ctx.ledger.observed(L2, 0).source == "topology"
    out = quote(graph, ctx, tr())
    assert L2 in out["refreshed"]
    assert (ctx.ledger.observed(L2, 0).gbps, ctx.ledger.observed(L2, 0).source) == (40, "mock")
    assert ctx.telemetry.calls == 1


def test_fresh_values_are_not_refetched(graph, ctx):
    quote(graph, ctx, tr())
    out = quote(graph, ctx, tr(), now=t(9, 1))    # samples are valid for 5 minutes, still fresh after 1
    assert out["refreshed"] == [] and ctx.telemetry.calls == 1


def test_quote_is_read_only(graph, ctx):
    quote(graph, ctx, tr())
    assert all(ctx.ledger.own(link, i) == 0 for link in MAIN for i in range(ctx.ledger.n_slots))


# ── blocked_by: blocked by our own bookings ───────────────────────────────

def test_blocked_by_own_commitment(net, graph, ctx):
    """Remove foreign traffic and book 30 ourselves on the main path instead: the earliest start can only get 70, because of own_commitment."""
    net._foreign[L2].clear()
    ctx.ledger.pending("ours", MAIN, [RateSegment(start=t(9), end=t(12), gbps=30)])
    first = quote(graph, ctx, tr())["response"].results[0].offers[0]
    assert (first.rate_profile[0].gbps, first.blocked_by) == (70, "own_commitment")


# ── the four rejection cases ──────────────────────────────────────────────

@pytest.mark.parametrize("transfer, status, cause", [
    (tr(dst="mars"), "unreachable", "no_path"),
    (tr(window=(t(9), t(9, 30))), "infeasible", "no_capacity"),                    # 50 TB in 30 minutes
    (tr(window=(t(10, day=21), t(12, day=21))), "infeasible", "beyond_horizon"),    # the ledger only reaches 09:00 next day
    (tr(nbytes=10 * 10**12, window=(t(9), t(11)), min_useful_rate_gbps=60),             # 40 Gbps would finish,
     "infeasible", "below_min_useful_rate"),                                          # but is below the declared 60
])
def test_rejections(graph, ctx, transfer, status, cause):
    result = quote(graph, ctx, transfer)["response"].results[0]
    assert (result.status, result.reason.cause) == (status, cause)


def test_now_clips_earliest_start(graph, ctx):
    offers = quote(graph, ctx, tr(), now=t(10, 5))["response"].results[0].offers
    assert min(o.rate_profile[0].start for o in offers) == t(10, 5)


# ── bundle and mode ───────────────────────────────────────────────────────

def test_mode_decides_admissible(graph, ctx):
    bundle = [tr(), tr(id="T2", dst="mars")]
    assert not quote(graph, ctx, *bundle, mode="all_or_nothing")["response"].admissible
    assert quote(graph, ctx, *bundle, mode="best_subset")["response"].admissible


# ── exit for failed validation ────────────────────────────────────────────

def test_invalid_request_goes_straight_to_respond(graph, ctx):
    raw = QuoteRequest(quote_id="q9", bundle=[tr()], mode="best_subset").model_dump()
    raw["bundle"][0]["window"] = {"earliest_start": t(15), "latest_finish": t(9)}   # window reversed
    out = graph.invoke({"raw": raw, "now": t(9)}, context=ctx)
    assert (out["response"].code, out["response"].request_id) == ("invalid_request", "q9")
    assert "refreshed" not in out and ctx.telemetry.calls == 0


def test_graph_shape(graph):
    nodes = set(graph.get_graph().nodes)
    assert {"validate_bundle", "refresh_if_stale", "find_placements", "estimate_finish", "respond"} <= nodes


# ── demo: print the full scenario and quote result ────────────────────────
#
# How to run (from the repository root), with one scenario as the argument:
#   genesis_scinet:        .venv/bin/python -m src.lib.network_agent.tests.test_step4_quote_graph test1
#   kklab_scinet_agents:   python -m network_agent.tests.test_step4_quote_graph test1
# scenarios: test1 / test2 / test3

SCENARIOS = {
    "test1": ("Slide 7 as drawn: foreign traffic takes 60 Gbps on L2 until 12:00; deadline 15:00", dict(foreign_gbps=60, deadline=t(15))),
    "test2": ("Variant 1: foreign traffic takes only 20 Gbps (80 Gbps left until 12:00)", dict(foreign_gbps=20, deadline=t(15))),
    "test3": ("Variant 2: deadline moved up to 13:00", dict(foreign_gbps=60, deadline=t(13))),
}


def hops(topology, path):
    """Directed link id sequence → 'anl-n02 ─L1→ esnet-atl ─L2→ ...'"""
    links = [topology.links[d] for d in path]
    return links[0].src + "".join(f" ─{d.link_id}→ {d.dst}" for d in links)


def availability_runs(ledger, path, start, end):
    """A path's available capacity over [start, end), merging adjacent equal runs: [(start, end, Gbps, bottleneck link)]."""
    runs = []
    for i in ledger.slots_covering(start, end):
        gbps, link = ledger.path_available(path, i)
        a, b = ledger.slot_start(i), ledger.slot_start(i + 1)
        if runs and runs[-1][2:] == (gbps, link):
            runs[-1] = (runs[-1][0], b, gbps, link)
        else:
            runs.append((a, b, gbps, link))
    return runs


def print_scenario(title, net, ctx, req, now, out):
    topo = net.topology
    print(f"\n{'=' * 100}\n{title}\n{'=' * 100}")
    print("Nodes:", ", ".join(topo.nodes))
    print("Links (physical; capacity is per direction):")
    printed = set()
    for d in topo.links.values():                           # print each physical link once, in its defined a → b direction
        if d.link_id not in printed:
            printed.add(d.link_id)
            print(f"  {d.link_id}: {d.src} — {d.dst}   {d.capacity_gbps:g} Gbps")
    print("Foreign traffic:")
    for link, ivs in net._foreign.items():
        for iv in ivs:
            print(f"  {link}   {iv.start:%H:%M}–{iv.end:%H:%M}   {iv.gbps:g} Gbps")
    print("Outages:", [f"{link} {iv.start:%H:%M}–{iv.end:%H:%M}" for link, ivs in net._outages.items() for iv in ivs] or "none")

    print(f"\nRequest {req.quote_id} (mode={req.mode}), now = {now:%H:%M}:")
    for tr_ in req.bundle:
        w = tr_.window
        print(f"  {tr_.id}: {tr_.src} → {tr_.dst}, {tr_.bytes / 1e12:g} TB, "
              f"window {w.earliest_start:%H:%M}–{w.latest_finish:%H:%M}")

    print("\nCandidate paths, with available capacity per time range after refresh (narrowest hop):")
    path_no = {}
    for tr_ in req.bundle:
        for k, path in enumerate(out["paths"][tr_.id], start=1):
            path_no[path] = k
            print(f"  path{k}: {hops(topo, path)}")
            for a, b, gbps, link in availability_runs(ctx.ledger, path, tr_.window.earliest_start,
                                                      min(tr_.window.latest_finish, ctx.ledger.horizon_end)):
                print(f"      {a:%H:%M}–{b:%H:%M}   {gbps:>5g} Gbps   bottleneck {link}")
    print("Links refreshed:", out["refreshed"])

    resp = out["response"]
    print(f"\nQuote result: admissible = {resp.admissible}")
    for r in resp.results:
        if r.status != "feasible":
            print(f"  {r.transfer_id}: {r.status} ({r.reason.cause}: {r.reason.detail})")
        for o in r.offers:
            s, p = o.rate_profile[0], ctx.offer_book[o.offer_id]   # offer_book holds the path and rule that are not exposed externally
            print(f"  {o.offer_id}: start {s.start:%H:%M} @ {s.gbps:>5g} Gbps → finish {o.predicted_finish_p50:%H:%M:%S}"
                  f"   [path{path_no[p.path]}, rule {p.strategy}]   blocked_by={o.blocked_by}")


def demo(title=SCENARIOS["test1"][0], foreign_gbps=60, deadline=t(15)):
    net = make_net(foreign_gbps)
    ctx = make_ctx(net)
    transfer = tr(window=(t(9), deadline))
    out = quote(build_quote_graph(), ctx, transfer)
    req = QuoteRequest(quote_id="q1", bundle=[transfer], mode="all_or_nothing")
    print_scenario(title, net, ctx, req, t(9), out)
    return out


def test_demo_printout():
    for title, kwargs in SCENARIOS.values():
        assert demo(title, **kwargs)["response"].admissible


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2 or sys.argv[1] not in SCENARIOS:
        print(f"Usage: python -m {__spec__.name} <scenario>")
        for name, (title, _) in SCENARIOS.items():
            print(f"  {name}   {title}")
        sys.exit(1)
    title, kwargs = SCENARIOS[sys.argv[1]]
    demo(title, **kwargs)
