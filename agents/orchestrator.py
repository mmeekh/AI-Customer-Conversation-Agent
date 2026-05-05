"""
Main agent orchestrator.
Coordinates: intent classification -> memory recall -> RAG -> response generation -> escalation.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from agents.intent_classifier import IntentClassifier, IntentResult
from agents.sentiment_analyzer import SentimentAnalyzer, SentimentResult
from memory.vector_store import VectorMemory
from memory.short_term import ShortTermMemory
from tools.knowledge_retriever import KnowledgeRetriever
from tools.escalation import EscalationService
from analytics.metrics import MetricsCollector

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    text: str
    intent: IntentResult
    sentiment: SentimentResult
    escalated: bool
    sources: list


class EmailAgentOrchestrator:
    """Top-level coordinator gluing classification, memory, and generation together."""

    def __init__(self, llm_client, model_id: str, persona: str):
        self.client = llm_client
        self.model = model_id
        self.persona = persona

        self.intent = IntentClassifier(llm_client, model_id)
        self.sentiment = SentimentAnalyzer(llm_client, model_id)
        self.short_mem = ShortTermMemory()
        self.long_mem = VectorMemory()
        self.knowledge = KnowledgeRetriever()
        self.escalation = EscalationService()
        self.metrics = MetricsCollector()

    def handle(self, thread_id: str, sender: str, message: str, channel: str = "gmail") -> AgentResponse:
        intent = self.intent.classify(message, sender)
        sentiment = self.sentiment.analyze(message)
        logger.info(f"thread={thread_id} intent={intent.intent}({intent.confidence:.2f}) urgency={sentiment.urgency}")

        if sentiment.requires_human or intent.intent == "vip_escalation":
            self.escalation.notify(thread_id, sender, message, intent, sentiment, channel)
            self.metrics.record(thread_id, channel, intent.intent, sentiment.polarity, escalated=True)
            return AgentResponse(
                text=self._holding_reply(),
                intent=intent, sentiment=sentiment, escalated=True, sources=[],
            )

        history = self.short_mem.get_window(thread_id)
        long_term_hits = self.long_mem.recall(message, k=3, thread_id=thread_id)
        kb_hits = self.knowledge.search(message, k=3, intent=intent.intent)

        reply = self._generate(message, history, long_term_hits, kb_hits, intent, sentiment)

        self.short_mem.append(thread_id, "user", message, channel, intent.intent, sentiment.polarity)
        self.short_mem.append(thread_id, "model", reply, channel, intent.intent, sentiment.polarity)
        self.long_mem.remember(thread_id, "user", message, {"channel": channel, "intent": intent.intent})
        self.long_mem.remember(thread_id, "model", reply, {"channel": channel, "intent": intent.intent})
        self.metrics.record(thread_id, channel, intent.intent, sentiment.polarity, escalated=False)

        return AgentResponse(
            text=reply, intent=intent, sentiment=sentiment,
            escalated=False, sources=[h.get("source") for h in kb_hits],
        )

    def _generate(self, message, history, mem_hits, kb_hits, intent, sentiment):
        context_block = self._build_context(mem_hits, kb_hits)
        chat = self.client.chats.create(
            model=self.model,
            config={"system_instruction": self._system_prompt(intent, sentiment, context_block)},
            history=history,
        )
        return chat.send_message(message).text.strip()

    def _system_prompt(self, intent, sentiment, context):
        return f"""{self.persona}

DETECTED INTENT: {intent.intent} (confidence: {intent.confidence:.2f})
CUSTOMER SENTIMENT: {sentiment.polarity:+.2f} | URGENCY: {sentiment.urgency}

RELEVANT CONTEXT FROM MEMORY AND KNOWLEDGE BASE:
{context}

RULES:
- Respond in the customer's language.
- Maximum 120-150 words, 3-4 short paragraphs.
- Do NOT add a signature; one is appended automatically.
- If sentiment is negative, lead with empathy.
- Cite knowledge base sources only if directly used.
"""

    @staticmethod
    def _build_context(mem_hits, kb_hits):
        lines = []
        for h in mem_hits[:3]:
            lines.append(f"[memory] {h['content'][:200]}")
        for h in kb_hits[:3]:
            lines.append(f"[kb:{h.get('source','?')}] {h.get('content','')[:200]}")
        return "\n".join(lines) or "(no prior context)"

    @staticmethod
    def _holding_reply() -> str:
        return (
            "Thank you for reaching out. Your message has been escalated to a "
            "specialist on our team and you will receive a personal response within "
            "the next business hours."
        )
