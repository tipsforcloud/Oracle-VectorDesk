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
        "Eres un agente técnico experto de soporte y helpdesk para la empresa.\n"
        "Tu misión es resolver la consulta del usuario basándote ESTRICTAMENTE en la información proporcionada a continuación.\n"
        "Reglas:\n"
        "1. Si la respuesta está en el contexto, explica el paso a paso claro, conciso y ordenado.\n"
        "2. Si la respuesta no está clara en el contexto, indica amablemente que el caso debe ser atendido por soporte especializado.\n"
        "3. Mantén un tono formal, empático y directo. Responde en español.\n\n"
        f"Contexto disponible:\n{retrieved_context}\n\n"
        f"Pregunta del usuario: {user_query}\n\n"
        "Respuesta resolutiva:"
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
        response.raise_for_status()
        data = response.json()
        raw_text = data.get("response", "").strip()
        # Eliminar posibles bloques de razonamiento interno <think>...</think> si el modelo los emite
        clean_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
        return clean_text if clean_text else raw_text

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error conectando con el motor LLM en Ollama ({OLLAMA_URL}): {str(e)}")
