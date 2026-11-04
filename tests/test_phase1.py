import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pathlib import Path
from src.infrastructure.files.csv_loader import load_prospects_from_csv
from src.infrastructure.database.supabase_repo import SupabaseRepository

def run_test() -> None:
    csv_path = Path("data/inbox_csv/test_leads.csv")
    
    # 1. Asegurar archivo de prueba
    if not csv_path.exists():
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_text(
            "Usuario IG,nombre completo,email,idioma,nicho,comentario\n"
            "@marcos_fitness,Marcos Pérez,marcos@fitnesspro.com,es,Entrenamiento Online,Tiene canal de YouTube activo\n"
            "laura_design,Laura Gómez,laura@gomezstudio.es,es,Diseño UI/UX,Busca automatizar captación\n",
            encoding="utf-8"
        )
        print(f"[OK] Creado archivo de prueba en {csv_path}")

    # 2. Leer y validar con Pydantic
    print("\n--- 1. Leyendo y validando CSV ---")
    prospects = load_prospects_from_csv(csv_path)
    print(f"Total prospectos validados: {len(prospects)}")
    for p in prospects:
        print(f" -> {p.full_name} | IG: {p.ig_username} | Email: {p.email} | Nicho: {p.niche}")

    # 3. Persistencia en Supabase
    print("\n--- 2. Persistiendo en Supabase ---")
    repo = SupabaseRepository()
    for p in prospects:
        prospect_id = repo.upsert_prospect(p)
        email_id = repo.create_pending_email(prospect_id)
        print(f"Guardado: Prospect ID={prospect_id} -> Email ID={email_id}")

    # 4. Verificar consulta relacional
    print("\n--- 3. Verificando lectura relacional de la cola ---")
    pending = repo.fetch_pending_emails_with_prospect(limit=5)
    print(f"Total correos PENDING en cola: {len(pending)}")
    for item in pending:
        prospect = item.get("prospects", {})
        print(f"Email ID: {item['id']} | Destinatario: {prospect.get('email')} ({prospect.get('full_name')})")

if __name__ == "__main__":
    run_test()