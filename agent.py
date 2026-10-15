"""
Backend del Agente de Soporte RAG (Low-Cost)
Arquitectura: OCI Compute (CPU-only con Ollama) + Oracle Database 23ai / 26ai (AI Vector Search nativo)
"""

import os
import time
import array
import requests
import oracledb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Configuración por variables de entorno
DB_USER = os.getenv("DB_USER", "app_support")
DB_PASSWORD = os.getenv("DB_PASSWORD", "CambiarPorTuPassword123!")
DB_DSN = os.getenv("DB_DSN", "localhost:1521/PDBLAB1")
WALLET_DIR = os.getenv("WALLET_DIR", None)
WALLET_PASSWORD = os.getenv("WALLET_PASSWORD", None)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")

app = FastAPI(title="OCI Low-Cost Support Agent API (Oracle Database 26ai)", version="2.0.0")

# Carga del modelo de embeddings en memoria RAM (768 dimensiones, alta precisión)
print("Cargando modelo de embeddings de alta precisión (768 dimensiones) en CPU...")
embed_model = SentenceTransformer("intfloat/multilingual-e5-base")
print("Modelo de embeddings listo.")


def get_db_connection():
    if WALLET_DIR:
        return oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN,
            wallet_location=WALLET_DIR,
            wallet_password=WALLET_PASSWORD
        )
    return oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN
    )


class TicketRequest(BaseModel):
    ticket_id: Optional[str] = "TICK-SAMPLE"
    user_query: str
    category: Optional[str] = None


class TicketResponse(BaseModel):
    ticket_id: Optional[str]
    user_query: str
    suggested_resolution: str
    confidence_score: float
    sources: List[dict]
    execution_time_ms: int


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "database": "Oracle Database 26ai AI Vector Search",
        "embedding_model": "intfloat/multilingual-e5-base (768 dims)",
        "llm_model": OLLAMA_MODEL,
        "db_dsn": DB_DSN
    }


@app.post("/api/v1/support/resolve", response_model=TicketResponse)
def resolve_ticket(payload: TicketRequest):
    start_time = time.time()
    
    # 1. Generar embedding vectorial con prefijo 'query: ' (768 floats normalizados)
    query_text = f"query: {payload.user_query}"
    query_vector = embed_model.encode(query_text, normalize_embeddings=True).tolist()
    query_vector_data = array.array("f", query_vector)
    
    # 2. Búsqueda vectorial nativa con VECTOR_DISTANCE en Oracle Database 26ai
    conn = None
    results = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            query_sql = """
                SELECT id, title, category, TO_CHAR(content) AS content_str,
                       (1 - VECTOR_DISTANCE(embedding, :query_vec, COSINE)) AS similarity
                FROM knowledge_base
                ORDER BY VECTOR_DISTANCE(embedding, :query_vec, COSINE) ASC
                FETCH FIRST 3 ROWS ONLY
            """
            cur.execute(query_sql, {"query_vec": query_vector_data})
            for row in cur.fetchall():
                results.append({
                    "id": row[0],
                    "title": row[1],
                    "category": row[2],
                    "content": row[3],
                    "similarity": float(row[4]) if row[4] is not None else 0.0
                })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error consultando Oracle Database 26ai: {str(e)}")
    finally:
        if conn:
            conn.close()

    # Si no hay suficiente similitud semántica, escalar a humano
    if not results or results[0]["similarity"] < 0.35:
        return TicketResponse(
            ticket_id=payload.ticket_id,
            user_query=payload.user_query,
            suggested_resolution="No se encontró documentación suficiente en la base de conocimiento para resolver este ticket automáticamente. Se escala a un agente humano.",
            confidence_score=results[0]["similarity"] if results else 0.0,
            sources=[],
            execution_time_ms=int((time.time() - start_time) * 1000)
        )

    # 3. Ensamblar contexto documental
    context_chunks = []
    sources = []
    for row in results:
        context_chunks.append(f"[{row['title']} - {row['category']}]:\n{row['content']}")
        sources.append({"id": row["id"], "title": row["title"], "similarity": round(float(row["similarity"]), 4)})
        
    combined_context = "\n\n---\n\n".join(context_chunks)
    
    # 4. Prompt para el LLM en Ollama
    system_prompt = (
        "Eres un agente técnico experto de soporte y helpdesk para la empresa. "
        "Tu misión es resolver la consulta del usuario basándote ESTRICTAMENTE en la información proporcionada a continuación.\n"
        "Reglas:\n"
        "1. Si la respuesta está en el contexto, explica el paso a paso claro y conciso.\n"
        "2. Si la respuesta no está clara en el contexto, indica amablemente que el caso debe ser atendido por soporte especializado.\n"
        "3. Mantén un tono formal, empático y directo. Responde en español.\n\n"
        f"Contexto disponible:\n{combined_context}\n\n"
        f"Pregunta del usuario: {payload.user_query}\n\n"
        "Respuesta resolutiva:"
    )

    # 5. Inferencia local con LLM en CPU (Ollama)
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
            timeout=60
        )
        response.raise_for_status()
        llm_output = response.json().get("response", "").strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error comunicando con Ollama en CPU: {str(e)}")

    elapsed_ms = int((time.time() - start_time) * 1000)

    # 6. Registrar métrica y auditoría en Oracle DB
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO agent_tickets_log 
                (ticket_external_id, user_query, retrieved_context, agent_response, confidence_score, status, execution_time_ms)
                VALUES (:ticket_id, :user_query, :context, :response, :score, :status, :exec_time)
            """, {
                "ticket_id": payload.ticket_id,
                "user_query": payload.user_query,
                "context": combined_context,
                "response": llm_output,
                "score": float(results[0]["similarity"]),
                "status": "auto_resolved" if results[0]["similarity"] > 0.65 else "draft",
                "exec_time": elapsed_ms
            })
            conn.commit()
    except Exception as log_err:
        print(f"Advertencia al registrar log en Oracle: {log_err}")
    finally:
        if conn:
            conn.close()

    return TicketResponse(
        ticket_id=payload.ticket_id,
        user_query=payload.user_query,
        suggested_resolution=llm_output,
        confidence_score=round(float(results[0]["similarity"]), 4),
        sources=sources,
        execution_time_ms=elapsed_ms
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("agent:app", host="0.0.0.0", port=8000, reload=False)
