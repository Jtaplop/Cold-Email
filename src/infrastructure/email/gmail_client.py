import base64
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from src.config.settings import settings

SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


class GmailClient:
    def __init__(self) -> None:
        self.creds: Credentials | None = None
        self._authenticate()
        self.service = build("gmail", "v1", credentials=self.creds)

    def _authenticate(self) -> None:
        """Carga o genera las credenciales OAuth2 del usuario."""
        token_path = settings.GMAIL_TOKEN_FILE
        client_secret_path = settings.GMAIL_CREDENTIALS_FILE

        if token_path.exists():
            self.creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not client_secret_path.exists():
                    raise FileNotFoundError(
                        f"No se encontró el archivo de credenciales en: {client_secret_path}\n"
                        "Descárgalo desde Google Cloud Console y colócalo en credentials/client_secret.json"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
                self.creds = flow.run_local_server(port=0)

            # Guardar el token para ejecuciones posteriores
            token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(token_path, "w", encoding="utf-8") as token_file:
                token_file.write(self.creds.to_json())

    def _build_raw_message(self, to: str, subject: str, html_body: str) -> dict:
        """Construye el MIMEText HTML y lo codifica en Base64 URL-safe."""
        message = MIMEText(html_body, "html", "utf-8")
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return {"raw": raw}

    def create_draft(self, to: str, subject: str, html_body: str) -> str:
        """Crea un borrador en la bandeja de entrada del usuario."""
        raw_message = self._build_raw_message(to, subject, html_body)
        draft = (
            self.service.users()
            .drafts()
            .create(userId="me", body={"message": raw_message})
            .execute()
        )
        return draft.get("id", "")

    def send_message(self, to: str, subject: str, html_body: str) -> str:
        """Envía el correo directamente."""
        raw_message = self._build_raw_message(to, subject, html_body)
        sent = (
            self.service.users()
            .messages()
            .send(userId="me", body=raw_message)
            .execute()
        )
        return sent.get("id", "")