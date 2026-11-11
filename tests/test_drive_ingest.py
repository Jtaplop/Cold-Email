import sys
from pathlib import Path

# Agregar raíz del proyecto al sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import settings
from src.infrastructure.drive.drive_client import DriveClient
from src.infrastructure.files.csv_loader import load_prospects_from_csv


def test_drive_integration():
    print("=== TEST AISLADO DE CONEXIÓN CON GOOGLE DRIVE ===")
    folder_id = settings.GOOGLE_DRIVE_FOLDER_ID

    if not folder_id:
        print("[ERROR] GOOGLE_DRIVE_FOLDER_ID no está configurado en el archivo .env")
        return

    print(f"1. Conectando con Google Drive y escaneando carpeta: {folder_id}...")
    client = DriveClient()
    files = client.list_csv_files(root_folder_id=folder_id)

    print(f"2. Archivos CSV localizados: {len(files)}")
    for f in files:
        topic_info = f" [Tópico: {f.topic}]" if f.topic else " [Raíz]"
        print(f"   - {f.name} (ID: {f.file_id}){topic_info}")

    if not files:
        print("\n[INFO] Sube un archivo CSV a tu carpeta de Drive o a una subcarpeta para probar la lectura.")
        return

    first_file = files[0]
    print(f"\n3. Descargando a memoria y parseando: {first_file.name}...")
    stream = client.download_csv_as_stream(first_file.file_id)
    prospects = load_prospects_from_csv(stream, default_niche=first_file.topic)

    print(f"   -> Prospectos válidos detectados: {len(prospects)}")
    if prospects:
        sample = prospects[0]
        print(f"   -> Primer prospecto: {sample.full_name} | {sample.email} | Nicho: {sample.niche}")

    print("\n[ÉXITO] Verificación completada correctamente.")


if __name__ == "__main__":
    test_drive_integration()