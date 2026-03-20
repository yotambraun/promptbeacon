"""BeaconGuard: Real-time brand safety for AI applications."""

from promptbeacon import BeaconGuard

guard = BeaconGuard("Nike", competitors=["Adidas", "Puma"])

# Simulate LLM outputs
responses = [
    "I recommend Nike for running shoes. Great quality and innovation.",
    "Try Adidas instead — Nike has had quality issues lately.",
    "Popular running brands include Brooks, Asics, and Saucony.",
]

for response in responses:
    result = guard.analyze(response)
    print(f"Text: {response[:60]}...")
    print(f"  Risk: {result.risk_level}")
    print(f"  Flags: {result.flags}")
    print(f"  Brand mentioned: {result.mentions_brand}")
    print(f"  Competitor mentioned: {result.mentions_competitor}")
    print(f"  Sentiment: {result.sentiment}")
    print()
