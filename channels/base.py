"""
Abstract base channel: every transport (Gmail, Intercom, Zendesk, Slack) implements this.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class IncomingMessage:
    msg_id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    channel: str
    metadata: dict


class ChannelAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def fetch_unread(self, limit: int = 5) -> List[IncomingMessage]: ...

    @abstractmethod
    def reply(self, message: IncomingMessage, body: str, html: Optional[str] = None) -> bool: ...

    @abstractmethod
    def mark_read(self, msg_id: str) -> None: ...
