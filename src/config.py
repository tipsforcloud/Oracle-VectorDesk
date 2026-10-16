"""
Módulo de Configuración Centralizada
Carga variables de entorno desde .env o el entorno del sistema.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Localizar la raíz del proyecto (un nivel arriba de src/)
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar archivo .env si existe en la raíz
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()

# Configuración de Oracle Database 26ai
DB_USER = os.getenv("DB_USER", "app_support")
DB_PASSWORD = os.getenv("DB_PASSWORD", "CambiarPorTuPassword123!")
DB_DSN = os.getenv("DB_DSN", "localhost:1521/FREEPDB1")
WALLET_DIR = os.getenv("WALLET_DIR", None)
WALLET_PASSWORD = os.getenv("WALLET_PASSWORD", None)

# Configuración del Motor de Inferencia en CPU (Ollama)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

# Configuración del Modelo de Embeddings
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-base")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))

# Umbral de Similitud Semántica para Escalar a Humano (Safe Fallback)
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.35"))

# Rutas de Datos y Documentos
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
DEMO_DOCS_DIR = DATA_DIR / "demo_docs"
BENCHMARK_FILE = DATA_DIR / "benchmark_questions.json"
SQL_INIT_FILE = BASE_DIR / "sql" / "init_db.sql"
