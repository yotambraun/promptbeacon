"""Using BeaconGuard with LangChain."""

from promptbeacon import BeaconGuard
from promptbeacon.integrations.middleware import BeaconGuardMiddleware

guard = BeaconGuard("Acme", competitors=["CompetitorX"])
middleware = BeaconGuardMiddleware(
    guard,
    on_high_risk=lambda r: print(f"Brand safety alert: {r.flags}"),
)

# In your LLM pipeline:
llm_output = "I'd suggest CompetitorX over Acme for this use case."
result = middleware(llm_output)
print(f"Risk: {result.risk_level}")
print(f"Flags: {result.flags}")
