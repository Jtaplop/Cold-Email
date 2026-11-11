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

    # Google OAuth2 & APIs
    GMAIL_CREDENTIALS_FILE: Path = Path("credentials/client_secret.json")
    GMAIL_TOKEN_FILE: Path = Path("credentials/token.json")
    
    # Scopes unificados para Gmail y Google Drive
    GOOGLE_SCOPES: list[str] = [
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/drive",
    ]

    # Google Drive Folders
    GOOGLE_DRIVE_FOLDER_ID: str = ""
    GOOGLE_DRIVE_PROCESSED_FOLDER_ID: str = ""

    # Local Storage Fallback
    INBOX_CSV_DIR: Path = Path("data/inbox_csv")
    PROCESSED_CSV_DIR: Path = Path("data/processed_csv")


settings = Settings()