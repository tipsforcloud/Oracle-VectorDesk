#!/usr/bin/env python3
"""
Asistente Interactivo de Instalación y Configuración (Setup Wizard)
Oracle-VectorDesk: Enterprise Support & Helpdesk RAG on Oracle Database 26ai
"""

import os
import sys
import getpass
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def print_banner():
    print("""
================================================================================
   ____                  _        __     __        _             ____            _    
  / __ \                | |       \ \   / /       | |           |  _ \          | |   
 | |  | |_ __ __ _  ___ | | ___    \ \_/ /__  ___ | |_ ___  _ __| | | |___  ___| | __
 | |  | | '__/ _` |/ __|| |/ _ \    \   / _ \/ __|| __/ _ \| '__| | | / _ \/ __| |/ /
 | |__| | | | (_| | (__ | |  __/     | |  __/ (__ | || (_) | |  | |_| |  __/\__ \   < 
  \____/|_|  \__,_|\___||_|\___|     |_|\___|\___| \__\___/|_|  |____/ \___||___/_|\_\\
                                                                                      
       Asistente Interactivo de Despliegue y Configuración en OCI
================================================================================
""")


def ask_input(prompt: str, default: str = "") -> str:
    if default:
        res = input(f"{prompt} [{default}]: ").strip()
        return res if res else default
    else:
        while True:
            res = input(f"{prompt}: ").strip()
            if res:
                return res


def check_python_dependencies():
    print("[1/5] Verificando dependencias de Python...")
    required = ["oracledb", "dotenv", "fastapi", "uvicorn", "pydantic", "requests"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"  -> Faltan paquetes requeridos: {', '.join(missing)}")
        install_now = input("  ¿Deseas instalarlos automáticamente con pip? [S/n]: ").strip().lower()
        if install_now != 'n':
            cmd = [sys.executable, "-m", "pip", "install", "--break-system-packages", "-r", str(BASE_DIR / "requirements.txt")]
            subprocess.check_call(cmd)
            print("  [✓] Dependencias base instaladas con éxito.")
    else:
        print("  [✓] Todas las dependencias base de Python están presentes.")


def setup_database_config():
    print("\n[2/5] Configuración de Conexión a Oracle Database 26ai...")
    print("Ingresa los datos de conexión a tu Base de Datos en OCI (Easy Connect):")

    host = ask_input("  Host / FQDN del DBSystem", "dbhost9185.sub04051019361.sarizavcn.oraclevcn.com")
    port = ask_input("  Puerto del Listener", "1521")
    service = ask_input("  Nombre del Servicio / PDB", "pdblab1.sub04051019361.sarizavcn.oraclevcn.com")
    user = ask_input("  Usuario de la Base de Datos", "app_support")
    
    password = getpass.getpass("  Contraseña del Usuario DB: ")
    while not password:
        password = getpass.getpass("  La contraseña no puede estar vacía. Reingresa: ")

    full_dsn = f"{host}:{port}/{service}"
    print(f"\n  Validando conectividad con Oracle 26ai en: {full_dsn}...")

    try:
        import oracledb
        conn = oracledb.connect(user=user, password=password, dsn=full_dsn)
        with conn.cursor() as cur:
            cur.execute("SELECT banner_full FROM v$version WHERE ROWNUM = 1")
            version = cur.fetchone()[0]
        conn.close()
        print(f"  [✓] ¡Conexión exitosa! Motor detectado: {version}")
    except Exception as e:
        print(f"\n  [!] Advertencia: No se pudo conectar a la base de datos: {e}")
        retry = input("  ¿Deseas guardar la configuración de todos modos? [S/n]: ").strip().lower()
        if retry == 'n':
            sys.exit(1)

    # Guardar en archivo .env
    env_content = f"""# Configuración Generada por Setup Wizard
DB_USER={user}
DB_PASSWORD={password}
DB_DSN={full_dsn}

# Inferencia en CPU (Ollama)
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_MODEL=qwen2.5:7b-instruct-q4_K_M
"""
    with open(str(BASE_DIR / ".env"), "w", encoding="utf-8") as f:
        f.write(env_content)
    print("  [✓] Archivo de entorno '.env' creado y configurado correctamente.")

    return user, password, full_dsn


