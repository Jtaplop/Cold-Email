import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.services.generation.generator_service import GeneratorService
from src.infrastructure.database.supabase_repo import SupabaseRepository
from src.domain.enums import EmailStatus

def run_phase2_test() -> None:
    print("--- INICIANDO TEST DE FASE 2: GENERACIÓN CON IA ---")
    
    service = GeneratorService()
    generados = service.process_pending_emails(limit=5)
    
    print(f"\nProceso finalizado. Total correos generados con éxito: {generados}")

    # Verificación en Supabase
    repo = SupabaseRepository()
    response = (
        repo.client.table("emails")
        .select("id, subject, body_html, status, prospects(email)")
        .eq("status", EmailStatus.GENERATED.value)
        .limit(2)
        .execute()
    )

    print("\n--- MUESTRA DEL RESULTADO GUARDADO EN SUPABASE ---")
    for row in response.data:
        email = row.get("prospects", {}).get("email")
        print(f"\nID: {row['id']} | Destinatario: {email}")
        print(f"Asunto: {row['subject']}")
        print("Cuerpo HTML (primeros 250 caracteres):")
        print(row['body_html'][:250] + "...")

if __name__ == "__main__":
    run_phase2_test()