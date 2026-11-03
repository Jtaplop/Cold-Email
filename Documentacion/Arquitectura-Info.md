# Arquitectura y Roadmap: Motor de Envío de Correos Personalizados con IA

Este documento define la arquitectura backend, la estructura de directorios, el diseño de datos y el plan de implementación paso a paso para el sistema automatizado de generación, evaluación y despacho de correos electrónicos.

---

## 1. Principios Arquitectónicos y Reglas de Diseño

Para garantizar que ningún archivo supere las **300 líneas de código** y que modificar el cuerpo del correo o los criterios del Juez no requiera tocar la lógica de Python, aplicaremos:

1. **Arquitectura Hexagonal / Clean Architecture simplificada:**
   * **`domain/`**: Modelos de datos puros (Pydantic) y estados del flujo.
   * **`services/`**: Lógica de negocio específica (Generador IA, Juez IA, Orquestador de Cola).
   * **`infrastructure/`**: Clientes externos aislados (Supabase, Gmail API OAuth2, Google GenAI SDK, Lector CSV).
   * **`templates/` (Prompts y Cuerpos desacoplados):** Todo el texto de los prompts, las instrucciones del Juez y la estructura base del correo vivirán en archivos `.yaml` o `.j2` (Jinja2) fuera del código Python.
2. **Esquemas Dinámicos para el CSV (`extra="allow"`):**
   * El modelo de entrada en Pydantic tendrá campos base obligatorios (`email`) y permitirá cualquier columna nueva que añadas al CSV en el futuro sin romper el código, inyectándola dinámicamente en el contexto de la IA.
3. **Patrón Productor-Consumidor Asíncrono (`asyncio`):**
   * **Productor:** Lee el CSV $\rightarrow$ Registra en Supabase $\rightarrow$ Genera correo con Gemini $\rightarrow$ Evalúa con el Juez $\rightarrow$ Actualiza estado en Supabase (`QUEUED_TO_SEND` o `QUEUED_TO_DRAFT`).
   * **Consumidor (Dispatcher):** Lee la cola de Supabase $\rightarrow$ Ejecuta llamada a Gmail API (`messages.send` o `drafts.create`) $\rightarrow$ Aplica *jitter* (pausa aleatoria) entre envíos reales.

---

## 2. Estructura del Proyecto (Árbol de Directorios)

Cada archivo tiene una responsabilidad única (Single Responsibility Principle), manteniéndose entre 40 y 180 líneas de código como máximo:

```text
cold_email_engine/
├── .env.example                 # Variables de entorno (Supabase, Google Cloud Project)
├── credentials/                 # Carpeta ignorada en Git para OAuth2
│   ├── client_secret.json       # Credencial descargada de Google Cloud
│   └── token.json               # Token autogenerado tras el primer login
├── data/
│   ├── inbox_csv/               # Carpeta donde depositas los CSV a procesar
│   └── processed_csv/           # Histórico de CSV ya procesados
├── templates/                   # CERO código Python aquí (Fácil edición)
│   ├── email_base.html.j2       # Estructura HTML limpia (firma, formato base)
│   ├── generator_prompt.yaml    # Sketch del correo, tono, ángulos e instrucciones
│   └── judge_rubric.yaml        # Reglas de evaluación, umbrales y filtros del Juez
├── src/
│   ├── config/
│   │   └── settings.py          # Carga de .env con pydantic-settings (< 60 líneas)
│   ├── domain/
│   │   ├── models.py            # DTOs: LeadData, GeneratedEmail, JudgeVerdict (< 100 líneas)
│   │   └── enums.py             # Estados: PENDING, QUEUED_SEND, QUEUED_DRAFT, SENT, DRAFTED, ERROR
│   ├── infrastructure/
│   │   ├── csv_loader.py        # Lectura de CSV y conversión a modelos dinámicos (< 80 líneas)
│   │   ├── supabase_repo.py     # CRUD de leads, cola y estadísticas (< 150 líneas)
│   │   ├── gemini_client.py     # Wrapper del SDK google-genai con Structured Outputs (< 120 líneas)
│   │   └── gmail_client.py      # OAuth2, creación de MIME, send_message y create_draft (< 180 líneas)
│   ├── services/
│   │   ├── prompt_builder.py    # Combina YAML + Jinja2 + variables del CSV (< 100 líneas)
│   │   ├── generator_service.py # Orquesta la redacción del email (< 90 líneas)
│   │   ├── judge_service.py     # Evalúa el email y decide SEND vs DRAFT (< 100 líneas)
│   │   ├── queue_worker.py      # Consumidor con pausas aleatorias (jitter) (< 140 líneas)
│   │   └── stats_reporter.py    # Resumen final en consola al terminar la ejecución (< 80 líneas)
│   └── main.py                  # Punto de entrada que coordina el pipeline (< 100 líneas)
└── requirements.txt
```

