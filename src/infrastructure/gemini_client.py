from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from src.config.settings import settings


class GeneratedEmailSchema(BaseModel):
    subject: str = Field(description="Asunto del correo, corto, directo y sin mayúsculas invasivas.")
    body_paragraphs: list[str] = Field(
        description="Lista ordenada de párrafos que componen el cuerpo del correo (de 2 a 4 párrafos)."
    )


class GeminiClient:
    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise ValueError("Falta GEMINI_API_KEY en la configuración (.env)")
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def generate_email(self, system_instruction: str, user_prompt: str) -> GeneratedEmailSchema:
        """
        Invoca Gemini forzando el retorno estricto de GeneratedEmailSchema.
        """
        response = self.client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=GeneratedEmailSchema,
                temperature=0.7,
            ),
        )

        if not response.parsed:
            raise RuntimeError("Gemini no retornó un esquema estructurado válido.")

        return response.parsed
    
    def evaluate_email(self, system_instruction: str, evaluation_prompt: str) -> "JudgeVerdictSchema":
        """Evalúa un correo generado contra la rúbrica de calidad usando salidas estructuradas."""
        from src.domain.models import JudgeVerdictSchema

        response = self.client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=evaluation_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=JudgeVerdictSchema,
                temperature=0.1,  # Temperatura baja para consistencia y rigor en la evaluación
            ),
        )

        if not response.parsed:
            raise RuntimeError("El modelo no retornó un veredicto estructurado válido.")

        return response.parsed