"""Finish-time estimation: given a reserved rate, roughly how fast the transfer actually completes
(slide 19: predicted_finish p50 / p95 at achievable rate).

``RateModel`` is the hook for the step-9 Learning calibration. The first version only has
``IdealRateModel``: it assumes actual rate = reserved rate, so p50 = p95 = the placement's end time.

Known limitation: once a calibrated model is used, an actual rate below the reserved rate makes p95
later than the end of the reserved window, so the transfer would overrun its reservation; placement
will then need to size reservations by the p95 rate.
"""

from datetime import datetime
from typing import Protocol

from .placement import Placement


class RateModel(Protocol):
    def predict_finish(self, p: Placement, nbytes: int) -> tuple[datetime, datetime]:
        """Return the (p50, p95) finish times."""
        ...


class IdealRateModel:
    def predict_finish(self, p: Placement, nbytes: int) -> tuple[datetime, datetime]:
        return p.end, p.end
