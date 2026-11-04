import asyncio
from pathlib import Path
from uuid import UUID
from jinja2 import Environment, FileSystemLoader

from src.domain.enums import EmailStatus
from src.infrastructure.ai.gemini_client import GeminiClient
from src.infrastructure.database.supabase_repo import SupabaseRepository
from src.services.evaluation.judge_service import JudgeService
from src.services.generation.prompt_builder import PromptBuilder
from src.services.reporting.stats_reporter import ExecutionStats


class GeneratorService:
    def __init__(self) -> None:
        self.repo = SupabaseRepository()
        self.gemini_client = GeminiClient()
        self.prompt_builder = PromptBuilder()
        self.judge_service = JudgeService()

        self.jinja_env = Environment(
            loader=FileSystemLoader("templates/email"),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.html_template = self.jinja_env.get_template("email_base.html.j2")

    async def run_producer(
        self,
        finished_event: asyncio.Event,
        stats: ExecutionStats,
        limit: int = 50,
        sender_name: str = "José Tapia",
    ) -> None:
        print("[PRODUCTOR] Iniciando redacción y control de calidad (Juez IA)...")
        system_instruction = self.prompt_builder.build_system_instruction()

        while True:
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

                print(f"\n[PRODUCTOR] Redactando para: {recipient} ({prospect.get('full_name')})")

                try:
                    # 1. Redacción estructurada
                    user_prompt = self.prompt_builder.build_user_prompt(prospect)
                    result = await asyncio.to_thread(
                        self.gemini_client.generate_email,
                        system_instruction,
                        user_prompt,
                    )

                    # 2. Renderizado HTML
                    rendered_html = self.html_template.render(
                        body_paragraphs=result.body_paragraphs,
                        sender_name=sender_name,
                    )

                    # 3. Quality Gate (Juez IA)
                    print(f"[JUEZ IA] Evaluando calidad del copy...")
                    verdict = await asyncio.to_thread(
                        self.judge_service.evaluate,
                        prospect,
                        result.subject,
                        result.body_paragraphs,
                    )

                    new_status = EmailStatus.QUEUED_SEND if verdict.passed else EmailStatus.QUEUED_DRAFT

                    # 4. Persistencia del veredicto
                    await asyncio.to_thread(
                        self.repo.update_email_judged,
                        email_id,
                        new_status,
                        result.subject,
                        rendered_html,
                        verdict.score,
                        verdict.critique,
                    )

                    stats.emails_generated += 1
                    if verdict.passed:
                        stats.emails_approved += 1
                        print(f"[JUEZ-APROBADO] Score: {verdict.score}/100 -> Estado: QUEUED_SEND")
                    else:
                        stats.emails_rejected_by_judge += 1
                        print(f"[JUEZ-RECHAZADO] Score: {verdict.score}/100 -> Desviado a: QUEUED_DRAFT")
                        print(f"[JUEZ-MOTIVO] {verdict.critique}")

                except Exception as exc:
                    err_msg = f"Error generando email {email_id}: {exc}"
                    print(f"[PRODUCTOR-ERROR] {err_msg}")
                    await asyncio.to_thread(
                        self.repo.update_email_failed, email_id, str(exc)
                    )
                    stats.emails_failed += 1
                    stats.errors.append(err_msg)

        finished_event.set()
        print("\n[PRODUCTOR] Generación completada. Señal enviada al despachador.")