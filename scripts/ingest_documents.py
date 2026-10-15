"""
Script de Ingesta y Vectorización de Documentos PDF
Extrae texto de archivos PDF en data/demo_docs/, calcula embeddings (768d)
y los inserta en la tabla KNOWLEDGE_BASE de Oracle Database 26ai.
"""

import os
import sys
import glob
from pathlib import Path

# Agregar raíz al sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import DEMO_DOCS_DIR, DB_DSN, DB_USER
from src.embeddings import get_passage_embedding
from src.database import insert_knowledge_document, test_db_connection


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrae el contenido de un archivo PDF usando pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("Error: 'pypdf' no está instalado.")
        print("Instálalo ejecutando: pip3 install --break-system-packages pypdf")
        sys.exit(1)

    reader = PdfReader(pdf_path)
    full_text = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        if page_text.strip():
            full_text.append(page_text.strip())
    return "\n\n".join(full_text)


def ingest_all_pdfs():
    pdf_files = sorted(glob.glob(os.path.join(str(DEMO_DOCS_DIR), "*.pdf")))
    if not pdf_files:
        print(f"No se encontraron archivos PDF en: {DEMO_DOCS_DIR}")
        print("Por favor ejecuta primero: python3 scripts/generate_demo_pdfs.py")
        return

    print("================================================================================")
    print(" INGESTA DE DOCUMENTOS PDF EN ORACLE DATABASE 26ai (AI VECTOR SEARCH) ")
    print("================================================================================")
    print(f"Directorio fuente: {DEMO_DOCS_DIR}")
    print(f"Total de archivos: {len(pdf_files)}")
    print(f"Destino: Oracle Database 26ai @ {DB_DSN} (Usuario: {DB_USER})\n")

    # Validar conexión antes de procesar
    db_check = test_db_connection()
    if not db_check["ok"]:
        print(f"Error conectando a Oracle Database 26ai: {db_check['error']}")
        sys.exit(1)

    print("Conexión exitosa con la base de datos.")
    print("Iniciando extracción de texto y cálculo de vectores (768 dimensiones)...\n")

    count = 0
    for idx, pdf_path in enumerate(pdf_files, 1):
        filename = os.path.basename(pdf_path)
        print(f"[{idx}/{len(pdf_files)}] Procesando: {filename}...")

        text = extract_text_from_pdf(pdf_path)
        if not text:
            print("  -> Advertencia: Documento vacío. Omitiendo.")
            continue

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

        metadata = {
            "source_file": filename,
            "document_code": doc_code,
            "category": category,
            "total_chars": len(text)
        }

        # Generar embedding de 768d con prefijo 'passage: '
        vector = get_passage_embedding(text, title=title)

        # Insertar en Oracle Database 26ai
        insert_knowledge_document(
            title=title,
            category=category,
            content=text,
            metadata=metadata,
            vector_floats=vector
        )
        count += 1
        print(f"  -> [✓] Vectorizado e insertado bajo categoría '{category}'.")

    print("\n================================================================================")
    print(f" ¡ÉXITO! Se ingirieron {count} documentos en Oracle Database 26ai.")
    print("================================================================================\n")


if __name__ == "__main__":
    ingest_all_pdfs()
