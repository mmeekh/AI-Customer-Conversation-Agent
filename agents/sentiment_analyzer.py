"""
Sentiment + urgency detection.
Outputs a polarity score and an urgency flag for escalation routing.
"""
from dataclasses import dataclass


@dataclass
class SentimentResult:
    polarity: float          # -1.0 (angry) -> +1.0 (happy)
    urgency: str             # 'low' | 'medium' | 'high' | 'critical'
    requires_human: bool
    reason: str


URGENCY_KEYWORDS = {
    "critical": ["lawsuit", "lawyer", "legal", "press", "tweet", "twitter", "ceo", "refund now"],
    "high": ["urgent", "asap", "immediately", "broken", "down", "outage", "frustrated", "angry"],
    "medium": ["soon", "today", "issue", "problem", "not working"],
}


class SentimentAnalyzer:
    """Hybrid LLM + keyword-based sentiment scoring."""

    def __init__(self, llm_client, model_id: str = "gemini-2.5-flash-lite"):
        self.client = llm_client
        self.model = model_id

    def analyze(self, message: str) -> SentimentResult:
        urgency = self._detect_urgency(message)
        polarity = self._score_polarity(message)
        return SentimentResult(
            polarity=polarity,
            urgency=urgency,
            requires_human=(polarity < -0.4 or urgency in {"high", "critical"}),
            reason=self._explain(polarity, urgency),
        )

    @staticmethod
    def _detect_urgency(text: str) -> str:
        lower = text.lower()
        for level in ("critical", "high", "medium"):
            if any(k in lower for k in URGENCY_KEYWORDS[level]):
                return level
        return "low"

    def _score_polarity(self, text: str) -> float:
        prompt = (
            "Rate the emotional polarity of this message from -1.0 (very angry/frustrated) "
            "to +1.0 (very happy/satisfied). Respond with ONLY the number.\n\n"
            f"MESSAGE: {text[:1000]}"
        )
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            return max(-1.0, min(1.0, float(response.text.strip())))
        except (ValueError, AttributeError):
            return 0.0

    @staticmethod
    def _explain(polarity: float, urgency: str) -> str:
        if polarity < -0.4 and urgency in {"high", "critical"}:
            return "Negative sentiment with high urgency: route to human immediately"
        if polarity < -0.4:
            return "Customer sounds frustrated: handle with care"
        if urgency == "critical":
            return "Critical urgency keywords detected: escalate"
        return "Standard handling"
