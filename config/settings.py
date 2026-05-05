"""
Centralised settings using pydantic-settings.
All env vars are loaded from .env at startup.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    GEMINI_API_KEY: str = ""
    MODEL_ID: str = "gemini-2.5-flash-lite"

    # Channels
    GMAIL_CREDENTIALS_FILE: str = "credentials.json"
    GMAIL_TOKEN_FILE: str = "token.json"
    INTERCOM_ACCESS_TOKEN: str = ""
    INTERCOM_ADMIN_ID: str = ""

    # Behaviour
    POLL_INTERVAL_SECONDS: int = 30
    MAX_MESSAGES_PER_POLL: int = 3
    MAX_RESPONSE_WORDS: int = 150
    TARGET_DOMAIN: str = ""

    # Memory
    SHORT_TERM_WINDOW: int = 10
    VECTOR_DB_PATH: str = "./data/chroma"

    # Escalation
    SLACK_ESCALATION_WEBHOOK: str = ""

    # Persona
    AGENT_NAME: str = "Emin"
    AGENT_COMPANY: str = "Clemta"
    AGENT_PERSONA: str = (
        "You are Emin, a customer success agent at Clemta. Reply professionally "
        "in the customer's language. Keep responses concise and actionable."
    )


settings = Settings()
