"""
Entry point: polls all configured channels and routes messages through the agent orchestrator.
"""
import time
import logging
import warnings
from datetime import datetime
from google import genai

from config.settings import settings
from agents.orchestrator import EmailAgentOrchestrator
from channels.gmail_channel import GmailChannel

warnings.filterwarnings("ignore")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s :: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def build_channels():
    """Initialize every channel that has credentials configured."""
    channels = []
    try:
        channels.append(GmailChannel(
            credentials_file=settings.GMAIL_CREDENTIALS_FILE,
            token_file=settings.GMAIL_TOKEN_FILE,
        ))
        logger.info("Gmail channel ready")
    except Exception as e:
        logger.warning(f"Gmail channel unavailable: {e}")

    if settings.INTERCOM_ACCESS_TOKEN:
        try:
            from channels.intercom_channel import IntercomChannel
            channels.append(IntercomChannel(
                access_token=settings.INTERCOM_ACCESS_TOKEN,
                admin_id=settings.INTERCOM_ADMIN_ID,
            ))
            logger.info("Intercom channel ready")
        except Exception as e:
            logger.warning(f"Intercom channel unavailable: {e}")

    return channels


def run_loop():
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    orchestrator = EmailAgentOrchestrator(
        llm_client=client,
        model_id=settings.MODEL_ID,
        persona=settings.AGENT_PERSONA,
    )
    channels = build_channels()
    if not channels:
        logger.error("No channels configured. Exiting.")
        return

    logger.info(f"Agent online with {len(channels)} channel(s). Polling every {settings.POLL_INTERVAL_SECONDS}s.")

    while True:
        for channel in channels:
            try:
                messages = channel.fetch_unread(limit=settings.MAX_MESSAGES_PER_POLL)
                for msg in messages:
                    if orchestrator.short_mem.is_processed(msg.msg_id):
                        continue
                    started = time.monotonic()
                    response = orchestrator.handle(
                        thread_id=msg.thread_id, sender=msg.sender,
                        message=msg.body, channel=channel.name,
                    )
                    channel.reply(msg, response.text)
                    channel.mark_read(msg.msg_id)
                    orchestrator.short_mem.mark_processed(msg.msg_id, channel.name)
                    elapsed_ms = int((time.monotonic() - started) * 1000)
                    logger.info(
                        f"[{channel.name}] {msg.sender} -> intent={response.intent.intent} "
                        f"sentiment={response.sentiment.polarity:+.2f} escalated={response.escalated} "
                        f"({elapsed_ms}ms)"
                    )
            except Exception as e:
                logger.error(f"[{channel.name}] poll failed: {e}")

        time.sleep(settings.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logger.info(f"Starting agent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    run_loop()
