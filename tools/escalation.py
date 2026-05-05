"""
Escalation service: notifies humans via Slack when the agent decides to hand off.
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)


class EscalationService:
    """Sends Slack notifications for escalated conversations."""

    def __init__(self, slack_webhook: str = None):
        self.webhook = slack_webhook or os.getenv("SLACK_ESCALATION_WEBHOOK")

    def notify(self, thread_id, sender, message, intent, sentiment, channel="gmail"):
        if not self.webhook:
            logger.warning(f"No Slack webhook configured. Escalation logged only: {thread_id}")
            return False

        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "Conversation Escalation"}},
            {"type": "section", "fields": [
                {"type": "mrkdwn", "text": f"*Channel:*\n{channel}"},
                {"type": "mrkdwn", "text": f"*Thread:*\n{thread_id}"},
                {"type": "mrkdwn", "text": f"*From:*\n{sender}"},
                {"type": "mrkdwn", "text": f"*Intent:*\n{intent.intent} ({intent.confidence:.0%})"},
                {"type": "mrkdwn", "text": f"*Sentiment:*\n{sentiment.polarity:+.2f}"},
                {"type": "mrkdwn", "text": f"*Urgency:*\n{sentiment.urgency.upper()}"},
            ]},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Message:*\n{message[:500]}"}},
            {"type": "context", "elements": [
                {"type": "mrkdwn", "text": f"Reason: {sentiment.reason}"}
            ]},
        ]

        try:
            r = requests.post(self.webhook, json={"blocks": blocks}, timeout=5)
            return r.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Slack notification failed: {e}")
            return False
