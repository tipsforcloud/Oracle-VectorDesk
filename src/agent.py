"""
API REST y Orquestador del Agente de Soporte RAG
Expone endpoints de resolución de tickets con búsqueda vectorial en Oracle Database 26ai.
"""

import re
import time
from fastapi import FastAPI, HTTPException
from src.config import DB_DSN, OLLAMA_MODEL, EMBEDDING_MODEL_NAME, SIMILARITY_THRESHOLD
from src.models import TicketRequest, TicketResponse, HealthResponse, SourceItem
from src.embeddings import get_query_embedding
from src.database import search_vector_knowledge_base, log_ticket_resolution
from src.llm import generate_support_resolution

app = FastAPI(
    title="Oracle-VectorDesk API",
    description="Agente de Soporte RAG con Oracle Database 26ai e Inferencia en CPU",
    version="2.0.0"
)


def is_pure_greeting(query: str) -> bool:
    """Detecta si la consulta del usuario es un saludo o cortesía conversacional."""
    clean = re.sub(r"[^\w\s]", "", query.lower()).strip()
    if not clean:
        return False

    greetings = {
        "hola", "buenas", "buenos dias", "buenos días", "buenas tardes",
        "buenas noches", "saludos", "que tal", "qué tal", "como estas",
        "cómo estás", "como te va", "cómo te va", "hey", "hello", "hi",
        "hola como estas", "hola cómo estás", "hola que tal", "hola qué tal",
        "hola buenos dias", "hola buenos días", "hola buenas tardes",
        "hola buenas noches", "buen dia", "buen día"
    }
    if clean in greetings:
        return True

    words = clean.split()
    if len(words) <= 4:
        starts_greeting = words[0] in ["hola", "buenas", "saludos", "hey", "hello", "hi"] or (
            len(words) >= 2 and words[0] == "buen" and words[1] in ["dia", "día"]
        )
        technical_keywords = [
            "error", "fallo", "problema", "pin", "telefono", "teléfono", "vpn",
            "sap", "pass", "contraseña", "ticket", "ayuda", "acceso", "soporte",
            "como", "cómo", "solicitar", "solicitud", "bloqueo", "desbloqueo"
        ]
        if starts_greeting and not any(kw in clean for kw in technical_keywords):
            return True

    return False


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Valida el estado operativo de los componentes de la solución."""
    ollama_ok = False
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=1)
        ollama_ok = (r.status_code == 200)
    except Exception:
        pass

    return HealthResponse(
        status="ok" if ollama_ok else "warning_ollama_offline",
        database="Oracle Database 26ai AI Vector Search",
        embedding_model=f"{EMBEDDING_MODEL_NAME} (768 dims)",
        llm_model=f"{OLLAMA_MODEL} ({'online' if ollama_ok else 'offline: servicio inactivo en :11434'})",
        dsn=DB_DSN
    )


@app.post("/api/v1/support/resolve", response_model=TicketResponse)
def resolve_ticket(payload: TicketRequest):
    """
    Recibe una consulta de soporte, genera su embedding, busca contexto en Oracle 26ai
    y sintetiza la solución con el modelo LLM local en CPU.
    """
    start_time = time.time()

    # 0. Detección de Saludos y Cortesía Conversacional (Small-Talk)
    if is_pure_greeting(payload.user_query):
        elapsed_ms = int((time.time() - start_time) * 1000)
        greeting_msg = (
            "¡Hola! 👋 Qué gusto saludarte. Soy tu asistente inteligente de soporte técnico y helpdesk corporativo, "
            "impulsado por Oracle Database 26ai. Estoy aquí para guiarte paso a paso con incidencias, accesos, "
            "procedimientos de TI y políticas de la empresa. ¿En qué te puedo colaborar el día de hoy?"
        )
        log_ticket_resolution(
            ticket_id=payload.ticket_id,
            user_query=payload.user_query,
            retrieved_context="Interacción de saludo y bienvenida.",
            agent_response=greeting_msg,
            confidence_score=1.0,
            status="greeting_chitchat",
            execution_time_ms=elapsed_ms
        )
        return TicketResponse(
            ticket_id=payload.ticket_id,
            user_query=payload.user_query,
            suggested_resolution=greeting_msg,
            confidence_score=1.0,
            sources=[],
            execution_time_ms=elapsed_ms,
            tokens_generated=0,
            tokens_per_second=0.0
        )

    # 1. Vectorizar la consulta en CPU
    try:
        query_vector = get_query_embedding(payload.user_query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando embedding de consulta: {str(e)}")

    # 2. Búsqueda vectorial nativa en Oracle Database 26ai
    try:
        db_results = search_vector_knowledge_base(query_vector, top_k=3)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando Oracle Database 26ai: {str(e)}")

    # 3. Validar umbral de corte semántico (Anti-Alucinación)
    top_score = db_results[0]["similarity"] if db_results else 0.0
    if not db_results or top_score < SIMILARITY_THRESHOLD:
        elapsed_ms = int((time.time() - start_time) * 1000)
        fallback_msg = (
            "No se encontró documentación suficiente en la base de conocimiento para resolver este ticket automáticamente. "
            "Se escala a un agente humano de soporte."
        )
        # Auditoría del escalamiento
        log_ticket_resolution(
            ticket_id=payload.ticket_id,
            user_query=payload.user_query,
            retrieved_context="",
            agent_response=fallback_msg,
            confidence_score=top_score,
            status="escalated_to_human",
            execution_time_ms=elapsed_ms
        )
        return TicketResponse(
            ticket_id=payload.ticket_id,
            user_query=payload.user_query,
            suggested_resolution=fallback_msg,
            confidence_score=round(top_score, 4),
            sources=[],
            execution_time_ms=elapsed_ms,
            tokens_generated=0,
            tokens_per_second=0.0
        )

    # 4. Ensamblar contexto recuperado
    context_chunks = []
    sources = []
    for row in db_results:
        context_chunks.append(f"[{row['title']} - {row['category']}]:\n{row['content']}")
        sources.append(SourceItem(
            id=row["id"],
            title=row["title"],
            similarity=round(float(row["similarity"]), 4)
        ))
    combined_context = "\n\n---\n\n".join(context_chunks)

    # 5. Generar resolución con LLM en CPU (Ollama)
    try:
        llm_resolution, llm_metrics = generate_support_resolution(payload.user_query, combined_context)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    elapsed_ms = int((time.time() - start_time) * 1000)

    # 6. Registrar auditoría y métricas en Oracle Database 26ai
    log_ticket_resolution(
        ticket_id=payload.ticket_id,
        user_query=payload.user_query,
        retrieved_context=combined_context,
        agent_response=llm_resolution,
        confidence_score=top_score,
        status="auto_resolved" if top_score > 0.65 else "draft_review",
        execution_time_ms=elapsed_ms
    )

    return TicketResponse(
        ticket_id=payload.ticket_id,
        user_query=payload.user_query,
        suggested_resolution=llm_resolution,
        confidence_score=round(top_score, 4),
        sources=sources,
        execution_time_ms=elapsed_ms,
        tokens_generated=llm_metrics.get("tokens_generated"),
        tokens_per_second=llm_metrics.get("tokens_per_second")
    )
