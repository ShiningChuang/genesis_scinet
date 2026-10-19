"""Telemetry 接口:network agent 从这里拉取链路的容量与状态(slide 10)。

network agent 只依赖 ``TelemetrySource`` 这个接口;背后是 mock、Telemetry Agent
(另一位同学负责)还是 SENSE / Prometheus,对它是透明的。
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from .schemas import LinkSample
from .sim import MockNetwork


class TelemetrySource(Protocol):
    def link_samples(self, link_ids: list[str], start: datetime, end: datetime,
                     now: datetime) -> list[LinkSample]:
        """返回这些有向链路在 [start, end) 内的样本;口径见 ``schemas.LinkSample``。"""
        ...


@dataclass
class MockTelemetry:
    """从 MockNetwork 读"真实情况",按状态变化切段返回样本。"""

    network: MockNetwork
    validity_seconds: int   # 样本有效期,即 valid_until = now + validity_seconds

    def link_samples(self, link_ids: list[str], start: datetime, end: datetime,
                     now: datetime) -> list[LinkSample]:
        valid_until = now + timedelta(seconds=self.validity_seconds)
        return [
            LinkSample(link_id=link, start=a, end=b, up=up, available_gbps=gbps,
                       sampled_at=now, valid_until=valid_until, source="mock")
            for link in link_ids
            for a, b, up, gbps in self.network.segments(link, start, end)
        ]
