"""Translate health evidence into a decision; adapters execute nothing here."""

from dataclasses import dataclass

from .plugin_health import HealthAssessment, HealthState


@dataclass(frozen=True)
class IsolationDecision:
    state: HealthState
    reason: str
    suppress_upstream: bool


class IsolationPolicy:
    def decide(self, assessment: HealthAssessment) -> IsolationDecision:
        return IsolationDecision(
            assessment.state,
            assessment.reason,
            assessment.state in {HealthState.PAUSED, HealthState.QUARANTINED},
        )
