import io
from dataclasses import dataclass
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from src.infrastructure.auth.google_auth import get_google_credentials


@dataclass
class RemoteSheetFile:
    file_id: str
    name: str
    topic: str
    mime_type: str


class DriveClient:
    def __init__(self) -> None:
        self.creds = get_google_credentials()
        self.service = build("drive", "v3", credentials=self.creds)

    def list_prospect_sheets(self, folder_id: str) -> list[RemoteSheetFile]:
        """
        Lista todas las hojas de cálculo (Google Sheets o CSV) dentro de la carpeta PROSPECTOS.
        El nombre del archivo define el tópico/nicho de prospección.
        """
        query = (
            f"'{folder_id}' in parents and "
            "("
            "mimeType = 'application/vnd.google-apps.spreadsheet' or "
            "mimeType = 'text/csv' or "
            "name contains '.csv'"
            ") and trashed = false"
        )
        resp = self.service.files().list(
            q=query,
            fields="files(id, name, mimeType)",
            spaces="drive",
            orderBy="name"
        ).execute()

        items = resp.get("files", [])
        sheets: list[RemoteSheetFile] = []

        for item in items:
            raw_name = item["name"]
            # Limpiar extensión para obtener un tópico limpio (ej. 'psicologia.csv' -> 'psicologia')
            clean_topic = raw_name.replace(".csv", "").strip().capitalize()
            sheets.append(
                RemoteSheetFile(
                    file_id=item["id"],
                    name=raw_name,
                    topic=clean_topic,
                    mime_type=item["mimeType"],
                )
            )

        return sheets

    def download_sheet_as_csv_stream(self, file: RemoteSheetFile) -> io.StringIO:
        """
        Descarga el archivo a memoria. Si es un Google Sheet nativo, lo exporta
        automáticamente a formato CSV al vuelo vía Drive API.
        """
        if file.mime_type == "application/vnd.google-apps.spreadsheet":
            request = self.service.files().export_media(
                fileId=file.file_id,
                mimeType="text/csv"
            )
        else:
            request = self.service.files().get_media(fileId=file.file_id)

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)
        content = fh.read().decode("utf-8-sig", errors="replace")
        return io.StringIO(content)