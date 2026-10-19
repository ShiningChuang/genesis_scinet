"""Scheduling agent ↔ network agent 的消息(slides 6、7、19)。

本文件含 planning 闭环 quote → reserve → commit 用到的消息,以及 telemetry 样本(第 3a 步);其余消息在第一次用到的那一步再加
(ServiceIntent / ServiceState → 第 3b 步,modify / release → 第 5b 步,
repaired / at_risk → 第 7 步,TransferRecord → 第 9 步)。

所有消息都是不可变的 pydantic 模型,未知字段一律拒绝:agent 之间走 JSON,
坏消息在入口就被拦下,不会流进账本。校验只管"格式与自洽",不管"能否满足"——
后者是 find_placements 的事。
"""

from datetime import datetime
from typing import Literal

from pydantic import (
    AwareDatetime, BaseModel, ConfigDict, NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt, model_validator,
)


class Msg(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _unique(ids: list[str], what: str) -> None:
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise ValueError(f"duplicate {what}: {dup}")


# ── quote ────────────────────────────────────────────────────────────────

class TimeWindow(Msg):
    earliest_start: AwareDatetime
    latest_finish: AwareDatetime

    @model_validator(mode="after")
    def _ordered(self):
        if self.earliest_start >= self.latest_finish:
            raise ValueError("earliest_start must be before latest_finish")
        return self


class TransferRequest(Msg):
    """一次传输的需求,而不是路由:"这些字节必须在 t1 之后开始、t2 之前结束"(slide 6)。"""

    id: str
    workflow_id: str
    priority: NonNegativeInt                          # 越大越重要
    src: str                                          # 站点/端点 id,对应拓扑里的节点
    dst: str
    bytes: PositiveInt
    is_estimate: bool                                 # True:大小是估计值,运行时会被 refine
    divisible: bool                                   # 能否拆成多段/多路径传输
    window: TimeWindow
    min_useful_rate_gbps: PositiveFloat | None = None  # 低于此速率的 offer 没有意义(slide 19)

    @model_validator(mode="after")
    def _distinct_ends(self):
        if self.src == self.dst:
            raise ValueError("src and dst must differ")
        return self


class QuoteRequest(Msg):
    """一次询问一个 bundle;只读,不预留任何东西(slide 6)。"""

    quote_id: str
    bundle: list[TransferRequest]
    mode: Literal["all_or_nothing", "best_subset"]

    @model_validator(mode="after")
    def _bundle_ok(self):
        if not self.bundle:
            raise ValueError("bundle must not be empty")
        _unique([t.id for t in self.bundle], "transfer id")
        return self


class RateSegment(Msg):
    """时间段 [start, end) 内以 gbps 速率传输。"""

    start: AwareDatetime
    end: AwareDatetime
    gbps: PositiveFloat

    @model_validator(mode="after")
    def _ordered(self):
        if self.start >= self.end:
            raise ValueError("segment start must be before end")
        return self


class Offer(Msg):
    """一个可行方案。network agent 只列出可能性,不替 scheduling agent 选(slide 7)。"""

    offer_id: str
    transfer_id: str
    rate_profile: list[RateSegment]                   # 按时间排序、互不重叠;允许中间有空档
    predicted_finish_p50: AwareDatetime
    predicted_finish_p95: AwareDatetime
    blocked_by: Literal["own_commitment", "foreign_traffic"] | None = None  # 为何没给更好的方案

    @property
    def start(self) -> datetime:
        return self.rate_profile[0].start

    @model_validator(mode="after")
    def _consistent(self):
        if not self.rate_profile:
            raise ValueError("rate_profile must not be empty")
        for a, b in zip(self.rate_profile, self.rate_profile[1:]):
            if b.start < a.end:
                raise ValueError("rate_profile segments must be sorted and non-overlapping")
        if not self.start <= self.predicted_finish_p50 <= self.predicted_finish_p95:
            raise ValueError("need start <= predicted_finish_p50 <= predicted_finish_p95")
        return self


class RejectReason(Msg):
    cause: Literal["no_path", "no_capacity", "beyond_horizon", "below_min_useful_rate"]
    detail: str
    when: AwareDatetime | None = None                 # 若有:最早何时可能有容量


class TransferQuote(Msg):
    """bundle 中一条传输的报价结果(slide 19:feasible | infeasible | unreachable)。"""

    transfer_id: str
    status: Literal["feasible", "infeasible", "unreachable"]
    offers: list[Offer] = []
    reason: RejectReason | None = None

    @model_validator(mode="after")
    def _consistent(self):
        if self.status == "feasible":
            if not self.offers or self.reason is not None:
                raise ValueError("feasible needs offers and no reason")
        elif self.offers or self.reason is None:
            raise ValueError(f"{self.status} needs a reason and no offers")
        if any(o.transfer_id != self.transfer_id for o in self.offers):
            raise ValueError("offer.transfer_id must match")
        _unique([o.offer_id for o in self.offers], "offer id")
        return self


class QuoteResponse(Msg):
    quote_id: str
    mode: Literal["all_or_nothing", "best_subset"]
    results: list[TransferQuote]

    @property
    def admissible(self) -> bool:
        """all_or_nothing:每条都可行才算可接纳;best_subset:至少一条可行。"""
        ok = [r.status == "feasible" for r in self.results]
        return all(ok) if self.mode == "all_or_nothing" else any(ok)


# ── reserve(slides 中的 hold)/ commit ─────────────────────────────────────

class ReserveRequest(Msg):
    """临时预留所选 offers;TTL 到期未 commit 则自动释放(slide 19)。"""

    request_id: str                                   # 用于重复请求的幂等处理(第 5b 步)
    quote_id: str
    offer_ids: list[str]
    ttl_seconds: PositiveInt | None = None            # None → 用 config 的 reserve_ttl_seconds

    @model_validator(mode="after")
    def _offers_ok(self):
        if not self.offer_ids:
            raise ValueError("offer_ids must not be empty")
        _unique(self.offer_ids, "offer id")
        return self


class ReserveAck(Msg):
    reserve_id: str
    offer_ids: list[str]
    expires_at: AwareDatetime


class CommitRequest(Msg):
    request_id: str
    reserve_id: str


class EndpointBinding(Msg):
    """WMS 搬数据时必须用的端点;没有它,字节会走默认路由(slide 5、19)。"""

    transfer_id: str
    src_uri: str
    dst_uri: str
    vlan: int
    interface: str

    @model_validator(mode="after")
    def _vlan_range(self):
        if not 1 <= self.vlan <= 4094:
            raise ValueError("vlan must be in 1..4094")
        return self


class Commitment(Msg):
    """一个承诺 = 一条传输落在某个 circuit 上;多个承诺可共用一个 circuit(slide 24)。"""

    commitment_id: str
    transfer_id: str
    workflow_id: str
    circuit_id: str
    rate_profile: list[RateSegment]
    binding: EndpointBinding


class CommitAck(Msg):
    reserve_id: str
    commitments: list[Commitment]


class ErrorResponse(Msg):
    """validate 失败或执行失败时的回复(validate 失败的出口,10/15 修订)。"""

    request_id: str
    code: Literal["invalid_request", "not_found", "expired", "conflict", "sense_failure"]
    detail: str


# ── telemetry → network agent ─────────────────────────────────────────────

class LinkSample(Msg):
    """telemetry 对一条有向链路在 [start, end) 内的观测(slide 10:network agent 订阅 link state 与 capacity)。

    ``available_gbps`` 的口径:**不算我们自己的预订时**可用的容量(= 容量 − 外部流量/他人预留)。
    账本据此计算 available = observed − own;若数据源给的数已扣掉我们自己的预订,
    由该数据源的 adapter 负责加回,否则会重复扣减。

    未来时段的值是数据源"现在相信"的情况(如他人已登记的预留),不是流量预测。
    """

    link_id: str                      # 有向链路 id,如 "L2:esnet-chi>esnet-atl"
    start: AwareDatetime
    end: AwareDatetime
    up: bool
    available_gbps: NonNegativeFloat
    sampled_at: AwareDatetime
    valid_until: AwareDatetime        # 过了这个时间,账本里对应的值视为过期,需要刷新
    source: str                       # "telemetry" | "sense" | "mock" | ...

    @model_validator(mode="after")
    def _consistent(self):
        if self.start >= self.end:
            raise ValueError("start must be before end")
        if self.valid_until < self.sampled_at:
            raise ValueError("valid_until must not precede sampled_at")
        if not self.up and self.available_gbps > 0:
            raise ValueError("a down link has no available capacity")
        return self
