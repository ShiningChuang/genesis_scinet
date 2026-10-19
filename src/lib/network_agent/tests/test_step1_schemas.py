"""Step 1:消息 schema。合法消息能构造并能经 JSON 往返;不合法消息在入口被拒。

用例取 slide 7:T1 = 50 TB,窗口 09:00–15:00;offer a2 = 12:00 起 100 Gbps,13:07 完成。
"""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from src.lib.network_agent.schemas import (
    CommitAck, Commitment, EndpointBinding, Offer, QuoteRequest, QuoteResponse,
    RateSegment, RejectReason, ReserveRequest, TimeWindow, TransferQuote, TransferRequest,
)
from src.lib.network_agent.tests.helpers import t


def t1(**over):
    base = dict(id="T1", workflow_id="WF-1", priority=1, src="anl-dtn01", dst="ornl-esgf",
                bytes=50 * 10**12, is_estimate=False, divisible=False,
                window=TimeWindow(earliest_start=t(9), latest_finish=t(15)))
    return TransferRequest(**(base | over))


def a2(**over):
    base = dict(offer_id="a2", transfer_id="T1",
                rate_profile=[RateSegment(start=t(12), end=t(13, 7), gbps=100)],
                predicted_finish_p50=t(13, 7), predicted_finish_p95=t(13, 20))
    return Offer(**(base | over))


# ── 合法消息 ──────────────────────────────────────────────────────────────

def test_valid_quote_roundtrip_json():
    q = QuoteRequest(quote_id="q1", bundle=[t1(), t1(id="T2")], mode="all_or_nothing")
    assert QuoteRequest.model_validate_json(q.model_dump_json()) == q


def test_offer_start_is_first_segment():
    assert a2().start == t(12)


def test_commit_ack_roundtrip_json():
    b = EndpointBinding(transfer_id="T1", src_uri="urn:anl", dst_uri="urn:ornl", vlan=3001, interface="eth1")
    c = Commitment(commitment_id="c1", transfer_id="T1", workflow_id="WF-1", circuit_id="C1",
                   rate_profile=a2().rate_profile, binding=b)
    ack = CommitAck(reserve_id="r1", commitments=[c])
    assert CommitAck.model_validate_json(ack.model_dump_json()) == ack


# ── 不合法消息被拒 ────────────────────────────────────────────────────────

@pytest.mark.parametrize("make", [
    lambda: TimeWindow(earliest_start=t(15), latest_finish=t(9)),                     # 时间窗颠倒
    lambda: TimeWindow(earliest_start=datetime(2026, 10, 20, 9), latest_finish=t(15)),  # 无时区
    lambda: t1(bytes=0),                                                              # 字节数非正
    lambda: t1(dst="anl-dtn01"),                                                      # src == dst
    lambda: t1(color="red"),                                                          # 未知字段
    lambda: QuoteRequest(quote_id="q", bundle=[], mode="best_subset"),                # 空 bundle
    lambda: QuoteRequest(quote_id="q", bundle=[t1(), t1()], mode="best_subset"),      # 重复 transfer id
    lambda: QuoteRequest(quote_id="q", bundle=[t1()], mode="some"),                   # 非法 mode
    lambda: RateSegment(start=t(12), end=t(12), gbps=10),                             # 空时间段
    lambda: RateSegment(start=t(12), end=t(13), gbps=0),                              # 速率非正
    lambda: a2(rate_profile=[RateSegment(start=t(12), end=t(13), gbps=10),
                             RateSegment(start=t(12, 30), end=t(14), gbps=10)]),      # 时间段重叠
    lambda: a2(predicted_finish_p95=t(13)),                                           # p95 < p50
    lambda: a2(predicted_finish_p50=t(11), predicted_finish_p95=t(11)),               # 完成早于开始
    lambda: ReserveRequest(request_id="r", quote_id="q", offer_ids=["a2", "a2"]),     # 重复 offer
    lambda: EndpointBinding(transfer_id="T1", src_uri="u", dst_uri="v", vlan=5000, interface="e"),
])
def test_rejected(make):
    with pytest.raises(ValidationError):
        make()


def test_frozen():
    with pytest.raises(ValidationError):
        t1().bytes = 1


# ── 报价结果的自洽性 ──────────────────────────────────────────────────────

def test_transfer_quote_consistency():
    no_cap = RejectReason(cause="no_capacity", detail="window full")
    TransferQuote(transfer_id="T1", status="feasible", offers=[a2()])
    TransferQuote(transfer_id="T1", status="infeasible", reason=no_cap)
    with pytest.raises(ValidationError):
        TransferQuote(transfer_id="T1", status="feasible")                    # 可行却没有 offer
    with pytest.raises(ValidationError):
        TransferQuote(transfer_id="T1", status="infeasible")                  # 不可行却没有原因
    with pytest.raises(ValidationError):
        TransferQuote(transfer_id="T2", status="feasible", offers=[a2()])     # offer 属于别的传输


def test_admissible_depends_on_mode():
    ok = TransferQuote(transfer_id="T1", status="feasible", offers=[a2()])
    bad = TransferQuote(transfer_id="T2", status="unreachable",
                        reason=RejectReason(cause="no_path", detail="no route"))
    assert not QuoteResponse(quote_id="q", mode="all_or_nothing", results=[ok, bad]).admissible
    assert QuoteResponse(quote_id="q", mode="best_subset", results=[ok, bad]).admissible
    assert not QuoteResponse(quote_id="q", mode="best_subset", results=[bad]).admissible


def test_slide7_arithmetic():
    """slide 7 的时间算术:50 TB 在 100 Gbps 下需 4000 s(≈ 1 h 07 min)。"""
    seconds = t1().bytes * 8 / (100 * 10**9)
    assert t(12) + timedelta(seconds=seconds) == t(13, 6) + timedelta(seconds=40)
