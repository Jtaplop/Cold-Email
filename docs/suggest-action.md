Actúa como un Ingeniero de Software Senior especializado en Clean Architecture y refactorización en Python.

### OBJETIVO
Reorganizar la estructura de carpetas y módulos del proyecto "Cold-Email" para eliminar el desorden visual y desacoplar adaptadores y servicios, **SIN modificar la lógica de negocio ni alterar el funcionamiento interno del código existente**. Tu única tarea técnica es reubicar archivos, actualizar las rutas de importación (`import ... from ...`), ajustar las rutas por defecto hacia plantillas en `Path(...)` y verificar que el sistema siga ejecutándose exactamente igual.

---

### ÁRBOL DE DESTINO OBLIGATORIO
Debes mover los archivos existentes para que queden distribuidos exactamente en este esquema:

Cold-Email/
├── credentials/
├── data/
│   ├── inbox_csv/
│   └── processed_csv/
├── templates/
│   ├── email/
│   │   └── email_base.html.j2
│   └── prompts/
│       ├── generator_prompt.yaml
│       └── judge_rubric.yaml
├── tests/
│   ├── __init__.py
│   ├── test_phase1.py
│   ├── test_phase2.py
│   ├── test_phase3.py
│   └── test_phase4.py
└── src/
    ├── __init__.py
    ├── main.py
    ├── config/
    │   ├── __init__.py
    │   └── settings.py
    ├── domain/
    │   ├── __init__.py
    │   ├── enums.py
    │   └── models.py
    ├── infrastructure/
    │   ├── __init__.py
    │   ├── ai/
    │   │   ├── __init__.py
    │   │   └── gemini_client.py
    │   ├── database/
    │   │   ├── __init__.py
    │   │   └── supabase_repo.py
    │   ├── email/
    │   │   ├── __init__.py
    │   │   └── gmail_client.py
    │   └── files/
    │       ├── __init__.py
    │       └── csv_loader.py
    └── services/
        ├── __init__.py
        ├── generation/
        │   ├── __init__.py
        │   ├── generator_service.py
        │   └── prompt_builder.py
        ├── evaluation/
        │   ├── __init__.py
        │   └── judge_service.py
        ├── dispatch/
        │   ├── __init__.py
        │   └── queue_worker.py
        └── reporting/
            ├── __init__.py
            └── stats_reporter.py

---

### REGLAS ESTRICTAS DE REFACTORIZACIÓN
1. **No toques la lógica algorítmica**: No cambies firmas de métodos, ni nombres de funciones, ni modelos Pydantic, ni llamadas asíncronas (`asyncio`), ni queries de Supabase, ni llamadas a Gemini.
2. **Actualización quirúrgica de Imports**:
   - `gemini_client.py` pasa a `src.infrastructure.ai.gemini_client`
   - `supabase_repo.py` pasa a `src.infrastructure.database.supabase_repo`
   - `gmail_client.py` pasa a `src.infrastructure.email.gmail_client`
   - `csv_loader.py` pasa a `src.infrastructure.files.csv_loader`
   - `generator_service.py` pasa a `src.services.generation.generator_service`
   - `prompt_builder.py` pasa a `src.services.generation.prompt_builder`
   - `judge_service.py` pasa a `src.services.evaluation.judge_service`
   - `queue_worker.py` pasa a `src.services.dispatch.queue_worker`
   - `stats_reporter.py` pasa a `src.services.reporting.stats_reporter`
3. **Actualización de rutas de plantillas en código**:
   - En `PromptBuilder.__init__`: la ruta por defecto cambia a `Path("templates/prompts/generator_prompt.yaml")`.
   - En `JudgeService.__init__`: la ruta por defecto cambia a `Path("templates/prompts/judge_rubric.yaml")`.
   - En `GeneratorService.__init__`: configurar el loader de Jinja2 apuntando a `templates/email` y cargar `email_base.html.j2` (o mantener `loader=FileSystemLoader("templates")` y cargar `email/email_base.html.j2`).
4. **Archivos `__init__.py`**: Garantiza que cada subcarpeta dentro de `src/` contenga su respectivo `__init__.py` vacío para que Python resuelva los submódulos sin errores de namespace.
5. **Ajuste en tests**:
   - Los archivos de prueba (`test_phase1.py` a `test_phase4.py`) deben moverse dentro de `tests/`. En la cabecera de cada uno, asegúrate de que agreguen la raíz del proyecto al `sys.path` (`sys.path.insert(0, str(Path(__file__).resolve().parent.parent))`) para que puedan ejecutarse directamente con `uv run tests/test_phaseX.py`.

---

### QUÉ DEBES ENTREGARME
1. **Comandos de PowerShell (Windows)** para crear las carpetas nuevas y mover los archivos existentes de forma automática sin hacerlo a mano.
2. **Código completo de cada archivo modificado**:
   - Archivos de servicios que cambiaron sus rutas de plantillas o imports (`generator_service.py`, `judge_service.py`, `prompt_builder.py`, `queue_worker.py`).
   - El orquestador `src/main.py` con las nuevas rutas de importación.
   - Los scripts dentro de `tests/` con sus imports actualizados.
3. El comando exacto para verificar que el pipeline corre intacto tras los movimientos.