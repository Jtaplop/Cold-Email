from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from src.config.settings import settings


def get_google_credentials() -> Credentials:
    """
    Obtiene credenciales válidas de Google OAuth2 con los scopes configurados.
    Valida token local, refresca expirados o lanza flujo web si no existe o cambiaron scopes.
    """
    token_path = settings.GMAIL_TOKEN_FILE
    client_secret_path = settings.GMAIL_CREDENTIALS_FILE
    scopes = settings.GOOGLE_SCOPES

    creds: Credentials | None = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    needs_refresh = creds and creds.expired and creds.refresh_token
    has_valid_scopes = creds.has_scopes(scopes) if creds else False

    if not creds or not creds.valid or not has_valid_scopes:
        if needs_refresh and has_valid_scopes:
            creds.refresh(Request())
        else:
            if not client_secret_path.exists():
                raise FileNotFoundError(
                    f"No se encontró el archivo de credenciales en: {client_secret_path}\n"
                    "Descárgalo desde Google Cloud Console y colócalo en credentials/client_secret.json"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), scopes)
            creds = flow.run_local_server(port=0)

        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return creds