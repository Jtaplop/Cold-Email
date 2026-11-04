import argparse
import asyncio
from pathlib import Path

from src.config.settings import settings
from src.infrastructure.files.csv_loader import archive_processed_csv, load_prospects_from_csv
from src.infrastructure.email.gmail_client import GmailClient
from src.infrastructure.database.supabase_repo import SupabaseRepository
from src.services.generation.generator_service import GeneratorService
from src.services.dispatch.queue_worker import QueueWorker
from src.services.reporting.stats_reporter import ExecutionStats


def ingest_csv_files(repo: SupabaseRepository, stats: ExecutionStats) -> None:
    """Busca CSVs en inbox_csv, inserta prospectos y crea correos PENDING."""
    inbox_dir = settings.INBOX_CSV_DIR
    inbox_dir.mkdir(parents=True, exist_ok=True)
    csv_files = list(inbox_dir.glob("*.csv"))

    if not csv_files:
        print("[INGESTA] No se encontraron archivos CSV en data/inbox_csv/")
        return

    for csv_file in csv_files:
        print(f"\n[INGESTA] Procesando archivo: {csv_file.name}")
        prospects = load_prospects_from_csv(csv_file)
        stats.csv_leads_found += len(prospects)

        for p in prospects:
            try:
                prospect_id = repo.upsert_prospect(p)
                repo.create_pending_email(prospect_id)
                stats.csv_leads_ingested += 1
            except Exception as exc:
                stats.errors.append(f"Fallo persistiendo prospecto {p.email}: {exc}")

        archived = archive_processed_csv(csv_file)
        print(f"[INGESTA-OK] Archivo archivado en: {archived.name}")


async def async_pipeline(mode: str, limit: int, skip_ingest: bool) -> None:
    stats = ExecutionStats()
    repo = SupabaseRepository()

    # 1. Ingesta de archivos CSV (si no se omitió)
    if not skip_ingest:
        ingest_csv_files(repo, stats)
    else:
        print("[INFO] Bandera --skip-ingest activa. Omitiendo lectura de CSV.")

    # 2. Inicialización de clientes y servicios
    gmail_client = GmailClient()
    generator = GeneratorService()
    worker = QueueWorker(
        repo=repo,
        gmail_client=gmail_client,
        stats=stats,
        mode=mode,
    )

    producer_finished = asyncio.Event()

    # 3. Lanzar Productor y Consumidor concurrentemente
    print(f"\n[PIPELINE] Arrancando Productor (IA) y Consumidor ({mode.upper()}) en paralelo...\n")
    await asyncio.gather(
        generator.run_producer(finished_event=producer_finished, stats=stats, limit=limit),
        worker.run(producer_finished=producer_finished),
    )

    # 4. Imprimir resumen
    stats.print_summary()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cold Email Engine: Motor automatizado de prospección con IA y Gmail API."
    )
    parser.add_argument(
        "--mode",
        choices=["draft", "send"],
        default="draft",
        help="Modo de ejecución: 'draft' crea borradores en Gmail; 'send' envía correos reales con jitter.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Límite máximo de correos a procesar en esta ejecución.",
    )
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Omite la lectura de archivos CSV y procesa solo lo que ya esté en Supabase.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    asyncio.run(
        async_pipeline(
            mode=args.mode,
            limit=args.limit,
            skip_ingest=args.skip_ingest,
        )
    )