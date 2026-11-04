from pathlib import Path
import yaml


class PromptBuilder:
    def __init__(self, prompt_yaml_path: Path = Path("templates/prompts/generator_prompt.yaml")) -> None:
        if not prompt_yaml_path.exists():
            raise FileNotFoundError(f"No existe el archivo de prompt: {prompt_yaml_path}")
        
        with open(prompt_yaml_path, mode="r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)

    def build_system_instruction(self) -> str:
        return self.config.get("system_instruction", "").strip()

    def build_user_prompt(self, prospect_data: dict) -> str:
        full_name = prospect_data.get("full_name") or "colega"
        ig_username = prospect_data.get("ig_username") or "no especificado"
        niche = prospect_data.get("niche") or "su sector comercial"
        comment = prospect_data.get("comment") or "Sin observaciones adicionales"
        language = prospect_data.get("language") or "es"

        framework = self.config.get("framework", {})
        constraints = "\n".join(f"- {c}" for c in self.config.get("constraints", []))

        prompt = f"""
Redacta un correo personalizado para el siguiente prospecto respetando estrictamente el esquema y las reglas.

DATOS DEL DESTINATARIO:
- Nombre: {full_name}
- Usuario Instagram: {ig_username}
- Nicho / Industria: {niche}
- Contexto / Observaciones clave: {comment}
- Idioma de redacción: {language}

ESTRUCTURA DEL MENSAJE:
1. Hook: {framework.get('hook', '')}
2. Dolor / Oportunidad: {framework.get('pain_or_opportunity', '')}
3. Propuesta sutil: {framework.get('solution_hint', '')}
4. CTA: {framework.get('call_to_action', '')}

REGLAS OBLIGATORIAS:
{constraints}
- IMPORTANTE: Responde enteramente en el idioma del destinatario ({language}).
"""
        return prompt.strip()