"""
Intent classification: routes incoming messages to the right pipeline.
Uses LLM-based zero-shot classification with confidence scoring.
"""
from typing import Dict
from dataclasses import dataclass


INTENTS = {
    "sales": "Pricing, demos, plans, signing up, product comparisons",
    "support": "Bug reports, technical issues, how-to questions",
    "billing": "Invoices, refunds, subscription changes, payment failures",
    "feedback": "Feature requests, suggestions, general feedback",
    "spam": "Promotional content, newsletters, irrelevant messages",
    "vip_escalation": "Enterprise inquiries, partnerships, press, legal",
}


@dataclass
class IntentResult:
    intent: str
    confidence: float
    reasoning: str


class IntentClassifier:
    """Zero-shot intent routing using the configured LLM client."""

    def __init__(self, llm_client, model_id: str = "gemini-2.5-flash-lite"):
        self.client = llm_client
        self.model = model_id

    def classify(self, message: str, sender: str = "") -> IntentResult:
        labels = "\n".join(f"- {k}: {v}" for k, v in INTENTS.items())
        prompt = f"""Classify this email into ONE of the following intents.
Return ONLY valid JSON: {{"intent": "...", "confidence": 0.0-1.0, "reasoning": "..."}}

INTENTS:
{labels}

SENDER: {sender}
EMAIL: {message[:1500]}"""

        response = self.client.models.generate_content(model=self.model, contents=prompt)
        return self._parse(response.text)

    @staticmethod
    def _parse(text: str) -> IntentResult:
        import json
        import re
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if not match:
            return IntentResult("support", 0.3, "Failed to parse classifier output")
        try:
            data = json.loads(match.group())
            return IntentResult(
                intent=data.get("intent", "support"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, ValueError):
            return IntentResult("support", 0.3, "Failed to parse classifier output")
