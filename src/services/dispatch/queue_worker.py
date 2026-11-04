import asyncio
import random
from uuid import UUID
from src.domain.enums import EmailStatus
from src.infrastructure.email.gmail_client import GmailClient
from src.infrastructure.database.supabase_repo import SupabaseRepository
from src.services.reporting.stats_reporter import ExecutionStats


class QueueWorker:
    def __init__(
        self,
        repo: SupabaseRepository,
        gmail_client: GmailClient,
        stats: ExecutionStats,
        mode: str = "draft",
        min_jitter: int = 45,
        max_jitter: int = 110,
    ) -> None:
        self.repo = repo
        self.gmail = gmail_client
        self.stats = stats
        self.mode = mode
        self.min_jitter = min_jitter
        self.max_jitter = max_jitter

    async def run(self, producer_finished: asyncio.Event) -> None:
        print(f"[WORKER] Consumidor activo en modo: {self.mode.upper()}")
        target_statuses = (
            [EmailStatus.QUEUED_SEND.value, EmailStatus.QUEUED_DRAFT.value, EmailStatus.GENERATED.value]
            if self.mode == "send"
            else [EmailStatus.QUEUED_DRAFT.value, EmailStatus.QUEUED_SEND.value, EmailStatus.GENERATED.value]
        )

        while True:
            items = await asyncio.to_thread(
                self.repo.fetch_queued_emails_with_prospect,
                statuses=target_statuses,
                limit=5,
            )

            if not items:
                if producer_finished.is_set():
                    print("[WORKER] Cola de despacho vacía y productor finalizado.")
                    break
                await asyncio.sleep(2)
                continue

            for item in items:
                email_id = UUID(item["id"])
                subject = item.get("subject") or "Sin asunto"
                body_html = item.get("body_html") or ""
                status_item = item.get("status")
                prospect = item.get("prospects") or {}
                recipient = prospect.get("email")

                if not recipient:
                    await asyncio.to_thread(
                        self.repo.update_email_failed,
                        email_id,
                        "El prospecto carece de dirección de correo válida.",
                    )
                    self.stats.emails_failed += 1
                    continue

                try:
                    # En modo send, solo se envía en vivo si fue aprobado expresamente
                    if self.mode == "send" and status_item == EmailStatus.QUEUED_SEND.value:
                        print(f"[WORKER] Enviando email en vivo a: {recipient}...")
                        msg_id = await asyncio.to_thread(
                            self.gmail.send_message, recipient, subject, body_html
                        )
                        await asyncio.to_thread(
                            self.repo.update_email_dispatched,
                            email_id,
                            EmailStatus.SENT,
                        )
                        self.stats.emails_sent += 1
                        print(f"[WORKER-OK] Enviado con éxito (Message ID: {msg_id})")

                        pause = random.uniform(self.min_jitter, self.max_jitter)
                        print(f"[JITTER] Pausa de {pause:.1f}s antes del próximo envío...")
                        await asyncio.sleep(pause)

                    else:
                        # Si es modo draft o si fue reprobado por el Juez en modo send
                        draft_label = " [REVISIÓN REQUERIDA]" if status_item == EmailStatus.QUEUED_DRAFT.value and self.mode == "send" else ""
                        actual_subject = f"{subject}{draft_label}"

                        print(f"[WORKER] Creando borrador para: {recipient}...")
                        draft_id = await asyncio.to_thread(
                            self.gmail.create_draft, recipient, actual_subject, body_html
                        )
                        await asyncio.to_thread(
                            self.repo.update_email_dispatched,
                            email_id,
                            EmailStatus.DRAFTED,
                        )
                        self.stats.emails_drafted += 1
                        print(f"[WORKER-OK] Borrador creado (Draft ID: {draft_id})")
                        await asyncio.sleep(0.5)

                except Exception as exc:
                    err_msg = f"Fallo al despachar email {email_id} a {recipient}: {exc}"
                    print(f"[WORKER-ERROR] {err_msg}")
                    await asyncio.to_thread(
                        self.repo.update_email_failed, email_id, str(exc)
                    )
                    self.stats.emails_failed += 1
                    self.stats.errors.append(err_msg)