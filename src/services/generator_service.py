import asyncio
from pathlib import Path
from uuid import UUID
from jinja2 import Environment, FileSystemLoader
from src.infrastructure.gemini_client import GeminiClient
from src.infrastructure.supabase_repo import SupabaseRepository
from src.services.prompt_builder import PromptBuilder


class GeneratorService:
    def __init__(self) -> None:
        self.repo = SupabaseRepository()
        self.gemini_client = GeminiClient()
        self.prompt_builder = PromptBuilder()

        # Configuración de Jinja2 para cargar plantillas HTML
        self.jinja_env = Environment(
            loader=FileSystemLoader("templates"),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.html_template = self.jinja_env.get_template("email_base.html.j2")

    def process_pending_emails(self, limit: int = 10, sender_name: str = "José Tapia") -> int:
        """
        Recupera correos PENDING, los redacta con Gemini, renderiza su HTML y los actualiza en Supabase.
        Retorna la cantidad de correos generados exitosamente.
        """
        pending_items = self.repo.fetch_pending_emails_with_prospect(limit=limit)
        if not pending_items:
            print("[INFO] No hay correos PENDING en la cola.")
            return 0

        success_count = 0
        system_instruction = self.prompt_builder.build_system_instruction()

        for item in pending_items:
            email_id = UUID(item["id"])
            prospect = item.get("prospects") or {}
            destinatario = prospect.get("email", "Desconocido")

            print(f"\n[GENERANDO] Correo para: {destinatario} ({prospect.get('full_name')})")

            try:
                # 1. Construir prompt
                user_prompt = self.prompt_builder.build_user_prompt(prospect)

                # 2. Llamada estructurada a Gemini
                result = self.gemini_client.generate_email(
                    system_instruction=system_instruction,
                    user_prompt=user_prompt,
                )

                # 3. Renderizar HTML final con Jinja2
                rendered_html = self.html_template.render(
                    body_paragraphs=result.body_paragraphs,
                    sender_name=sender_name,
                )

                # 4. Actualizar en Supabase a GENERATED
                self.repo.update_email_generated(
                    email_id=email_id,
                    subject=result.subject,
                    body_html=rendered_html,
                )

                print(f"[OK] Asunto: {result.subject}")
                print(f"[OK] Párrafos generados: {len(result.body_paragraphs)}")
                success_count += 1

            except Exception as exc:
                error_msg = f"Fallo al generar email {email_id}: {str(exc)}"
                print(f"[ERROR] {error_msg}")
                self.repo.update_email_failed(email_id=email_id, error_message=str(exc))

        return success_count

    async def run_producer(
        self,
        finished_event: asyncio.Event,
        stats: "ExecutionStats",
        limit: int = 50,
        sender_name: str = "José Tapia",
    ) -> None:
        """
        Corrutina productora: busca correos PENDING, los redacta con Gemini y los pasa a GENERATED.
        Al vaciar la cola, activa el finished_event.
        """
        import asyncio

        print("[PRODUCTOR] Iniciando generación de correos pendientes...")
        system_instruction = self.prompt_builder.build_system_instruction()

        while True:
            # Buscar lote de pendientes de forma asíncrona
            pending_items = await asyncio.to_thread(
                self.repo.fetch_pending_emails_with_prospect, limit=limit
            )

            if not pending_items:
                print("[PRODUCTOR] No hay más correos PENDING en Supabase.")
                break

            for item in pending_items:
                email_id = UUID(item["id"])
                prospect = item.get("prospects") or {}
                recipient = prospect.get("email", "Desconocido")

                print(f"[PRODUCTOR] Redactando para: {recipient} ({prospect.get('full_name')})")

                try:
                    user_prompt = self.prompt_builder.build_user_prompt(prospect)

                    # Inferencia de Gemini
                    result = await asyncio.to_thread(
                        self.gemini_client.generate_email,
                        system_instruction,
                        user_prompt,
                    )

                    # Renderizado Jinja2
                    rendered_html = self.html_template.render(
                        body_paragraphs=result.body_paragraphs,
                        sender_name=sender_name,
                    )

                    # Actualizar estado a GENERATED en Supabase
                    await asyncio.to_thread(
                        self.repo.update_email_generated,
                        email_id,
                        result.subject,
                        rendered_html,
                    )

                    stats.emails_generated += 1
                    print(f"[PRODUCTOR-OK] Generado: '{result.subject}' -> Guardado como GENERATED")

                except Exception as exc:
                    err_msg = f"Error generando email {email_id}: {exc}"
                    print(f"[PRODUCTOR-ERROR] {err_msg}")
                    await asyncio.to_thread(
                        self.repo.update_email_failed, email_id, str(exc)
                    )
                    stats.emails_failed += 1
                    stats.errors.append(err_msg)

        # Señalizar al worker de que el productor terminó de procesar los PENDING
        finished_event.set()
        print("[PRODUCTOR] Generación completada. Señal enviada al consumidor.")