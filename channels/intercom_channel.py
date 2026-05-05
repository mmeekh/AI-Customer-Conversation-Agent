"""
Intercom channel adapter.
Uses the Intercom REST API to fetch conversations and reply as an admin.
"""
import os
import requests
from typing import List, Optional

from channels.base import ChannelAdapter, IncomingMessage


INTERCOM_API_BASE = "https://api.intercom.io"


class IntercomChannel(ChannelAdapter):
    name = "intercom"

    def __init__(self, access_token: Optional[str] = None, admin_id: Optional[str] = None):
        self.token = access_token or os.getenv("INTERCOM_ACCESS_TOKEN")
        self.admin_id = admin_id or os.getenv("INTERCOM_ADMIN_ID")
        if not self.token:
            raise ValueError("INTERCOM_ACCESS_TOKEN is required")

    @property
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Intercom-Version": "2.11",
        }

    def fetch_unread(self, limit: int = 5) -> List[IncomingMessage]:
        payload = {
            "query": {
                "operator": "AND",
                "value": [
                    {"field": "open", "operator": "=", "value": True},
                    {"field": "read", "operator": "=", "value": False},
                ],
            },
            "pagination": {"per_page": limit},
        }
        r = requests.post(f"{INTERCOM_API_BASE}/conversations/search", headers=self._headers, json=payload)
        r.raise_for_status()
        out = []
        for conv in r.json().get("conversations", []):
            source = conv.get("source", {})
            author = source.get("author", {})
            out.append(IncomingMessage(
                msg_id=conv["id"],
                thread_id=conv["id"],
                sender=author.get("email", author.get("id", "unknown")),
                subject=source.get("subject", ""),
                body=source.get("body", ""),
                channel="intercom",
                metadata={"contact_id": author.get("id"), "type": source.get("type")},
            ))
        return out

    def reply(self, message: IncomingMessage, body: str, html: Optional[str] = None) -> bool:
        payload = {
            "message_type": "comment",
            "type": "admin",
            "admin_id": self.admin_id,
            "body": html or body,
        }
        r = requests.post(
            f"{INTERCOM_API_BASE}/conversations/{message.thread_id}/reply",
            headers=self._headers, json=payload,
        )
        return r.status_code == 200

    def mark_read(self, msg_id: str) -> None:
        requests.put(
            f"{INTERCOM_API_BASE}/conversations/{msg_id}/read",
            headers=self._headers, json={"read": True},
        )

    def assign_to_human(self, conversation_id: str, assignee_id: str, note: str = "") -> bool:
        payload = {
            "message_type": "assignment",
            "type": "admin",
            "admin_id": self.admin_id,
            "assignee_id": assignee_id,
            "body": note,
        }
        r = requests.post(
            f"{INTERCOM_API_BASE}/conversations/{conversation_id}/parts",
            headers=self._headers, json=payload,
        )
        return r.status_code == 200
