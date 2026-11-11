import csv
import io
from datetime import datetime
from pathlib import Path
from typing import TextIO
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
    "nicho de mercado": "niche",
    "sector": "niche",
    "topico": "niche",
    "tópico": "niche",
    "topic": "niche",
    "comentario": "comment",
    "comentarios": "comment",
}


def load_prospects_from_csv(
    source: Path | str | TextIO,
    default_niche: str | None = None,
) -> list[ProspectCreate]:
    """
    Lee datos delimitados por coma desde un archivo en disco o un buffer de memoria (TextIO),
    mapea los encabezados dinámicamente, asigna el tópico por defecto si falta y valida
    cada fila contra el modelo ProspectCreate.
    """
    prospects: list[ProspectCreate] = []

    if isinstance(source, (str, Path)):
        file_path = Path(source)
        if not file_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo local: {file_path}")
        with open(file_path, mode="r", encoding="utf-8-sig") as f:
            return _parse_csv_content(f, default_niche=default_niche)

    return _parse_csv_content(source, default_niche=default_niche)


def _parse_csv_content(
    stream: TextIO,
    default_niche: str | None = None,
) -> list[ProspectCreate]:
    """Parsea el stream de texto respetando los encabezados normalizados."""
    prospects: list[ProspectCreate] = []
    reader = csv.DictReader(stream)

    if not reader.fieldnames:
        return prospects

    header_map = {
        col: COLUMN_MAPPING.get(col.strip().lower(), None)
        for col in reader.fieldnames
        if col
    }

    for row_index, row in enumerate(reader, start=2):
        payload: dict[str, str | None] = {}
        for original_header, mapped_attr in header_map.items():
            if mapped_attr:
                val = row.get(original_header)
                payload[mapped_attr] = val.strip() if val else None

        # Si no existe nicho específico en la fila, asignamos el inferido por la carpeta/tópico
        if not payload.get("niche") and default_niche:
            payload["niche"] = default_niche

        # Descarte de seguridad si la fila carece de email válido
        raw_email = payload.get("email")
        if not raw_email or "@" not in raw_email or raw_email.strip() in {"?", "-", "null", "none"}:
            continue

        try:
            lead = ProspectCreate(**payload)
            prospects.append(lead)
        except Exception as exc:
            print(f"[WARN] Fila {row_index} descartada por validación: {exc}")

    return prospects


def archive_processed_csv(source_file: Path) -> Path:
    """Mueve el CSV local procesado a data/processed_csv/ con prefijo temporal."""
    import shutil

    settings.PROCESSED_CSV_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_path = settings.PROCESSED_CSV_DIR / f"{timestamp}_{source_file.name}"
    shutil.move(str(source_file), str(target_path))
    return target_path