def execute_sql_initialization(user, password, dsn):
    print("\n[3/5] Creación de Estructuras Vectoriales en Oracle 26ai...")
    run_ddl = input("  ¿Deseas verificar/crear las tablas de KNOWLEDGE_BASE y auditoría en la BD? [S/n]: ").strip().lower()
    if run_ddl != 'n':
        sql_file = BASE_DIR / "sql" / "init_db.sql"
        if not sql_file.exists():
            print(f"  [!] No se encontró el archivo: {sql_file}")
            return

        try:
            import oracledb
            conn = oracledb.connect(user=user, password=password, dsn=dsn)
            with open(str(sql_file), "r", encoding="utf-8") as f:
                content = f.read()

            # Separar sentencias por ';'
            statements = [stmt.strip() for stmt in content.split(";") if stmt.strip() and not stmt.strip().startswith("--")]
            with conn.cursor() as cur:
                for stmt in statements:
                    try:
                        cur.execute(stmt)
                    except Exception as err:
                        if "ORA-00955" in str(err) or "already exists" in str(err):
                            pass  # Ya existe la tabla o índice
                        else:
                            print(f"    Nota en sentencia: {err}")
            conn.commit()
            conn.close()
            print("  [✓] Estructuras de base de datos verificadas y listas.")
        except Exception as e:
            print(f"  [!] Error al ejecutar DDL: {e}")


def check_ollama_service():
    print("\n[4/5] Verificando Motor LLM en CPU (Ollama)...")
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m.get("name") for m in resp.json().get("models", [])]
            print(f"  [✓] Servicio Ollama activo. Modelos disponibles: {', '.join(models) if models else 'Ninguno'}")
            if not any("qwen2.5:7b" in m for m in models):
                print("  [!] Aviso: El modelo 'qwen2.5:7b-instruct-q4_K_M' no está descargado.")
                print("      Ejecuta en consola: ollama pull qwen2.5:7b-instruct-q4_K_M")
        else:
            print("  [!] Ollama respondió con código no exitoso.")
    except Exception:
        print("  [!] No se pudo conectar a Ollama en http://localhost:11434.")
        print("      Asegúrate de instalarlo con: curl -fsSL https://ollama.com/install.sh | sh")


def setup_knowledge_base():
    print("\n[5/5] Ingesta de Documentos a la Base de Conocimiento...")
    print("  Selecciona cómo deseas inicializar el conocimiento:")
    print("  1) Generar y cargar los 10 documentos PDF de demostración (Recomendado para pruebas iniciales).")
    print("  2) Ingestar mis propios documentos PDF colocados en 'data/documents/'.")
    print("  3) Omitir por ahora (subiré mis archivos PDF más tarde).")

    choice = input("  Selecciona una opción [1/2/3, por defecto 3]: ").strip()
    if choice == "1":
        print("\n  Generando 10 documentos PDF en data/demo_docs/...")
        gen_script = BASE_DIR / "scripts" / "generate_demo_pdfs.py"
        subprocess.check_call([sys.executable, str(gen_script)])

        print("\n  Vectorizando e ingestando demo PDFs en Oracle Database 26ai...")
        ingest_script = BASE_DIR / "scripts" / "ingest_documents.py"
        subprocess.check_call([sys.executable, str(ingest_script), "--demo"])
    elif choice == "2":
        print("\n  Iniciando ingesta de documentos propios desde 'data/documents/'...")
        ingest_script = BASE_DIR / "scripts" / "ingest_documents.py"
        subprocess.check_call([sys.executable, str(ingest_script)])
    else:
        print("  [✓] Ingesta omitida. Puedes colocar tus archivos PDF en 'data/documents/' en cualquier momento")
        print("      y ejecutar: python3 scripts/ingest_documents.py")


def main():
    print_banner()
    check_python_dependencies()
    user, password, dsn = setup_database_config()
    execute_sql_initialization(user, password, dsn)
    check_ollama_service()
    setup_knowledge_base()

    print("\n================================================================================")
    print(" ¡DESPLIEGUE Y CONFIGURACIÓN COMPLETADOS CON ÉXITO! ")
    print("================================================================================")
    print("\nPara iniciar el servicio del agente ejecuta:")
    print("  python3 run.py")
    print("\nPara ejecutar el benchmark de 20 preguntas:")
    print("  python3 scripts/run_benchmark.py")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
