"""
Modelos de Datos y Esquemas Pydantic
Definen los contratos de entrada y salida para la API REST.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class SourceItem(BaseModel):
    id: int
    title: str
    similarity: float


class TicketRequest(BaseModel):
    ticket_id: Optional[str] = Field(default="TCK-1001", description="Identificador único del ticket")
    user_query: str = Field(..., description="Pregunta o consulta del usuario")
    category: Optional[str] = Field(default=None, description="Categoría opcional del ticket")


class TicketResponse(BaseModel):
    ticket_id: Optional[str]
    user_query: str
    suggested_resolution: str
    confidence_score: float
    sources: List[SourceItem]
    execution_time_ms: int
    tokens_generated: Optional[int] = Field(default=None, description="Total de tokens generados por el LLM")
    tokens_per_second: Optional[float] = Field(default=None, description="Velocidad de generación en tokens por segundo")


class HealthResponse(BaseModel):
    status: str
    database: str
    embedding_model: str
    llm_model: str
    dsn: str
