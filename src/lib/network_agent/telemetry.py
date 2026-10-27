"""Telemetry interface: where the network agent pulls link capacity and state from (slide 10).

The network agent depends only on the ``TelemetrySource`` interface; whether a mock, the Telemetry
Agent or SENSE / Prometheus sits behind it is transparent to the agent.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from .schemas import LinkSample
from .sim import MockNetwork


class TelemetrySource(Protocol):
    def link_samples(self, link_ids: list[str], start: datetime, end: datetime,
                     now: datetime) -> list[LinkSample]:
        """Return samples for these directed links over [start, end); see ``schemas.LinkSample`` for the semantics."""
        ...


@dataclass
class MockTelemetry:
    """Read the "ground truth" from MockNetwork and return samples split at every state change."""

    network: MockNetwork
    validity_seconds: int   # sample lifetime, i.e. valid_until = now + validity_seconds

    def link_samples(self, link_ids: list[str], start: datetime, end: datetime,
                     now: datetime) -> list[LinkSample]:
        valid_until = now + timedelta(seconds=self.validity_seconds)
        return [
            LinkSample(link_id=link, start=a, end=b, up=up, available_gbps=gbps,
                       sampled_at=now, valid_until=valid_until, source="mock")
            for link in link_ids
            for a, b, up, gbps in self.network.segments(link, start, end)
        ]
