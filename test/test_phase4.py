import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.services.judge_service import JudgeService

def run_phase4_test() -> None:
    print("--- INICIANDO TEST DE FASE 4: EVALUADOR / JUEZ IA ---")
    judge = JudgeService()

    prospect_ejemplo = {
        "full_name": "Marcos Pérez",
        "email": "marcos@fitnesspro.com",
        "niche": "Entrenador Online B2B",
        "comment": "Tiene reels virales pero ningún embudo estructurado para monetizarlos.",
    }

    # Caso A: Copy bueno, directo y sin clichés
    print("\n--- CASO 1: COPY ÓPTIMO (Debe Aprobar >= 80) ---")
    buen_asunto = "tus reels y la captación"
    buenos_parrafos = [
        "Marcos, vi el alcance que tienen tus reels hablando de recomposición corporal.",
        "Muchos entrenadores con tu volumen de visitas pierden leads diarios por depender de DMs manuales en lugar de un filtro automatizado.",
        "Diseñé una estructura simple de 3 pasos que convierte seguidores en llamadas agendadas sin invertir en pauta.",
        "¿Te cuadra que te pase un video de 90 segundos mostrándote cómo funciona?",
    ]

    veredicto_a = judge.evaluate(prospect_ejemplo, buen_asunto, buenos_parrafos)
    print(f"Puntuación: {veredicto_a.score}/100")
    print(f"Aprobado: {veredicto_a.passed}")
    print(f"Crítica: {veredicto_a.critique}")
    print(f"Reglas violadas: {veredicto_a.violated_rules}")

    # Caso B: Copy con clichés, corporativismo y llamada de 45 minutos
    print("\n--- CASO 2: COPY DEFECTUOSO (Debe Suspender < 80) ---")
    mal_asunto = "Oportunidad revolucionaria de sinergia comercial para ti"
    malos_parrafos = [
        "Estimado Marcos, espero que este email te encuentre bien y estés teniendo un excelente día en tu prestigiosa empresa.",
        "Me pongo en contacto contigo porque somos una agencia integral líder en el mercado que genera sinergias revolucionarias de alto impacto exponencial para marcas personales líderes.",
        "Nuestra tecnología patentada transformará holísticamente todos tus procesos comerciales para potenciar tus ventas de forma masiva y disruptiva.",
        "¿Tendrías 45 minutos esta semana para una llamada por Zoom donde te haga una demostración exhaustiva de todo nuestro portafolio de servicios?",
    ]

    veredicto_b = judge.evaluate(prospect_ejemplo, mal_asunto, malos_parrafos)
    print(f"Puntuación: {veredicto_b.score}/100")
    print(f"Aprobado: {veredicto_b.passed}")
    print(f"Crítica: {veredicto_b.critique}")
    print(f"Reglas violadas: {veredicto_b.violated_rules}")

if __name__ == "__main__":
    run_phase4_test()