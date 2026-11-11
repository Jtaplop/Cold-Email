import sys
from pathlib import Path

# Garantiza que la raíz del proyecto esté en el path de búsqueda de módulos
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import asyncio
from src.infrastructure.database.supabase_repo import SupabaseRepository
from src.infrastructure.email.gmail_client import GmailClient
from src.services.dispatch.queue_worker import QueueWorker
from src.services.generation.generator_service import GeneratorService
from src.services.ingestion.ingestion_service import IngestionService
from src.services.reporting.stats_reporter import ExecutionStats

async def async_pipeline(
    mode: str,
    limit: int,
    skip_ingest: bool,
    sheet: str | None = None,
    drive_folder_id: str | None = None,
) -> None:
    stats = ExecutionStats()
    repo = SupabaseRepository()

    # 1. Sincronización dinámica desde Google Drive
    if not skip_ingest:
        ingestion_service = IngestionService(repo=repo)
        ingestion_service.ingest(
            stats=stats,
            sheet_filter=sheet,
            drive_folder_id=drive_folder_id,
        )
    else:
        print("[INFO] Bandera --skip-ingest activa. Omitiendo lectura de Sheets.")

    # 2. Clientes y servicios
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
        description="Cold Email Engine: Motor automatizado con Sheets dinámicos, Gemini y Gmail API."
    )
    parser.add_argument(
        "--mode",
        choices=["draft", "send"],
        default="draft",
        help="Modo de ejecución: 'draft' crea borradores en Gmail; 'send' envía correos con jitter.",
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
        help="Omite la sincronización con Drive y procesa lo que ya está en Supabase.",
    )
    parser.add_argument(
        "--sheet",
        type=str,
        default=None,
        help="Nombre o tópico del Sheet a procesar (ej. 'psicologia', 'fitness', o 'all'). Si no se indica, se muestra un menú interactivo.",
    )
    parser.add_argument(
        "--drive-folder-id",
        type=str,
        default=None,
        help="ID de carpeta en Google Drive (invalida el valor de .env).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    asyncio.run(
        async_pipeline(
            mode=args.mode,
            limit=args.limit,
            skip_ingest=args.skip_ingest,
            sheet=args.sheet,
            drive_folder_id=args.drive_folder_id,
        )
    )