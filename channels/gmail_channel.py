"""
Gmail channel adapter using Gmail API + OAuth2.
"""
import os
import base64
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.header import Header
from typing import List, Optional

from email_reply_parser import EmailReplyParser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from channels.base import ChannelAdapter, IncomingMessage


SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
IGNORE_SENDERS = {
    "binance", "google", "linkedin", "no-reply", "noreply",
    "newsletter", "trendyol", "github", "coursera", "indeed",
}


class GmailChannel(ChannelAdapter):
    name = "gmail"

    def __init__(
        self,
        credentials_file: str = "credentials.json",
        token_file: str = "token.json",
        signature_path: Optional[str] = "signature.png",
    ):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.signature_path = signature_path
        self.service = self._build_service()

    def _build_service(self):
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w") as f:
                f.write(creds.to_json())
        return build("gmail", "v1", credentials=creds)

    def fetch_unread(self, limit: int = 5) -> List[IncomingMessage]:
        results = self.service.users().messages().list(
            userId="me", q="is:unread newer_than:30m", maxResults=limit,
        ).execute()
        messages = []
        for ref in results.get("messages", []):
            full = self.service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
            parsed = self._parse(full)
            if parsed and not self._is_ignored(parsed.sender):
                messages.append(parsed)
        return messages

    def _parse(self, msg) -> Optional[IncomingMessage]:
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        _, sender = email.utils.parseaddr(headers.get("From", ""))
        body = self._extract_body(msg["payload"]) or msg.get("snippet", "")
        return IncomingMessage(
            msg_id=msg["id"],
            thread_id=msg["threadId"],
            sender=sender,
            subject=headers.get("Subject", ""),
            body=body,
            channel="gmail",
            metadata={"original_message_id": headers.get("Message-ID", "")},
        )

    @staticmethod
    def _extract_body(payload) -> str:
        content = ""
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                    content = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
        elif "data" in payload.get("body", {}):
            content = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        if not content:
            return ""
        return EmailReplyParser.read(content).reply.strip()

    @staticmethod
    def _is_ignored(sender: str) -> bool:
        s = sender.lower()
        return any(k in s for k in IGNORE_SENDERS)

    def reply(self, message: IncomingMessage, body: str, html: Optional[str] = None) -> bool:
        subject = message.subject if message.subject.lower().startswith("re:") else f"Re: {message.subject}"
        if self.signature_path and os.path.exists(self.signature_path):
            mime = self._build_html_with_signature(body)
        else:
            mime = MIMEText(body, "plain", "utf-8")
        mime["To"] = message.sender
        mime["Subject"] = Header(subject, "utf-8").encode()
        mime["In-Reply-To"] = message.metadata.get("original_message_id", "")
        mime["References"] = message.metadata.get("original_message_id", "")
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        self.service.users().messages().send(
            userId="me", body={"raw": raw, "threadId": message.thread_id}
        ).execute()
        return True

    def _build_html_with_signature(self, body: str) -> MIMEMultipart:
        html_body = body.replace("\n", "<br>")
        html = f"""<html><body>
<p style="font-family:Arial,sans-serif;font-size:14px;color:#333;">{html_body}</p>
<div style="margin-top:5px;"><img src="cid:signature_image" alt="signature" style="width:200px;"></div>
</body></html>"""
        outer = MIMEMultipart("related")
        alt = MIMEMultipart("alternative")
        outer.attach(alt)
        alt.attach(MIMEText(html, "html", "utf-8"))
        with open(self.signature_path, "rb") as f:
            img = MIMEImage(f.read(), name="signature.png")
            img.add_header("Content-ID", "<signature_image>")
            img.add_header("Content-Disposition", "inline", filename="signature.png")
            outer.attach(img)
        return outer

    def mark_read(self, msg_id: str) -> None:
        self.service.users().messages().batchModify(
            userId="me", body={"ids": [msg_id], "removeLabelIds": ["UNREAD"]}
        ).execute()