---

## 3. Diseño de los Módulos Clave

### A. Sistema de Plantillas y Prompts Modificables (`templates/`)
Para que puedas iterar el cuerpo del correo y los criterios del Juez en segundos sin tocar Python:

* **`templates/generator_prompt.yaml`**:
  ```yaml
  system_instruction: |
    Eres un experto redactando propuestas B2B personalizadas, directas y sin relleno corporativo.
  email_sketch: |
    1. Gancho hiper-específico basado en {{ lead.company }} y {{ lead.custom_observation }}.
    2. Conexión rápida con el problema detectado: {{ lead.pain_point }}.
    3. Propuesta de valor directa en 2 líneas.
    4. Call to Action (CTA) de baja fricción.
  constraints:
    - Longitud máxima: 120 palabras.
    - Tono: Natural, de tú a tú, profesional pero cercano.
    - Prohibido usar frases cliché como "Espero que este correo te encuentre bien".
  ```

* **`templates/judge_rubric.yaml`** (Escalable desde básico hasta avanzado):
  ```yaml
  pass_threshold: 80 # Puntuación mínima sobre 100 para enviar directo
  active_rules:
    - id: no_placeholders
      description: "No debe contener corchetes sin rellenar como [Nombre] o {{variable}}."
      critical: true # Si falla una regla crítica, va directo a Draft aunque tenga buena nota
    - id: word_count
      description: "El correo debe ser conciso y directo, menos de 150 palabras."
      critical: false
    - id: natural_tone
      description: "No debe sonar a plantilla genérica ni usar lenguaje robótico."
      critical: true
  ```

### B. Salidas Estructuradas (Pydantic + Gemini API)
Tanto el Generador como el Juez devolverán objetos tipados mediante `response_schema` de la API de Google:

* **Respuesta del Generador (`GeneratedEmailSchema`):**
  * `subject`: `str`
  * `body_paragraphs`: `list[str]` (Luego se inyectan en `email_base.html.j2` para asegurar que el formato HTML, saltos de línea y tu firma queden siempre impecables).
* **Respuesta del Juez (`JudgeVerdictSchema`):**
  * `passed`: `bool`
  * `score`: `int` (0-100)
  * `failed_rules`: `list[str]`
  * `reasoning`: `str` (Se guarda en Supabase para que sepas *por qué* se mandó a Draft).

### C. Modelo de Persistencia en Supabase
Una única tabla principal `email_campaigns_queue` que actúa como registro histórico y cola de trabajo:

| Columna | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | `uuid` (PK) | Identificador único |
| `email` | `text` (Unique/Index) | Correo del destinatario (evita duplicados) |
| `lead_metadata` | `jsonb` | Todas las columnas extra del CSV guardadas dinámicamente |
| `status` | `text` | `PENDING`, `QUEUED_SEND`, `QUEUED_DRAFT`, `SENT`, `DRAFTED`, `FAILED` |
| `generated_subject` | `text` | Asunto redactado por Gemini |
| `generated_body_html`| `text` | Cuerpo final renderizado |
| `judge_score` | `int4` | Nota asignada por el Juez |
| `judge_feedback` | `text` | Motivo de aprobación o de desvío a Draft |
| `processed_at` | `timestamptz` | Fecha de envío o creación de borrador |

---

## 4. Flujo de Ejecución Concurrente

1. **Inicio del Script (`main.py`):**
   * Verifica conexión con Supabase y validez del `token.json` de Gmail API.
