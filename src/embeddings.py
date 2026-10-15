"""
Módulo de Generación de Embeddings Vectoriales en CPU
Utiliza sentence-transformers con el modelo 'intfloat/multilingual-e5-base' (768 dimensiones).
"""

from typing import List
from sentence_transformers import SentenceTransformer
from src.config import EMBEDDING_MODEL_NAME

print(f"Inicializando modelo de embeddings: {EMBEDDING_MODEL_NAME} en CPU...")
_embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
print("Modelo de embeddings cargado en memoria RAM.")


def get_query_embedding(query_text: str) -> List[float]:
    """
    Genera el vector de búsqueda para una consulta del usuario.
    Los modelos E5 requieren el prefijo 'query: ' para maximizar la similitud con pasajes.
    """
    text_with_prefix = f"query: {query_text.strip()}"
    return _embed_model.encode(text_with_prefix, normalize_embeddings=True).tolist()


def get_passage_embedding(document_text: str, title: str = "") -> List[float]:
    """
    Genera el vector de indexación para un pasaje o documento.
    Los modelos E5 requieren el prefijo 'passage: ' para la base documental.
    """
    prefix = f"passage: {title}. " if title else "passage: "
    text_with_prefix = f"{prefix}{document_text.strip()}"
    return _embed_model.encode(text_with_prefix, normalize_embeddings=True).tolist()
