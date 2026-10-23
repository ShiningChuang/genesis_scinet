"""Graph A · Protocol Graph: the quote branch (step 4). The reserve / commit branches join the same graph in step 5a.

    START → validate_bundle ─ok──► refresh_if_stale → find_placements → estimate_finish → respond → END
                            └fail────────────────────────────────────────────────────────► respond

A quote is read-only: it reserves no capacity and never calls SENSE. Its only write is refreshing
stale ``observed`` values in the ledger, which are observations, not bookings.

Nodes only orchestrate: they decide what runs in which order and where data flows. The actual
computation and rules live in placement.py, ledger.py and estimate.py; a node takes its inputs from
state, calls those modules, and writes the results back to state. Shared objects such as the ledger
come from runtime.context (see context.py).
"""

from datetime import datetime
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from pydantic import ValidationError

from ..context import AgentContext
from ..placement import Placement, dedupe, search
from ..schemas import (
    ErrorResponse, Offer, QuoteRequest, QuoteResponse, RateSegment, RejectReason, TransferQuote,
)
from ..topology import Path


class QuoteState(TypedDict, total=False):
    raw: dict                                     # input: the scheduling agent's request (JSON parsed into a dict)
    now: datetime                                 # input: current time, supplied by the caller (for tests and simulated clocks)
    request: QuoteRequest                         # written by validate_bundle
    paths: dict[str, list[Path]]                  # written by refresh_if_stale: transfer_id → candidate paths
    refreshed: list[str]                          # written by refresh_if_stale: links refreshed this time
    placements: dict[str, list[Placement]]        # written by find_placements: feasible placements
    rejections: dict[str, RejectReason]           # written by find_placements: why a transfer is infeasible
    offers: dict[str, list[Offer]]                # written by estimate_finish
    response: QuoteResponse | ErrorResponse       # output


# ── nodes ────────────────────────────────────────────────────────────────

def validate_bundle(state: QuoteState) -> dict:
    """Check format and internal consistency only (the rules in schemas.py); whether the request can be met is left to later nodes."""
    raw = state["raw"]
    try:
        return {"request": QuoteRequest.model_validate(raw)}
    except ValidationError as e:
        quote_id = raw.get("quote_id") if isinstance(raw, dict) else None
        return {"response": ErrorResponse(request_id=str(quote_id or "unknown"), code="invalid_request",
                                          detail="; ".join(err["msg"] for err in e.errors()))}


def refresh_if_stale(state: QuoteState, runtime: Runtime[AgentContext]) -> dict:
    """Find candidate paths for each transfer; for observations on those paths that are stale within the
    window, pull fresh samples from telemetry once and write them into the ledger."""
    ctx, now = runtime.context, state["now"]
    ledger = ctx.ledger
    paths: dict[str, list[Path]] = {}
    stale: dict[str, set[int]] = {}               # directed link → stale slot indices
    for tr in state["request"].bundle:
        try:
            paths[tr.id] = ctx.topology.paths(tr.src, tr.dst, ctx.cfg.max_paths)
        except KeyError:                          # endpoint not in the topology: treat as "no path"
            paths[tr.id] = []
        start = max(tr.window.earliest_start, now, ledger.origin)
        end = min(tr.window.latest_finish, ledger.horizon_end)
        if start >= end:
            continue
        for path in paths[tr.id]:
            for link in path:
                for i in ledger.slots_covering(start, end):
                    if ledger.is_stale(link, i, now):
                        stale.setdefault(link, set()).add(i)
    if stale:
        first = min(min(slots) for slots in stale.values())
        last = max(max(slots) for slots in stale.values())
        ledger.apply(ctx.telemetry.link_samples(sorted(stale), ledger.slot_start(first),
                                                ledger.slot_start(last + 1), now))
    return {"paths": paths, "refreshed": sorted(stale)}


def find_placements(state: QuoteState, runtime: Runtime[AgentContext]) -> dict:
    """Run placement.search once per transfer per candidate path; dedupe across paths, preferring shorter paths."""
    ctx = runtime.context
    placements: dict[str, list[Placement]] = {}
    rejections: dict[str, RejectReason] = {}
    for tr in state["request"].bundle:
        candidates = state["paths"][tr.id]
        if not candidates:
            rejections[tr.id] = RejectReason(cause="no_path", detail=f"no path from {tr.src} to {tr.dst}")
            continue
        found: list[Placement] = []
        reasons: list[RejectReason] = []
        for path in candidates:
            result = search(ctx.ledger, path, tr, state["now"], ctx.cfg.rate_step_gbps)
            if isinstance(result, RejectReason):
                reasons.append(result)
            else:
                found.extend(result)
        if found:
            placements[tr.id] = dedupe(found)
        else:
            rejections[tr.id] = reasons[0]        # report the shortest path's reason
    return {"placements": placements, "rejections": rejections}


def estimate_finish(state: QuoteState, runtime: Runtime[AgentContext]) -> dict:
    """Placement → offer: estimate p50 / p95 finish times with the rate model."""
    req = state["request"]
    nbytes = {tr.id: tr.bytes for tr in req.bundle}
    offers: dict[str, list[Offer]] = {}
    for tid, ps in state["placements"].items():
        offers[tid] = []
        for k, p in enumerate(ps, start=1):
            p50, p95 = runtime.context.rate_model.predict_finish(p, nbytes[tid])
            offers[tid].append(Offer(
                offer_id=f"{req.quote_id}/{tid}/{k}", transfer_id=tid,
                rate_profile=[RateSegment(start=p.start, end=p.end, gbps=p.gbps)],
                predicted_finish_p50=p50, predicted_finish_p95=p95, blocked_by=p.blocked_by))
    return {"offers": offers}


def respond(state: QuoteState, runtime: Runtime[AgentContext]) -> dict:
    """Assemble the QuoteResponse; record offer_id → placement in offer_book so that reserve (step 5a)
    can look up the path by id."""
    if "response" in state:                       # validation failed; an ErrorResponse is already set
        return {}
    req = state["request"]
    results = []
    for tr in req.bundle:
        if tr.id in state["offers"]:
            offers = state["offers"][tr.id]
            for offer, p in zip(offers, state["placements"][tr.id]):
                runtime.context.offer_book[offer.offer_id] = p
            results.append(TransferQuote(transfer_id=tr.id, status="feasible", offers=offers))
        else:
            reason = state["rejections"][tr.id]
            status = "unreachable" if reason.cause == "no_path" else "infeasible"
            results.append(TransferQuote(transfer_id=tr.id, status=status, reason=reason))
    return {"response": QuoteResponse(quote_id=req.quote_id, mode=req.mode, results=results)}


# ── edges ────────────────────────────────────────────────────────────────

def after_validate(state: QuoteState) -> str:
    return "respond" if "response" in state else "refresh_if_stale"


def build_quote_graph():
    g = StateGraph(QuoteState, context_schema=AgentContext)
    g.add_node("validate_bundle", validate_bundle)
    g.add_node("refresh_if_stale", refresh_if_stale)
    g.add_node("find_placements", find_placements)
    g.add_node("estimate_finish", estimate_finish)
    g.add_node("respond", respond)
    g.add_edge(START, "validate_bundle")
    g.add_conditional_edges("validate_bundle", after_validate, ["refresh_if_stale", "respond"])
    g.add_edge("refresh_if_stale", "find_placements")
    g.add_edge("find_placements", "estimate_finish")
    g.add_edge("estimate_finish", "respond")
    g.add_edge("respond", END)
    return g.compile()
