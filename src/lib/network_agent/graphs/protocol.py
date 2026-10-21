"""图 A · Protocol Graph:quote 分支(第 4 步)。reserve / commit 分支在第 5a 步加到同一张图上。

    START → validate_bundle ─ok──► refresh_if_stale → find_placements → estimate_finish → respond → END
                            └fail────────────────────────────────────────────────────────► respond

quote 是只读的:不预扣容量,不调用 SENSE。唯一的写入是刷新账本里过期的 observed,
那是观测,不是预订。

节点只做编排:业务逻辑在 placement.py、ledger.py、estimate.py 里,节点负责从 state 取输入、
调用它们、把结果写回 state。账本等共用对象从 runtime.context 取(见 context.py)。
图里的节点只负责"按什么顺序做、数据从哪来到哪去"，真正的计算和规则写在别的文件里，节点去调用它们。
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
    raw: dict                                     # 输入:scheduling agent 发来的请求(JSON 解析后的 dict)
    now: datetime                                 # 输入:当前时刻,由调用方给(便于测试和模拟时钟)
    request: QuoteRequest                         # validate_bundle 写
    paths: dict[str, list[Path]]                  # refresh_if_stale 写:transfer_id → 候选路径
    refreshed: list[str]                          # refresh_if_stale 写:这次刷新了哪些链路
    placements: dict[str, list[Placement]]        # find_placements 写:可行方案
    rejections: dict[str, RejectReason]           # find_placements 写:不可行的原因
    offers: dict[str, list[Offer]]                # estimate_finish 写
    response: QuoteResponse | ErrorResponse       # 输出


# ── 节点 ─────────────────────────────────────────────────────────────────

def validate_bundle(state: QuoteState) -> dict:
    """只检查格式与自洽(schemas.py 里的规则);能否满足交给后面的节点。"""
    raw = state["raw"]
    try:
        return {"request": QuoteRequest.model_validate(raw)}
    except ValidationError as e:
        quote_id = raw.get("quote_id") if isinstance(raw, dict) else None
        return {"response": ErrorResponse(request_id=str(quote_id or "unknown"), code="invalid_request",
                                          detail="; ".join(err["msg"] for err in e.errors()))}


def refresh_if_stale(state: QuoteState, runtime: Runtime[AgentContext]) -> dict:
    """找出每条传输的候选路径;路径上、窗口内过期的观测值,向 telemetry 拉一次新的写进账本。"""
    ctx, now = runtime.context, state["now"]
    ledger = ctx.ledger
    paths: dict[str, list[Path]] = {}
    stale: dict[str, set[int]] = {}               # 有向链路 → 过期的槽号
    for tr in state["request"].bundle:
        try:
            paths[tr.id] = ctx.topology.paths(tr.src, tr.dst, ctx.cfg.max_paths)
        except KeyError:                          # 端点不在拓扑里:按"没有路径"处理
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
    """每条传输、每条候选路径跑一次 placement.search;跨路径去重,短路径的方案优先。"""
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
            rejections[tr.id] = reasons[0]        # 报最短路径的原因
    return {"placements": placements, "rejections": rejections}


def estimate_finish(state: QuoteState, runtime: Runtime[AgentContext]) -> dict:
    """方案 → offer:用 rate model 估 p50 / p95 完成时间。"""
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
    """组装 QuoteResponse;把 offer_id → 方案记进 offer_book,第 5a 步 reserve 时按 id 取回路径。"""
    if "response" in state:                       # validate 失败,已经有 ErrorResponse
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


# ── 边 ───────────────────────────────────────────────────────────────────

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
