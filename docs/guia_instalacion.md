# Guía de Puesta en Marcha: Cold-Email Engine

Esta guía detalla paso a paso cómo clonar, configurar el entorno, instalar dependencias, obtener las credenciales necesarias y verificar que el proyecto funcione en un ordenador completamente nuevo.

---

## 1. Requisitos Previos del Sistema

Antes de empezar, asegúrate de tener instalado en el nuevo PC:

1. **Git:** Descárgalo desde [git-scm.com](https://git-scm.com/) si no lo tienes instalado.
2. **Python (versión 3.11 o 3.12):** Asegúrate de marcar la casilla *"Add python.exe to PATH"* durante la instalación.
3. **uv (Gestor de paquetes rápido):**
   * En Windows (PowerShell):
     ```powershell
     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```
   * En Linux/macOS:
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

---

## 2. Clonación y Estructura de Carpetas

Abre la terminal en la carpeta donde quieras alojar el proyecto y ejecuta:

```powershell
# 1. Clonar el repositorio
git clone <URL_DE_TU_REPOSITORIO>
cd Cold-Email

# 2. Asegurar la existencia de directorios locales (ignorados en git)
mkdir credentials
mkdir data\inbox_csv
mkdir data\processed_csv
```

---

## 3. Creación del Entorno Virtual e Instalación de Dependencias

Con `uv` puedes crear el entorno e instalar todos los paquetes necesarios en cuestión de segundos:

```powershell
# 1. Crear entorno virtual con Python 3.12 (o 3.11)
uv venv --python 3.12

# 2. Activar entorno virtual
# En Windows:
.venv\Scripts\activate
# En Linux/macOS:
# source .venv/bin/activate

# 3. Instalar la totalidad de dependencias requeridas
uv pip install pydantic pydantic-settings supabase google-genai google-api-python-client google-auth-oauthlib jinja2 pyyaml email-validator
```

---

## 4. Dónde y Cómo Obtener las Claves y Credenciales

### A. Supabase (`SUPABASE_URL` y `SUPABASE_KEY`)

1. Inicia sesión en tu panel de [Supabase](https://supabase.com/dashboard).
2. Entra en tu proyecto (o crea uno nuevo).
3. **Crear las tablas en la Base de Datos:** Ve a **SQL Editor** (icono de terminal a la izquierda) y ejecuta este script DDL:
   ```sql
   create table if not exists prospects (
       id uuid primary key default gen_random_uuid(),
       ig_username text unique,
       email text not null unique,
       full_name text,
       language text not null default 'es',
       niche text,
       comment text,
       created_at timestamptz not null default now(),
       updated_at timestamptz not null default now()
   );

   create table if not exists emails (
       id uuid primary key default gen_random_uuid(),
       prospect_id uuid not null references prospects(id) on delete cascade,
       subject text,
       body_html text,
       status text not null default 'PENDING',
       error_message text,
       created_at timestamptz not null default now(),
       processed_at timestamptz
   );
   ```
4. **Obtener la URL:** Haz clic en el botón verde **Connect** en la parte superior del dashboard o ve a **Project Settings** $\rightarrow$ **API** $\rightarrow$ copia el valor de **Project URL**.
5. **Obtener la Clave Secreta:** Ve a **Project Settings** $\rightarrow$ **API Keys** $\rightarrow$ copia la clave en **Secret keys** (`sb_secret_...`) o pulsa en **View legacy API keys** y copia la clave `service_role`.

---

### B. Google Gemini API (`GEMINI_API_KEY`)

1. Accede a [Google AI Studio](https://aistudio.google.com/).
2. Inicia sesión con tu cuenta de Google.
3. Haz clic en **Get API key** $\rightarrow$ **Create API key**.
4. Copia la cadena generada (`AIzaSy...`).

---

### C. Google Cloud: Gmail API (`client_secret.json`)

1. Accede a [Google Cloud Console](https://console.cloud.google.com/).
2. Selecciona tu proyecto o crea uno nuevo (ej. `Cold-Email-Engine`).
3. **Habilitar API:**
   * Ve a **APIs & Services** $\rightarrow$ **Library**.
   * Busca `Gmail API` y pulsa **Enable**.
4. **Pantalla de Consentimiento OAuth:**
   * Ve a **APIs & Services** $\rightarrow$ **OAuth consent screen**.
   * Elige **External** y pulsa **Create**.
   * Rellena nombre de la app (`Cold Email Dispatcher`) y tus correos de soporte/contacto.
   * En la pestaña **Scopes**: Añade `https://www.googleapis.com/auth/gmail.compose`.
   * En la pestaña **Test users** (*Crítico*): Pulsa **Add Users** y añade el correo exacto de Gmail desde el que crearás los borradores/enviarás.
   * Guarda los cambios.
5. **Descargar Credencial:**
   * Ve a **APIs & Services** $\rightarrow$ **Credentials**.
   * Pulsa **+ Create Credentials** $\rightarrow$ **OAuth client ID**.
   * Application type: **Desktop app**.
   * Haz clic en **Create** y luego en **Download JSON**.
   * Renombra el archivo descargado a:
     ```text
     client_secret.json
     ```
   * Muévelo a la carpeta `credentials/` del proyecto:
     ```text
     credentials/client_secret.json
     ```

---

## 5. Archivo de Variables de Entorno (`.env`)

Crea un archivo llamado `.env` en la raíz del proyecto con la siguiente estructura:

```env
# ==========================================
# SUPABASE
# ==========================================
SUPABASE_URL=https://xxxxxxxxxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=sb_secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ==========================================
# GOOGLE GEMINI
# ==========================================
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ==========================================
# GMAIL API & STORAGE
# ==========================================
GMAIL_CREDENTIALS_FILE=credentials/client_secret.json
GMAIL_TOKEN_FILE=credentials/token.json
INBOX_CSV_DIR=data/inbox_csv
PROCESSED_CSV_DIR=data/processed_csv
```

---

## 6. Verificación Paso a Paso del Sistema

Para confirmar que todo el stack está operativo en el nuevo PC, ejecuta secuencialmente las pruebas:

### Prueba 1: Ingesta CSV y Persistencia Relacional
```powershell
uv run test_phase1.py
```
* **Qué hace:** Crea un CSV de prueba en `data/inbox_csv/test_leads.csv`, valida los datos con Pydantic y los persiste en Supabase con estado `PENDING`.

---

### Prueba 2: Redacción con IA (Gemini) y Maquetación Jinja2
```powershell
uv run test_phase2.py
```
* **Qué hace:** Toma los correos `PENDING`, ejecuta el modelo `gemini-3.8-flash` con salida estructurada, renderiza el cuerpo HTML con la plantilla y actualiza el estado en Supabase a `GENERATED`.

---

### Prueba 3: Autenticación Gmail y Creación de Borradores
```powershell
uv run test_phase3.py
```
* **Qué hace:** 
  1. Abrirá el navegador para que autorices la aplicación con tu cuenta de Google (solo la primera vez).
  2. Generará automáticamente `credentials/token.json`.
  3. Creará los borradores en tu bandeja de Gmail y actualizará el estado en Supabase a `DRAFTED`.

---

## Resumen de Comandos Rápidos

```powershell
# Clonar y entrar
git clone <URL>
cd Cold-Email

# Entorno e instalación
uv venv --python 3.12
.venv\Scripts\activate
uv pip install pydantic pydantic-settings supabase google-genai google-api-python-client google-auth-oauthlib jinja2 pyyaml email-validator

# Carpetas
mkdir credentials, data\inbox_csv, data\processed_csv

# (Colocar .env en la raíz y client_secret.json en credentials/)

# Ejecución de verificación
uv run test_phase1.py
uv run test_phase2.py
uv run test_phase3.py
```