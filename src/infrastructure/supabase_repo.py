from uuid import UUID
from supabase import Client, create_client
from src.config.settings import settings
from src.domain.enums import EmailStatus
from src.domain.models import ProspectCreate


class SupabaseRepository:
    def __init__(self) -> None:
        self.client: Client = create_client(
            supabase_url=settings.SUPABASE_URL,
            supabase_key=settings.SUPABASE_KEY,
        )

    def upsert_prospect(self, prospect: ProspectCreate) -> UUID:
        """
        Inserta el prospecto o actualiza sus datos si el email ya existe.
        Retorna el UUID único del prospecto.
        """
        data = {
            "email": prospect.email,
            "ig_username": prospect.ig_username,
            "full_name": prospect.full_name,
            "language": prospect.language,
            "niche": prospect.niche,
            "comment": prospect.comment,
        }

        # Realiza el upsert referenciando la columna unique 'email'
        response = (
            self.client.table("prospects")
            .upsert(data, on_conflict="email")
            .execute()
        )

        if not response.data:
            raise RuntimeError(f"Error persistiendo el prospecto: {prospect.email}")

        return UUID(response.data[0]["id"])

    def create_pending_email(self, prospect_id: UUID) -> UUID:
        """Crea un registro de correo en estado PENDING vinculado al prospecto."""
        data = {
            "prospect_id": str(prospect_id),
            "status": EmailStatus.PENDING.value,
        }
        response = self.client.table("emails").insert(data).execute()
        if not response.data:
            raise RuntimeError(f"Error creando el email PENDING para el prospecto {prospect_id}")

        return UUID(response.data[0]["id"])

    def fetch_pending_emails_with_prospect(self, limit: int = 50) -> list[dict]:
        """
        Recupera correos pendientes junto con la información del prospecto (JOIN relacional).
        Devuelve el contexto completo necesario para que la IA genere el correo.
        """
        response = (
            self.client.table("emails")
            .select("id, status, created_at, prospects(id, email, full_name, ig_username, language, niche, comment)")
            .eq("status", EmailStatus.PENDING.value)
            .limit(limit)
            .execute()
        )
        return response.data or []