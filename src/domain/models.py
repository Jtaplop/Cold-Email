from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from src.domain.enums import EmailStatus


class ProspectBase(BaseModel):
    email: EmailStr
    ig_username: str | None = None
    full_name: str | None = None
    language: str = "es"
    niche: str | None = None
    comment: str | None = None

    @field_validator("ig_username", mode="before")
    @classmethod
    def clean_ig_username(cls, value: str | None) -> str | None:
        if not value or not str(value).strip():
            return None
        return str(value).strip().lstrip("@")

    @field_validator("language", mode="before")
    @classmethod
    def normalize_language(cls, value: str | None) -> str:
        if not value or not str(value).strip():
            return "es"
        return str(value).strip().lower()


class ProspectCreate(ProspectBase):
    """Modelo utilizado durante la ingesta del CSV antes de insertarse en la BD."""
    pass


class ProspectDB(ProspectBase):
    """Modelo que representa una fila real recuperada de Supabase."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class EmailCreate(BaseModel):
    """Modelo para encolar un correo nuevo asociado a un prospecto."""
    prospect_id: UUID
    subject: str | None = None
    body_html: str | None = None
    status: EmailStatus = EmailStatus.PENDING


class EmailDB(BaseModel):
    """Modelo que representa el registro completo del correo en Supabase."""
    id: UUID
    prospect_id: UUID
    subject: str | None = None
    body_html: str | None = None
    status: EmailStatus
    error_message: str | None = None
    created_at: datetime
    processed_at: datetime | None = None