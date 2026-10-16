"""
Capa de Persistencia y Acceso a Datos
Conector y operaciones nativas en Oracle Database 26ai (AI Vector Search).
"""

import array
import json
import oracledb
from typing import List, Dict, Any, Optional
from src.config import DB_USER, DB_PASSWORD, DB_DSN, WALLET_DIR, WALLET_PASSWORD

# Inicializar Modo Thick (Oracle Instant Client) para soporte completo de
# Native Network Encryption (SQLNET.ENCRYPTION_SERVER = REQUIRED), ATP y Base DB.
try:
    oracledb.init_oracle_client()
except Exception:
    pass


def get_connection():
    """Retorna una conexión abierta hacia Oracle Database 26ai."""
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


def test_db_connection() -> Dict[str, Any]:
    """Valida la conectividad básica contra la base de datos."""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT banner_full FROM v$version WHERE ROWNUM = 1")
            banner = cur.fetchone()[0]
        conn.close()
        return {"ok": True, "banner": banner}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def search_vector_knowledge_base(query_vector: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Ejecuta una búsqueda vectorial exacta (Exact Vector Search) sobre Oracle Database 26ai
    utilizando la función nativa VECTOR_DISTANCE(..., COSINE) optimizada con SIMD.
    """
    vector_data = array.array("f", query_vector)
    results = []

    sql = f"""
        SELECT id, title, category, TO_CHAR(content) AS content_str,
               (1 - VECTOR_DISTANCE(embedding, :query_vec, COSINE)) AS similarity
        FROM knowledge_base
        ORDER BY VECTOR_DISTANCE(embedding, :query_vec, COSINE) ASC
        FETCH FIRST {int(top_k)} ROWS ONLY
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, {"query_vec": vector_data})
            for row in cur.fetchall():
                results.append({
                    "id": row[0],
                    "title": row[1],
                    "category": row[2],
                    "content": row[3],
                    "similarity": float(row[4]) if row[4] is not None else 0.0
                })
    finally:
        conn.close()

    return results


def insert_knowledge_document(title: str, category: str, content: str, 
                              metadata: Optional[Dict[str, Any]], 
                              vector_floats: List[float]) -> int:
    """Inserta un documento y su correspondiente vector en la tabla knowledge_base."""
    vector_data = array.array("f", vector_floats)
    meta_json = json.dumps(metadata) if metadata else None

    sql = """
        INSERT INTO knowledge_base (title, category, content, metadata, embedding)
        VALUES (:title, :category, :content, :metadata, :embedding)
    """

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, {
                "title": title,
                "category": category,
                "content": content,
                "metadata": meta_json,
                "embedding": vector_data
            })
            conn.commit()
    finally:
        conn.close()

    return True


def log_ticket_resolution(ticket_id: str, user_query: str, retrieved_context: str,
                          agent_response: str, confidence_score: float, 
                          status: str, execution_time_ms: int):
    """Registra de manera asíncrona o directa el resultado del ticket en la tabla de auditoría."""
    sql = """
        INSERT INTO agent_tickets_log 
        (ticket_external_id, user_query, retrieved_context, agent_response, confidence_score, status, execution_time_ms)
        VALUES (:ticket_id, :user_query, :context, :response, :score, :status, :exec_time)
    """

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(sql, {
                "ticket_id": ticket_id,
                "user_query": user_query,
                "context": retrieved_context,
                "response": agent_response,
                "score": float(confidence_score),
                "status": status,
                "exec_time": execution_time_ms
            })
            conn.commit()
    except Exception as e:
        print(f"Advertencia al registrar auditoría en Oracle: {e}")
    finally:
        if conn:
            conn.close()
