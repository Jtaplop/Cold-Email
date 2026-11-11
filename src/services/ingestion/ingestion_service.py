from src.config.settings import settings
from src.domain.models import ProspectCreate
from src.infrastructure.database.supabase_repo import SupabaseRepository
from src.infrastructure.drive.drive_client import DriveClient, RemoteSheetFile
from src.infrastructure.files.csv_loader import load_prospects_from_csv
from src.services.reporting.stats_reporter import ExecutionStats


class IngestionService:
    def __init__(self, repo: SupabaseRepository) -> None:
        self.repo = repo
        self._drive_client: DriveClient | None = None

    @property
    def drive_client(self) -> DriveClient:
        if self._drive_client is None:
            self._drive_client = DriveClient()
        return self._drive_client

    def ingest(
        self,
        stats: ExecutionStats,
        sheet_filter: str | None = None,
        drive_folder_id: str | None = None,
    ) -> None:
        """Sincroniza los prospectos de Google Sheets con Supabase de forma incremental."""
        folder_id = drive_folder_id or settings.GOOGLE_DRIVE_FOLDER_ID
        if not folder_id:
            print("[INGESTA] Error: GOOGLE_DRIVE_FOLDER_ID no configurado.")
            return

        print(f"[INGESTA] Escaneando carpeta de prospectos en Drive...")
        try:
            available_sheets = self.drive_client.list_prospect_sheets(folder_id)
        except Exception as exc:
            err_msg = f"Fallo al conectar con Google Drive: {exc}"
            print(f"[ERROR] {err_msg}")
            stats.errors.append(err_msg)
            return

        if not available_sheets:
            print("[INGESTA] No se encontraron hojas de cálculo en la carpeta configurada.")
            return

        # Selección de hojas (automática por filtro o interactiva en consola)
        selected_sheets = self._resolve_target_sheets(available_sheets, sheet_filter)
        if not selected_sheets:
            print("[INGESTA] Ninguna hoja seleccionada para procesar.")
            return

        for sheet in selected_sheets:
            self._sync_single_sheet(sheet=sheet, stats=stats)

    def _resolve_target_sheets(
        self, available: list[RemoteSheetFile], sheet_filter: str | None
    ) -> list[RemoteSheetFile]:
        """Resuelve qué hojas procesar: por parámetro CLI o preguntando en terminal."""
        if sheet_filter:
            filter_lower = sheet_filter.lower().strip()
            if filter_lower == "all" or filter_lower == "todas":
                return available
            matches = [
                s for s in available
                if filter_lower in s.name.lower() or filter_lower in s.topic.lower()
            ]
            if not matches:
                print(f"[AVISO] No se encontró ninguna hoja que coincida con '{sheet_filter}'.")
            return matches

        # Menú interactivo por consola
        print("\n" + "=" * 50)
        print("   SELECCIONA LA LISTA A PROCESAR (DRIVE)")
        print("=" * 50)
        for idx, sheet in enumerate(available, start=1):
            print(f" [{idx}] {sheet.topic} ({sheet.name})")
        print(f" [{len(available) + 1}] Procesar TODAS las listas")
        print(" [0] Cancelar")
        print("=" * 50)

        while True:
            choice = input(f"Selecciona una opción [1-{len(available) + 1}]: ").strip()
            if choice == "0":
                return []
            if choice == str(len(available) + 1):
                return available
            if choice.isdigit() and 1 <= int(choice) <= len(available):
                return [available[int(choice) - 1]]
            print("Opción inválida. Inténtalo de nuevo.")

    def _sync_single_sheet(self, sheet: RemoteSheetFile, stats: ExecutionStats) -> None:
        """Descarga una hoja, analiza los leads y guarda en Supabase los que sean nuevos."""
        print(f"\n[SINCRONIZANDO] Hoja: {sheet.name} | Tópico: [{sheet.topic}]")
        try:
            csv_stream = self.drive_client.download_sheet_as_csv_stream(sheet)
            prospects = load_prospects_from_csv(csv_stream, default_niche=sheet.topic)
            stats.csv_leads_found += len(prospects)

            new_leads = 0
            existing_leads = 0

            for p in prospects:
                try:
                    # 1. Upsert o rescate del prospecto en Supabase
                    prospect_id = self.repo.upsert_prospect(p)

                    # 2. Escudo anti-duplicados: verificar si ya fue procesado o enviado
                    if self.repo.has_existing_email(prospect_id):
                        existing_leads += 1
                        stats.csv_leads_skipped += 1
                        continue

                    # 3. Solo si no tiene email previo se añade a la cola PENDING
                    self.repo.create_pending_email(prospect_id)
                    new_leads += 1
                    stats.csv_leads_ingested += 1
                    print(f"  [+ NUEVO LEAD] {p.email} ({p.full_name or 'Sin nombre'}) -> PENDING")

                except Exception as exc:
                    err_msg = f"Error guardando lead {p.email}: {exc}"
                    print(f"  [ERROR] {err_msg}")
                    stats.errors.append(err_msg)

            print(f"[RESUMEN HOJA] {sheet.topic}: {new_leads} nuevos leads encolados | {existing_leads} ya existían (sin cambios).")

        except Exception as exc:
            err_msg = f"Error leyendo hoja {sheet.name}: {exc}"
            print(f"[ERROR] {err_msg}")
            stats.errors.append(err_msg)