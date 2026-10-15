"""
Script de Ingesta y Vectorización de Documentos PDF
Motor: Oracle Database 26ai (AI Vector Search Nativo)
Extrae texto de archivos PDF en docs_demo/, genera embeddings de 768 dimensiones
con 'intfloat/multilingual-e5-base' en CPU e inserta en la tabla KNOWLEDGE_BASE.
"""

import os
import sys
import array
import json
import glob
import oracledb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Parámetros de conexión a Oracle Database 26ai
DB_USER = os.getenv("DB_USER", "app_support")
DB_PASSWORD = os.getenv("DB_PASSWORD", "CambiarPorTuPassword123!")
DB_DSN = os.getenv("DB_DSN", "localhost:1521/PDBLAB1")

DOCS_DIR = os.getenv("DOCS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs_demo"))


def extract_text_from_pdf(pdf_path):
    """Extrae el contenido de un PDF usando pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("La librería 'pypdf' no está instalada.")
        print("Por favor instala pypdf ejecutando: pip3 install --break-system-packages pypdf")
        sys.exit(1)

    reader = PdfReader(pdf_path)
    full_text = []
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if page_text.strip():
            full_text.append(page_text.strip())
    return "\n\n".join(full_text)


def ingest_pdfs():
    pdf_files = sorted(glob.glob(os.path.join(DOCS_DIR, "*.pdf")))
    if not pdf_files:
        print(f"No se encontraron archivos PDF en el directorio: {DOCS_DIR}")
        print("Asegúrate de ejecutar primero: python3 generate_sample_pdfs.py")
        return

    print("================================================================================")
    print(" INGESTA DE DOCUMENTOS PDF EN ORACLE DATABASE 26ai (AI VECTOR SEARCH) ")
    print("================================================================================")
    print(f"Directorio de documentos: {DOCS_DIR}")
    print(f"Total de PDFs detectados: {len(pdf_files)}")
    print(f"Destino: Oracle Database 26ai @ {DB_DSN} (Usuario: {DB_USER})\n")

    print("Cargando modelo de embeddings de alta precisión (768 dimensiones) en CPU...")
    embed_model = SentenceTransformer("intfloat/multilingual-e5-base")
    print("Modelo cargado exitosamente en RAM.\n")

    print("Conectando a Oracle Database 26ai...")
    conn = oracledb.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        dsn=DB_DSN
    )
    cur = conn.cursor()
    print("Conexión establecida con la Pluggable Database.\n")

    insert_sql = """
        INSERT INTO knowledge_base (title, category, content, metadata, embedding)
        VALUES (:title, :category, :content, :metadata, :embedding)
    """

    ingested_count = 0
    for idx, pdf_file in enumerate(pdf_files, 1):
        filename = os.path.basename(pdf_file)
        print(f"[{idx}/{len(pdf_files)}] Procesando: {filename}...")

        raw_text = extract_text_from_pdf(pdf_file)
        if not raw_text:
            print(f"  -> Advertencia: No se pudo extraer texto de {filename}. Omitiendo.")
            continue

        # Inferencia de título y categoría según el nombre del archivo
        clean_name = filename.replace(".pdf", "")
        parts = clean_name.split("_", 2)
        doc_code = parts[0] + ("-" + parts[1] if len(parts) > 2 else "")
        title = parts[-1].replace("_", " ")

        category = "Políticas y Procedimientos TI"
        if "Wifi" in filename or "VPN" in filename:
            category = "Redes y Conectividad"
        elif "MFA" in filename or "Phishing" in filename or "BYOD" in filename:
            category = "Ciberseguridad e Identidad"
        elif "Hardware" in filename or "Impresion" in filename:
            category = "Activos y Servicios TI"
        elif "SAP" in filename:
            category = "Aplicaciones Corporativas"
        elif "OneDrive" in filename:
            category = "Almacenamiento y Backup"
        elif "Bajas" in filename or "Offboarding" in filename:
            category = "Gestión de Identidades y Accesos"
        elif "Guardias" in filename or "Soporte" in filename:
            category = "Operaciones y Mesa de Ayuda"

        metadata = json.dumps({
            "source_file": filename,
            "document_code": doc_code,
            "category": category,
            "total_chars": len(raw_text)
        })

        # Generar embedding con prefijo obligatorio 'passage: ' para E5
        passage_input = f"passage: {title}. {raw_text}"
        vector = embed_model.encode(passage_input, normalize_embeddings=True).tolist()
        vector_data = array.array("f", vector)

        cur.execute(insert_sql, {
            "title": title,
            "category": category,
            "content": raw_text,
            "metadata": metadata,
            "embedding": vector_data
        })
        ingested_count += 1
        print(f"  -> Vectorizado y almacenado (768 dims) bajo categoría '{category}'.")

    conn.commit()
    cur.close()
    conn.close()

    print("\n================================================================================")
    print(f" ¡ÉXITO! Se ingirieron {ingested_count} documentos PDF en Oracle Database 26ai.")
    print("================================================================================\n")


if __name__ == "__main__":
    ingest_pdfs()
