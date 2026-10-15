"""
Script de Ingesta y Vectorización de Documentos PDF
Extrae texto de archivos PDF en data/documents/ (o data/demo_docs/),
calcula embeddings (768d) con intfloat/multilingual-e5-base y los inserta
en la tabla KNOWLEDGE_BASE de Oracle Database 26ai.

Uso:
  python3 scripts/ingest_documents.py                 # Ingesta desde data/documents/
  python3 scripts/ingest_documents.py --demo          # Ingesta desde data/demo_docs/
  python3 scripts/ingest_documents.py --dir /mi/ruta  # Ingesta desde ruta personalizada
"""

import os
import sys
import glob
import argparse
from pathlib import Path

# Agregar raíz al sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import DOCUMENTS_DIR, DEMO_DOCS_DIR, DB_DSN, DB_USER
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


def determine_target_directory(args) -> Path:
    """Determina de qué carpeta se deben leer los PDFs."""
    if args.dir:
        custom_p = Path(args.dir)
        if not custom_p.exists():
            print(f"Error: El directorio especificado no existe: {args.dir}")
            sys.exit(1)
        return custom_p

    if args.demo:
        return DEMO_DOCS_DIR

    # Por defecto buscar en data/documents/ (documentos propios del cliente)
    client_files = glob.glob(os.path.join(str(DOCUMENTS_DIR), "*.pdf"))
    if client_files:
        return DOCUMENTS_DIR

    # Si data/documents/ está vacío, verificar si demo_docs tiene archivos
    demo_files = glob.glob(os.path.join(str(DEMO_DOCS_DIR), "*.pdf"))
    if demo_files:
        print(f"Nota: No se detectaron PDFs en '{DOCUMENTS_DIR}'.")
        print(f"Se encontraron {len(demo_files)} documentos en '{DEMO_DOCS_DIR}'.")
        choice = input("¿Deseas procesar los documentos de demostración? [S/n]: ").strip().lower()
        if choice != 'n':
            return DEMO_DOCS_DIR

    return DOCUMENTS_DIR


def ingest_pdfs(target_dir: Path):
    pdf_files = sorted(glob.glob(os.path.join(str(target_dir), "*.pdf")))
    if not pdf_files:
        print(f"\n[!] No se encontraron archivos PDF en: {target_dir}")
        print(f"    Coloca tus archivos PDF en '{DOCUMENTS_DIR}' y vuelve a ejecutar este script.")
        print("    O si deseas generar los de demo, ejecuta: python3 scripts/generate_demo_pdfs.py")
        return

    print("================================================================================")
    print(" INGESTA DE DOCUMENTOS PDF EN ORACLE DATABASE 26ai (AI VECTOR SEARCH) ")
    print("================================================================================")
    print(f"Directorio fuente: {target_dir}")
    print(f"Total de archivos PDF: {len(pdf_files)}")
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
            print("  -> Advertencia: Documento sin texto extraíble. Omitiendo.")
            continue

        clean_name = filename.replace(".pdf", "")
        parts = clean_name.split("_", 2)
        doc_code = parts[0] if len(parts) > 1 else "DOC"
        title = parts[-1].replace("_", " ") if len(parts) > 1 else clean_name.replace("_", " ")

        category = "General / Documentación Corporativa"
        if "Wifi" in filename or "VPN" in filename or "Red" in filename:
            category = "Redes y Conectividad"
        elif "MFA" in filename or "Phishing" in filename or "BYOD" in filename or "Seguridad" in filename:
            category = "Ciberseguridad e Identidad"
        elif "Hardware" in filename or "Impresion" in filename or "Equipo" in filename:
            category = "Activos y Servicios TI"
        elif "SAP" in filename or "ERP" in filename or "CRM" in filename:
            category = "Aplicaciones Corporativas"
        elif "OneDrive" in filename or "Backup" in filename or "Copia" in filename:
            category = "Almacenamiento y Backup"
        elif "Bajas" in filename or "Offboarding" in filename or "Acceso" in filename:
            category = "Gestión de Identidades y Accesos"
        elif "Guardias" in filename or "Soporte" in filename or "Mesa" in filename:
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


def main():
    parser = argparse.ArgumentParser(description="Ingesta y vectorización de PDFs a Oracle 26ai")
    parser.add_argument("--demo", action="store_true", help="Ingestar directamente desde data/demo_docs/")
    parser.add_argument("--dir", type=str, help="Ruta personalizada a un directorio con PDFs")
    args = parser.parse_args()

    target_dir = determine_target_directory(args)
    ingest_pdfs(target_dir)


if __name__ == "__main__":
    main()
