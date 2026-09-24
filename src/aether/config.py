from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/sqlite/aether.db"
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"

    # Model inference backend (Ollama, local-first)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"

    # Telegram bot bridge (optional; wired via the /setup page)
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_AGENT_ID: str = "aria"
    TELEGRAM_ENABLED: bool = False

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
