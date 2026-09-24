from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/sqlite/aether.db"
    API_PORT: int = 8456
    API_HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"

    # Model inference backend (Ollama, local-first)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Provider routing: "ollama" (local, no key) or a remote provider id from
    # aether.model.providers (openai, openrouter, groq, deepseek, xai, gemini,
    # anthropic). Remote keys live in their own env vars (OPENAI_API_KEY, …).
    MODEL_PROVIDER: str = "ollama"
    MODEL_NAME: str = ""  # empty -> provider default_model / OLLAMA_MODEL
    # Generic key override for remote providers (per-provider env vars win).
    PROVIDER_API_KEY: str = ""

    # Telegram bot bridge (optional; wired via the /setup page)
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_AGENT_ID: str = "aria"
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_CHAT_ID: str = ""
    # Allowlist: comma-separated Telegram user IDs that may talk to the bot.
    # Empty = everyone (or TELEGRAM_ALLOW_ALL_USERS=true for dev).
    TELEGRAM_ALLOWED_USERS: str = ""
    TELEGRAM_ALLOW_ALL_USERS: bool = False

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
