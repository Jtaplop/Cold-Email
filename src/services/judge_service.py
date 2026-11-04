from pathlib import Path
import yaml
from src.domain.models import JudgeVerdictSchema
from src.infrastructure.gemini_client import GeminiClient


class JudgeService:
    def __init__(self, rubric_path: Path = Path("templates/judge_rubric.yaml")) -> None:
        if not rubric_path.exists():
            raise FileNotFoundError(f"No existe el archivo de rúbrica: {rubric_path}")

        with open(rubric_path, mode="r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

        self.gemini_client = GeminiClient()
        self.passing_score = self.config.get("scoring", {}).get("passing_score", 80)

    def evaluate(self, prospect: dict, subject: str, body_paragraphs: list[str]) -> JudgeVerdictSchema:
        full_body = "\n\n".join(body_paragraphs)
        word_count = len(full_body.split())

        system_instruction = self.config.get("system_instruction", "").strip()
        rules = "\n".join(f"- {r}" for r in self.config.get("rules", {}).get("critical_violations", []))

        prompt = f"""
EVALÚA EL SIGUIENTE EMAIL EN FRÍO:

CONTEXTO DEL PROSPECTO:
- Destinatario: {prospect.get('full_name')} ({prospect.get('email')})
- Nicho: {prospect.get('niche')}
- Observaciones previas: {prospect.get('comment')}

EMAIL A AUDITAR:
- Asunto: {subject}
- Conteo de palabras aproximado: {word_count}
- Cuerpo:
{full_body}

REGLAS CRÍTICAS A VERIFICAR:
{rules}

INSTRUCCIÓN:
Asigna un score entre 0 y 100. Si el score es mayor o igual a {self.passing_score} y no viola ninguna regla crítica, passed es True. Si incumple reglas o el tono es artificial/spam, passed es False.
"""
        return self.gemini_client.evaluate_email(system_instruction, prompt.strip())