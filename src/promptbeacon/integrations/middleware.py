"""Generic middleware for BeaconGuard integration."""

from __future__ import annotations

from collections.abc import Callable

from promptbeacon.guard import BeaconGuard, GuardResult


class BeaconGuardMiddleware:
    """Callable middleware that runs BeaconGuard analysis on text.

    Can be inserted into any LLM pipeline. Optionally fires a callback
    when a high-risk result is detected.

    Example::

        guard = BeaconGuard("Acme", competitors=["CompetitorX"])
        mw = BeaconGuardMiddleware(guard, on_high_risk=lambda r: alert(r))
        result = mw("Try CompetitorX instead of Acme.")
    """

    def __init__(
        self,
        guard: BeaconGuard,
        on_high_risk: Callable[[GuardResult], None] | None = None,
    ) -> None:
        self.guard = guard
        self.on_high_risk = on_high_risk

    def __call__(self, text: str) -> GuardResult:
        """Analyze text and fire callback if high risk.

        Args:
            text: The LLM output text to analyze.

        Returns:
            GuardResult from the analysis.
        """
        result = self.guard.analyze(text)
        if result.risk_level == "high" and self.on_high_risk is not None:
            self.on_high_risk(result)
        return result
