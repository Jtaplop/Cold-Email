from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Supabase Credentials
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # Google Gemini API
    GEMINI_API_KEY: str = ""

    # Gmail API Credentials Paths
    GMAIL_CREDENTIALS_FILE: Path = Path("credentials/client_secret.json")
    GMAIL_TOKEN_FILE: Path = Path("credentials/token.json")

    # Storage Paths
    INBOX_CSV_DIR: Path = Path("data/inbox_csv")
    PROCESSED_CSV_DIR: Path = Path("data/processed_csv")


# Instancia única (Singleton a nivel de módulo)
settings = Settings()