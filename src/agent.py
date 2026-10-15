"""
API REST y Orquestador del Agente de Soporte RAG
Expone endpoints de resolución de tickets con búsqueda vectorial en Oracle Database 26ai.
"""

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


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Valida el estado operativo de los componentes de la solución."""
    return HealthResponse(
        status="ok",
        database="Oracle Database 26ai AI Vector Search",
        embedding_model=f"{EMBEDDING_MODEL_NAME} (768 dims)",
        llm_model=OLLAMA_MODEL,
        dsn=DB_DSN
    )


@app.post("/api/v1/support/resolve", response_model=TicketResponse)
def resolve_ticket(payload: TicketRequest):
    """
    Recibe una consulta de soporte, genera su embedding, busca contexto en Oracle 26ai
    y sintetiza la solución con el modelo LLM local en CPU.
    """
    start_time = time.time()

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
            execution_time_ms=elapsed_ms
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
        llm_resolution = generate_support_resolution(payload.user_query, combined_context)
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
        execution_time_ms=elapsed_ms
    )
