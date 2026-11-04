import csv
import shutil
from datetime import datetime
from pathlib import Path
from src.config.settings import settings
from src.domain.models import ProspectCreate


COLUMN_MAPPING = {
    "usuario ig": "ig_username",
    "usuario_ig": "ig_username",
    "instagram": "ig_username",
    "nombre completo": "full_name",
    "nombre": "full_name",
    "email": "email",
    "correo": "email",
    "idioma": "language",
    "nicho": "niche",
    "comentario": "comment",
    "comentarios": "comment",
}


def load_prospects_from_csv(file_path: Path) -> list[ProspectCreate]:
    """
    Lee un archivo CSV delimitado por comas, mapea sus encabezados
    y valida cada fila contra el modelo ProspectCreate.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo: {file_path}")

    prospects: list[ProspectCreate] = []

    with open(file_path, mode="r", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if not reader.fieldnames:
            return []

        # Normalizar los nombres de las cabeceras detectadas a minúsculas
        header_map = {
            col: COLUMN_MAPPING.get(col.strip().lower(), None)
            for col in reader.fieldnames
        }

        for row_index, row in enumerate(reader, start=2):
            payload: dict[str, str | None] = {}
            for original_header, mapped_attr in header_map.items():
                if mapped_attr:
                    val = row.get(original_header)
                    payload[mapped_attr] = val.strip() if val else None

            # Si la fila carece de email, se descarta para proteger la integridad
            if not payload.get("email"):
                continue

            try:
                lead = ProspectCreate(**payload)
                prospects.append(lead)
            except Exception as exc:
                print(f"[WARN] Fila {row_index} descartada por error de validación: {exc}")

    return prospects


def archive_processed_csv(source_file: Path) -> Path:
    """Mueve el CSV procesado a data/processed_csv/ con un prefijo temporal."""
    settings.PROCESSED_CSV_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_path = settings.PROCESSED_CSV_DIR / f"{timestamp}_{source_file.name}"
    shutil.move(str(source_file), str(target_path))
    return target_path