2. **Fase 1: Ingesta (`csv_loader.py` $\rightarrow$ `supabase_repo.py`):**
   * Lee los CSV de `data/inbox_csv/`.
   * Verifica contra Supabase qué correos no se han procesado aún y los inserta en estado `PENDING` guardando sus variables en `lead_metadata` (`JSONB`).
3. **Fase 2: Pipeline Productor-Consumidor (`asyncio.gather`):**
   * **Corrutina Productora (Rápida):**
     * Toma los `PENDING`, construye el prompt inyectando `lead_metadata`, llama al **Generador**, pasa el resultado al **Juez** y actualiza la fila en Supabase a `QUEUED_SEND` (si `passed == True`) o `QUEUED_DRAFT` (si `passed == False`).
   * **Corrutina Consumidora / Cola (Controlada):**
     * Escucha la cola en Supabase.
     * Si hay un `QUEUED_DRAFT`: Llama a `users.drafts.create` de Gmail API inmediatamente (no requiere esperar pausa larga porque no sale a internet) y marca como `DRAFTED`.
     * Si hay un `QUEUED_SEND`: Llama a `users.messages.send` de Gmail API, marca como `SENT` y activa el `await asyncio.sleep(random.uniform(45, 110))` antes de enviar el siguiente correo real.
4. **Fase 3: Cierre y Estadísticas (`stats_reporter.py`):**
   * Una vez vaciada la cola de generación y envío, imprime en consola el informe final:
     * Total leídos del CSV vs Omitidos por duplicidad.
     * Total Enviados con éxito (`SENT`).
     * Total Desviados a Borradores (`DRAFTED`) + desglose de motivos del Juez.
     * Tiempo total de ejecución y errores (si los hubiera).

---

## 5. Roadmap de Implementación (Paso a Paso)

Desarrollaremos el backend en **5 Fases iterativas**. No pasaremos a la siguiente hasta que la anterior esté probada y validada:

### Fase 1: Cimientos, Configuración y Persistencia (Supabase + CSV Dinámico)
* **Objetivo:** Leer cualquier CSV con columnas arbitrarias y sincronizarlo con Supabase sin duplicar contactos.
* **Entregables:**
  1. Script SQL para crear la tabla en tu proyecto de Supabase.
  2. `settings.py`, `enums.py` y `models.py` (con soporte dinámico de variables).
  3. `csv_loader.py` y `supabase_repo.py`.

### Fase 2: Motor de Plantillas, Generador IA y Juez IA (Google Cloud / Gemini)
* **Objetivo:** Convertir una fila de Supabase en un correo personalizado y obtener el veredicto estructurado del Juez.
* **Entregables:**
  1. Archivos de configuración `generator_prompt.yaml`, `judge_rubric.yaml` y `email_base.html.j2`.
  2. `prompt_builder.py` y `gemini_client.py`.
  3. `generator_service.py` y `judge_service.py`.

### Fase 3: Integración Oficial con Gmail API (OAuth2 + MIME Builder)
* **Objetivo:** Autenticar tu cuenta de Gmail y probar el envío de un correo real y la creación de un borrador nativo en tu bandeja.
* **Entregables:**
  1. Guía rápida de activación de Gmail API y descarga de `client_secret.json` en tu consola de Google Cloud.
  2. `gmail_client.py` (manejo de refresco de token automático, codificación Base64 URL-safe y llamadas a `send` y `drafts.create`).

### Fase 4: Orquestación de Cola Asíncrona, Jitter y Estadísticas
* **Objetivo:** Unir el Productor (IA) y el Consumidor (Gmail) para que trabajen en paralelo y generen el reporte final.
* **Entregables:**
  1. `queue_worker.py` (gestión de la cola, reintentos ante caídas de red y pausas aleatorias).
  2. `stats_reporter.py` y `main.py`.

### Fase 5: Prueba End-to-End (Dry-Run con tus propios correos de prueba)
* **Objetivo:** Ejecutar el flujo completo con un CSV de 3-5 correos tuyos de prueba (forzando que unos pasen el Juez y otros fallen para ver cómo caen en Borradores).

---