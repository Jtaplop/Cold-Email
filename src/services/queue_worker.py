import asyncio
import random
from uuid import UUID
from src.domain.enums import EmailStatus
from src.infrastructure.gmail_client import GmailClient
from src.infrastructure.supabase_repo import SupabaseRepository
from src.services.stats_reporter import ExecutionStats


class QueueWorker:
    def __init__(
        self,
        repo: SupabaseRepository,
        gmail_client: GmailClient,
        stats: ExecutionStats,
        mode: str = "draft",  # 'draft' o 'send'
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
        """
        Consumidor asíncrono que sondea correos GENERATED y los despacha.
        Finaliza cuando el productor termina Y no quedan correos en cola.
        """
        print(f"[WORKER] Consumidor iniciado en modo: {self.mode.upper()}")

        while True:
            # 1. Consultar si hay correos listos para despachar
            items = await asyncio.to_thread(
                self.repo.fetch_generated_emails_with_prospect, limit=5
            )

            if not items:
                # Si el productor ya terminó y la cola está vacía, el worker cierra
                if producer_finished.is_set():
                    print("[WORKER] No quedan correos pendientes de despacho. Finalizando consumidor.")
                    break
                # Esperar 2 segundos antes de volver a consultar la cola
                await asyncio.sleep(2)
                continue

            for item in items:
                email_id = UUID(item["id"])
                subject = item.get("subject") or "Sin asunto"
                body_html = item.get("body_html") or ""
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
                    if self.mode == "send":
                        print(f"[WORKER] Enviando correo a: {recipient}...")
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

                        # Jitter aleatorio para proteger entregabilidad
                        pause = random.uniform(self.min_jitter, self.max_jitter)
                        print(f"[JITTER] Esperando {pause:.1f}s antes del próximo envío...")
                        await asyncio.sleep(pause)

                    else:  # Modo 'draft'
                        print(f"[WORKER] Creando borrador para: {recipient}...")
                        draft_id = await asyncio.to_thread(
                            self.gmail.create_draft, recipient, subject, body_html
                        )
                        await asyncio.to_thread(
                            self.repo.update_email_dispatched,
                            email_id,
                            EmailStatus.DRAFTED,
                        )
                        self.stats.emails_drafted += 1
                        print(f"[WORKER-OK] Borrador creado (Draft ID: {draft_id})")
                        # Pequeña pausa técnica entre llamadas de API
                        await asyncio.sleep(0.5)

                except Exception as exc:
                    err_msg = f"Fallo al despachar email {email_id} a {recipient}: {exc}"
                    print(f"[WORKER-ERROR] {err_msg}")
                    await asyncio.to_thread(
                        self.repo.update_email_failed, email_id, str(exc)
                    )
                    self.stats.emails_failed += 1
                    self.stats.errors.append(err_msg)