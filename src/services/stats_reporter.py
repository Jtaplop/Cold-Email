import time
from dataclasses import dataclass, field


@dataclass
class ExecutionStats:
    start_time: float = field(default_factory=time.time)
    csv_leads_found: int = 0
    csv_leads_ingested: int = 0
    csv_leads_skipped: int = 0
    emails_generated: int = 0
    emails_approved: int = 0
    emails_rejected_by_judge: int = 0
    emails_drafted: int = 0
    emails_sent: int = 0
    emails_failed: int = 0
    errors: list[str] = field(default_factory=list)

    def print_summary(self) -> None:
        elapsed = time.time() - self.start_time
        minutes, seconds = divmod(elapsed, 60)

        print("\n" + "=" * 58)
        print("           RESUMEN DE EJECUCIÓN DEL PIPELINE")
        print("=" * 58)
        print(f" Tiempo total:                 {int(minutes)}m {seconds:.1f}s")
        print(f" Prospectos en CSV:            {self.csv_leads_found}")
        print(f" Ingestados / Actualizados:    {self.csv_leads_ingested}")
        print(f" Omitidos (sin email):         {self.csv_leads_skipped}")
        print("-" * 58)
        print(f" Correos redactados con IA:    {self.emails_generated}")
        print(f"  * Aprobados por Juez:        {self.emails_approved}")
        print(f"  * Desviados por Juez:        {self.emails_rejected_by_judge}")
        print("-" * 58)
        print(f" Borradores creados en Gmail:  {self.emails_drafted}")
        print(f" Correos enviados en vivo:     {self.emails_sent}")
        print(f" Errores / Fallidos:           {self.emails_failed}")

        if self.errors:
            print("-" * 58)
            print(" DETALLE DE ERRORES:")
            for err in self.errors[:5]:
                print(f"  * {err}")
            if len(self.errors) > 5:
                print(f"  * ... y {len(self.errors) - 5} errores más.")

        print("=" * 58 + "\n")