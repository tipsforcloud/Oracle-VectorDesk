"""
Cliente del Motor LLM en CPU (Ollama)
Gestiona la inferencia local con Qwen 2.5 7B sobre procesadores AMD EPYC en OCI Compute.
"""

import re
import requests
from typing import Optional
from src.config import OLLAMA_URL, OLLAMA_MODEL


def generate_support_resolution(user_query: str, retrieved_context: str) -> str:
    """
    Envía el prompt al modelo LLM local a través de la API REST de Ollama.
    Garantiza que la respuesta se fundamente estrictamente en el contexto recuperado.
    """
    system_prompt = (
        "Eres un agente técnico de soporte y helpdesk corporativo amable, empático y experto.\n"
        "Tu misión es resolver la consulta del usuario basándote ESTRICTAMENTE en la información proporcionada a continuación.\n\n"
        "Pautas de comunicación y estilo:\n"
        "1. Saluda al usuario de manera cordial y empática (ej: '¡Hola! Con gusto te ayudo con esta gestión') antes de dar la solución.\n"
        "2. Explica el procedimiento de forma natural, amena y estructurada paso a paso, utilizando viñetas cuando aplique.\n"
        "3. Sé preciso y riguroso con los datos técnicos (números de teléfono, PINs, extensiones, comandos, políticas), tomándolos únicamente del contexto. No inventes información ausente.\n"
        "4. Si la información no está en el contexto, explica con amabilidad que no se dispone de ese dato y sugiere escalar el ticket.\n"
        "5. Despídete cordialmente ofreciendo apoyo si surgen más dudas.\n\n"
        f"Contexto disponible:\n{retrieved_context}\n\n"
        f"Pregunta del usuario: {user_query}\n\n"
        "Respuesta:"
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": system_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "num_ctx": 4096
                }
            },
            timeout=90
        )
        if response.status_code == 404:
            err_msg = ""
            try:
                err_msg = response.json().get("error", "")
            except Exception:
                pass
            raise RuntimeError(
                f"El modelo '{OLLAMA_MODEL}' no está instalado en Ollama. "
                f"Descárgalo ejecutando en la terminal: 'ollama pull {OLLAMA_MODEL}'. "
                f"Detalle: {err_msg or 'Model not found'}"
            )
        data = response.json()
        raw_text = data.get("response", "").strip()
        # Eliminar posibles bloques de razonamiento interno <think>...</think> si el modelo los emite
        clean_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
        final_text = clean_text if clean_text else raw_text

        # Extraer métricas de telemetría de Ollama
        eval_count = data.get("eval_count", 0)
        eval_duration_ns = data.get("eval_duration", 0)
        eval_seconds = eval_duration_ns / 1e9 if eval_duration_ns > 0 else 0.0
        tokens_per_second = round(eval_count / eval_seconds, 2) if eval_seconds > 0 else 0.0

        metrics = {
            "tokens_generated": eval_count,
            "tokens_per_second": tokens_per_second,
            "eval_duration_ms": int(eval_duration_ns / 1e6) if eval_duration_ns > 0 else 0
        }
        return final_text, metrics

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"No se pudo conectar con Ollama en {OLLAMA_URL} (Connection refused). "
            "El servicio no está en ejecución. Inícialo con: 'sudo systemctl start ollama' "
            f"y asegúrate de tener el modelo descargado con: 'ollama pull {OLLAMA_MODEL}'."
        )
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error comunicando con el motor LLM en Ollama ({OLLAMA_URL}): {str(e)}")
