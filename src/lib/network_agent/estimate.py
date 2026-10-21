"""完成时间估计:预留了某个速率,实际大概多快传完(slide 19:predicted_finish p50 / p95 at achievable rate)。

``RateModel`` 是第 9 步 Learning 校准结果的接入点。第一版只有 ``IdealRateModel``:
假设实际速率 = 预留速率,所以 p50 = p95 = 方案的结束时间。

已知局限:换成校准模型后,若实际速率低于预留速率,p95 会晚于预留时段的结束,
传输会超出预留时段;届时 placement 需要按 p95 速率来定预留时长。
"""

from datetime import datetime
from typing import Protocol

from .placement import Placement


class RateModel(Protocol):
    def predict_finish(self, p: Placement, nbytes: int) -> tuple[datetime, datetime]:
        """返回 (p50, p95) 完成时间。"""
        ...


class IdealRateModel:
    def predict_finish(self, p: Placement, nbytes: int) -> tuple[datetime, datetime]:
        return p.end, p.end
