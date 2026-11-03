from uuid import UUID
from src.infrastructure.gmail_client import GmailClient
from src.infrastructure.supabase_repo import SupabaseRepository
from src.domain.enums import EmailStatus

def run_phase3_test() -> None:
    print("--- INICIANDO TEST DE FASE 3: CONEXIÓN GMAIL API (BORRADORES) ---")
    
    repo = SupabaseRepository()
    emails_to_dispatch = repo.fetch_generated_emails_with_prospect(limit=5)
    
    if not emails_to_dispatch:
        print("[INFO] No hay correos en estado GENERATED en Supabase.")
        return

    print(f"Total correos listos para crear borrador: {len(emails_to_dispatch)}")
    
    # Inicializa GmailClient (abrirá el navegador la primera vez)
    gmail = GmailClient()

    for item in emails_to_dispatch:
        email_id = UUID(item["id"])
        subject = item["subject"]
        body_html = item["body_html"]
        prospect = item.get("prospects") or {}
        destinatario = prospect.get("email")

        print(f"\nCreando borrador para: {destinatario}...")
        try:
            draft_id = gmail.create_draft(to=destinatario, subject=subject, html_body=body_html)
            print(f"[OK] Borrador creado con éxito en Gmail (Draft ID: {draft_id})")

            # Actualizar estado en Supabase a DRAFTED
            repo.update_email_dispatched(email_id=email_id, new_status=EmailStatus.DRAFTED)
            print(f"[OK] Estado actualizado a DRAFTED en Supabase para Email ID: {email_id}")
        except Exception as exc:
            print(f"[ERROR] No se pudo procesar el correo {email_id}: {exc}")

if __name__ == "__main__":
    run_phase3_test()