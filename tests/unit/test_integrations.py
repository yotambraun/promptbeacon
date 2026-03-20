"""Tests for BeaconGuard integrations."""

import pytest

from promptbeacon.guard import BeaconGuard, GuardResult
from promptbeacon.integrations.middleware import BeaconGuardMiddleware


@pytest.fixture
def guard():
    return BeaconGuard("Acme", competitors=["CompetitorX"])


class TestBeaconGuardMiddleware:
    def test_callable_returns_guard_result(self, guard):
        mw = BeaconGuardMiddleware(guard)
        result = mw("Acme is a great company.")
        assert isinstance(result, GuardResult)

    def test_on_high_risk_callback_fires(self, guard):
        fired = []
        mw = BeaconGuardMiddleware(
            guard,
            on_high_risk=lambda r: fired.append(r),
        )
        # Trigger high risk: competitor + negative sentiment
        mw("CompetitorX is better. Acme has problems and issues. Avoid Acme.")
        assert len(fired) == 1
        assert fired[0].risk_level == "high"

    def test_on_high_risk_not_fired_for_low_risk(self, guard):
        fired = []
        mw = BeaconGuardMiddleware(
            guard,
            on_high_risk=lambda r: fired.append(r),
        )
        mw("Acme is a great company with excellent products.")
        assert len(fired) == 0

    def test_middleware_without_callback(self, guard):
        mw = BeaconGuardMiddleware(guard)
        result = mw("CompetitorX is better than Acme. Avoid Acme.")
        assert result.risk_level in ("medium", "high")


class TestLangChainIntegration:
    def test_langchain_import_error(self):
        """LangChain classes raise ImportError when langchain-core is missing."""
        # This test only runs if langchain-core is NOT installed
        try:
            import langchain_core  # noqa: F401

            pytest.skip("langchain-core is installed")
        except ImportError:
            pass

        from promptbeacon.integrations.langchain import BeaconGuardCallbackHandler

        guard = BeaconGuard("Test")
        with pytest.raises(ImportError, match="langchain-core"):
            BeaconGuardCallbackHandler(guard)

    def test_langchain_output_parser_import_error(self):
        """Output parser raises ImportError when langchain-core is missing."""
        try:
            import langchain_core  # noqa: F401

            pytest.skip("langchain-core is installed")
        except ImportError:
            pass

        from promptbeacon.integrations.langchain import BeaconGuardOutputParser

        guard = BeaconGuard("Test")
        with pytest.raises(ImportError, match="langchain-core"):
            BeaconGuardOutputParser(guard=guard)
