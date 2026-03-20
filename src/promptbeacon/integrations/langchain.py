"""LangChain integration for BeaconGuard.

Requires ``langchain-core`` to be installed. This module uses lazy imports
so that ``langchain-core`` is NOT a hard dependency of promptbeacon.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from promptbeacon.guard import BeaconGuard, GuardResult

if TYPE_CHECKING:
    pass


def _import_langchain_core():
    """Lazy import langchain_core, raising a clear error if missing."""
    try:
        import langchain_core  # noqa: F401
    except ImportError as e:
        raise ImportError(
            "langchain-core is required for LangChain integration. "
            "Install it with: pip install 'promptbeacon[langchain]'"
        ) from e


class BeaconGuardCallbackHandler:
    """LangChain callback handler that runs BeaconGuard on LLM outputs.

    Inherits from ``langchain_core.callbacks.BaseCallbackHandler`` at
    runtime via lazy import.

    Example::

        from promptbeacon import BeaconGuard
        from promptbeacon.integrations.langchain import BeaconGuardCallbackHandler

        guard = BeaconGuard("Acme", competitors=["CompetitorX"])
        handler = BeaconGuardCallbackHandler(guard)
        # Pass handler to your LangChain chain's callbacks
    """

    def __init__(
        self,
        guard: BeaconGuard,
        on_high_risk: Callable[[GuardResult], None] | None = None,
    ) -> None:
        _import_langchain_core()
        from langchain_core.callbacks import BaseCallbackHandler

        self.__class__.__bases__ = (BaseCallbackHandler,)
        self.guard = guard
        self.on_high_risk = on_high_risk
        self.last_result: GuardResult | None = None

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:  # noqa: ARG002
        """Called when an LLM call ends. Analyzes the response text."""
        # Extract text from LLMResult
        text = ""
        if hasattr(response, "generations") and response.generations:
            for gen_list in response.generations:
                for gen in gen_list:
                    if hasattr(gen, "text"):
                        text += gen.text

        if text:
            self.last_result = self.guard.analyze(text)
            if self.last_result.risk_level == "high" and self.on_high_risk is not None:
                self.on_high_risk(self.last_result)


class BeaconGuardOutputParser:
    """LangChain output parser that returns GuardResult.

    Inherits from ``langchain_core.output_parsers.BaseOutputParser`` at
    runtime via lazy import.

    Example::

        from promptbeacon import BeaconGuard
        from promptbeacon.integrations.langchain import BeaconGuardOutputParser

        guard = BeaconGuard("Acme", competitors=["CompetitorX"])
        parser = BeaconGuardOutputParser(guard=guard)
        # Use in a chain: chain | parser
    """

    def __init__(self, guard: BeaconGuard) -> None:
        _import_langchain_core()
        from langchain_core.output_parsers import BaseOutputParser

        self.__class__.__bases__ = (BaseOutputParser,)
        self.guard = guard

    @property
    def _type(self) -> str:
        return "beacon_guard"

    def parse(self, text: str) -> GuardResult:
        """Parse LLM output text into a GuardResult.

        Args:
            text: The LLM output text.

        Returns:
            GuardResult from BeaconGuard analysis.
        """
        return self.guard.analyze(text)
