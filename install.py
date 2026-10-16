#!/usr/bin/env python3
"""
Asistente Interactivo de Instalación y Configuración (Setup Wizard)
Oracle-VectorDesk: Enterprise Support & Helpdesk RAG on Oracle Database 26ai
"""

import os
import sys
import shutil
import getpass
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))


def print_banner():
    print(r"""
================================================================================
   ____                  _        __     __        _             ____            _    
  / __ \                | |       \ \   / /       | |           |  _ \          | |   
 | |  | |_ __ __ _  ___ | | ___    \ \_/ /__  ___ | |_ ___  _ __| | | |___  ___| | __
 | |  | | '__/ _` |/ __|| |/ _ \    \   / _ \/ __|| __/ _ \| '__| | | / _ \/ __| |/ /
 | |__| | | | (_| | (__ | |  __/     | |  __/ (__ | || (_) | |  | |_| |  __/\__ \   < 
  \____/|_|  \__,_|\___||_|\___|     |_|\___|\___| \__\___/|_|  |____/ \___||___/_|\_\\
                                                                                      
       Asistente Interactivo de Despliegue y Configuración en OCI
       Desarrollado para la comunidad por TipsForCloud
       🌐 https://tipsforcloud.com | 📺 https://www.youtube.com/@TipsForCloud
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
    print("[1/6] Verificando dependencias de Python...")
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


def load_existing_env():
    """Carga variables del archivo .env si existe en el directorio."""
    env_file = BASE_DIR / ".env"
    env_vars = {}
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars


def setup_database_config():
    print("\n[2/6] Configuración y Conexión a Oracle Database 26ai...")
    print("  Selecciona la modalidad de tu Base de Datos en OCI:")
    print("  1) Base Database Service en VM / On-Prem / Contenedor (SQL*Net TCP :1521) [Recomendado]")
    print("  2) Autonomous AI Database Serverless (mTLS con Wallet zip/directorio)")

    db_flavor = input("  Modalidad [1/2, defecto 1]: ").strip()
    if not db_flavor:
        db_flavor = "1"

    wallet_dir = None
    wallet_password = None

    env_vars = load_existing_env()
    existing_dsn = env_vars.get("DB_DSN", "")
    existing_user = env_vars.get("DB_USER", "app_support")

    default_host = existing_dsn.split(":")[0] if ":" in existing_dsn else ""
    default_port = existing_dsn.split(":")[1].split("/")[0] if ":" in existing_dsn and "/" in existing_dsn else "1521"
    default_service = existing_dsn.split("/")[1] if "/" in existing_dsn else ""

    if db_flavor == "2":
        print("\n  -- Conexión a Oracle Autonomous AI Database (Serverless) --")
        wallet_dir = ask_input("  Ruta al directorio de la Wallet (descomprimida)", env_vars.get("WALLET_DIR", "/opt/oracle/wallet"))
        wallet_pwd_input = getpass.getpass("  Contraseña de la Wallet (opcional, Enter para omitir): ").strip()
        wallet_password = wallet_pwd_input if wallet_pwd_input else env_vars.get("WALLET_PASSWORD", None)
        full_dsn = ask_input("  Nombre del TNS Alias / Servicio", existing_dsn if existing_dsn and not ":" in existing_dsn else "vectordb_low")
        user = ask_input("  Usuario de la Base de Datos (ej. ADMIN o usuario en PDB)", env_vars.get("DB_USER", "ADMIN"))
        password = getpass.getpass("  Contraseña del Usuario DB: ")
        while not password:
            password = getpass.getpass("  La contraseña no puede estar vacía. Reingresa: ")
    else:
        print("\n  -- Conexión a Oracle Base Database Service (VM / Docker / On-Prem) --")
        print("  💡 Asegúrate de que el usuario en la PDB tenga cuota y permisos para crear tablas:")
        print("     GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO <usuario>;")
        prompt_host = "  Host / FQDN o IP del DBSystem"
        if not default_host:
            prompt_host += " (ej. 10.0.1.15 o dbhost.sub.yourvcn.oraclevcn.com)"
        host = ask_input(prompt_host, default_host)
        port = ask_input("  Puerto del Listener", default_port)
        prompt_svc = "  Nombre del Servicio / PDB"
        if not default_service:
            prompt_svc += " (ej. pdb1.sub.yourvcn.oraclevcn.com o FREEPDB1)"
        service = ask_input(prompt_svc, default_service)
        user = ask_input("  Usuario de Base de Datos en la PDB (ej. app_support o SYSTEM)", existing_user)
        full_dsn = f"{host}:{port}/{service}"
        password = getpass.getpass("  Contraseña del Usuario DB: ")
        while not password:
            password = getpass.getpass("  La contraseña no puede estar vacía. Reingresa: ")

    print(f"\n  Validando conectividad directa con Oracle 26ai en: {full_dsn}...")
    try:
        import oracledb
        connect_kwargs = {
            "user": user,
            "password": password,
            "dsn": full_dsn
        }
        if wallet_dir:
            connect_kwargs["wallet_location"] = wallet_dir
            if wallet_password:
                connect_kwargs["wallet_password"] = wallet_password

        conn = oracledb.connect(**connect_kwargs)
        with conn.cursor() as cur:
            cur.execute("SELECT banner_full FROM v$version WHERE ROWNUM = 1")
            version = cur.fetchone()[0]
        conn.close()
        first_line = [l.strip() for l in version.splitlines() if l.strip()]
        print(f"  [✓] ¡Conexión exitosa a Oracle Database! ({first_line[0] if first_line else version})")
    except Exception as e:
        err_msg = str(e)
        print(f"\n  [!] Advertencia: No se pudo conectar directamente por TCP a la base de datos: {err_msg}")
        if "DPY-3001" in err_msg:
            print("\n  🔍 Diagnóstico (DPY-3001 - Native Network Encryption):")
            print("   - En OCI DBSystems, 'sqlnet.ora' suele tener 'SQLNET.ENCRYPTION_SERVER = REQUIRED'.")
            print("   - Para permitir conexiones modo Thin de python-oracledb, edita sqlnet.ora en el servidor")
            print("     y cambia a 'SQLNET.ENCRYPTION_SERVER = ACCEPTED'.")
        elif "DPY-6001" in err_msg or "ORA-12514" in err_msg:
            print("\n  🔍 Diagnóstico (ORA-12514 - Service not registered):")
            print("   - Verifica que el nombre del servicio o PDB sea el correcto con 'lsnrctl status'.")
            print("   - En OCI DBSystems el servicio suele incluir el dominio de la VCN.")
        elif "ORA-01017" in err_msg:
            print("\n  🔍 Diagnóstico (ORA-01017 - Credenciales inválidas):")
            print("   - Usuario o contraseña incorrectos, o el usuario no existe en la PDB.")

        retry = input("  ¿Deseas guardar la configuración de todos modos? [S/n]: ").strip().lower()
        if retry == 'n':
            sys.exit(1)

    # Guardar en archivo .env
    env_lines = [
        "# Configuración Generada por Setup Wizard",
        f"DB_USER={user}",
        f"DB_PASSWORD={password}",
        f"DB_DSN={full_dsn}"
    ]
    if wallet_dir:
        env_lines.append(f"WALLET_DIR={wallet_dir}")
        if wallet_password:
            env_lines.append(f"WALLET_PASSWORD={wallet_password}")

    env_lines.extend([
        "",
        "# Inferencia en CPU (Ollama)",
        "OLLAMA_URL=http://localhost:11434/api/generate",
        "OLLAMA_MODEL=qwen3:4b",
        "",
        "# Modelo de Embeddings y Umbral",
        "EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-base",
        "EMBEDDING_DIM=768",
        "SIMILARITY_THRESHOLD=0.35"
    ])

    with open(str(BASE_DIR / ".env"), "w", encoding="utf-8") as f:
        f.write("\n".join(env_lines) + "\n")
    print("  [✓] Archivo de entorno '.env' creado y configurado correctamente.")

    return user, password, full_dsn, wallet_dir, wallet_password


def execute_sql_initialization(user, password, dsn, wallet_dir=None, wallet_password=None):
    print("\n[3/6] Configuración de Estructuras Vectoriales en Oracle 26ai...")

    sql_file = BASE_DIR / "sql" / "init_db.sql"
    if not sql_file.exists():
        print(f"  [!] No se encontró el archivo DDL: {sql_file}")
        return

    try:
        import oracledb
        connect_kwargs = {
            "user": user,
            "password": password,
            "dsn": dsn
        }
        if wallet_dir:
            connect_kwargs["wallet_location"] = wallet_dir
            if wallet_password:
                connect_kwargs["wallet_password"] = wallet_password

        conn = oracledb.connect(**connect_kwargs)
        cur = conn.cursor()

        # Inspeccionar si las tablas ya existen en el esquema del usuario
        cur.execute("""
            SELECT table_name 
            FROM user_tables 
            WHERE table_name IN ('KNOWLEDGE_BASE', 'AGENT_TICKETS_LOG')
        """)
        existing_tables = [row[0] for row in cur.fetchall()]

        if existing_tables:
            print(f"  [i] Se detectaron tablas existentes en el esquema: {', '.join(existing_tables)}")
            print("      ¿Cómo deseas proceder?")
            print("      1) Conservar tablas y datos existentes (Continuar instalación).")
            print("      2) Eliminar tablas existentes (DROP PURGE) y crearlas limpias desde cero.")
            print("      3) Cancelar instalación.")
            
            action = input("      Selecciona una opción [1/2/3, por defecto 1]: ").strip()
            if action == "2":
                print("      Purgando tablas previas de Oracle-VectorDesk...")
                for t in existing_tables:
                    try:
                        cur.execute(f"DROP TABLE {t} PURGE")
                        print(f"      [✓] Tabla {t} eliminada.")
                    except Exception as drop_err:
                        print(f"      [!] Error eliminando {t}: {drop_err}")
                conn.commit()
            elif action == "3":
                print("      Instalación cancelada por el usuario.")
                conn.close()
                sys.exit(0)
            else:
                print("      [✓] Conservando tablas y datos existentes.")
                conn.close()
                return

        # Crear estructuras mediante init_db.sql
        print("  Creando estructuras vectoriales (VECTOR 768d y logs de auditoría)...")
        with open(str(sql_file), "r", encoding="utf-8") as f:
            content = f.read()

        statements = [stmt.strip() for stmt in content.split(";") if stmt.strip() and not stmt.strip().startswith("--")]
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
        print("  [✓] Estructuras de base de datos creadas y listas.")

    except Exception as e:
        print(f"  [!] Error al interactuar con la base de datos: {e}")


def check_ollama_service():
    print("\n[4/6] Verificando Motor LLM en CPU (Ollama)...")
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m.get("name") for m in resp.json().get("models", [])]
            print(f"  [✓] Servicio Ollama activo. Modelos disponibles: {', '.join(models) if models else 'Ninguno'}")
            if not any("qwen3" in m.lower() or "qwen2.5" in m.lower() for m in models):
                print("  [!] Aviso: El modelo 'qwen3:4b' no está descargado.")
                print("      Ejecuta en consola: ollama pull qwen3:4b")
        else:
            print("  [!] Ollama respondió con código no exitoso.")
    except Exception:
        print("  [!] No se pudo conectar a Ollama en http://localhost:11434.")
        print("      Asegúrate de instalarlo con: curl -fsSL https://ollama.com/install.sh | sh")


def setup_knowledge_base():
    print("\n[5/6] Ingesta de Documentos a la Base de Conocimiento...")
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


def configure_firewall_port(port: int = 8000):
    """Verifica y abre el puerto en firewalld si está activo."""
    if sys.platform != "linux" or not shutil.which("firewall-cmd"):
        return

    try:
        cmd_prefix = [] if os.geteuid() == 0 else ["sudo"]
        st = subprocess.run(cmd_prefix + ["firewall-cmd", "--state"], capture_output=True, text=True)
        if st.returncode != 0 or "running" not in st.stdout.lower():
            return

        qp = subprocess.run(cmd_prefix + ["firewall-cmd", f"--query-port={port}/tcp"], capture_output=True, text=True)
        if qp.returncode == 0 and "yes" in qp.stdout.lower():
            print(f"  [✓] Cortafuegos (firewalld): Puerto {port}/tcp ya se encuentra abierto.")
        else:
            print(f"  [!] Cortafuegos detectado: El puerto {port}/tcp está bloqueado.")
            open_fw = input(f"  ¿Deseas abrir el puerto {port}/tcp permanentemente en firewalld? [S/n]: ").strip().lower()
            if open_fw != 'n':
                subprocess.run(cmd_prefix + ["firewall-cmd", "--permanent", f"--add-port={port}/tcp"], check=True)
                subprocess.run(cmd_prefix + ["firewall-cmd", "--reload"], check=True)
                print(f"  [✓] Puerto {port}/tcp abierto permanentemente y reglas de firewalld recargadas.")
    except Exception as e:
        print(f"  [!] Nota al verificar cortafuegos: {e}")


def configure_systemd_service():
    print("\n[6/6] Configuración de Red, Cortafuegos y Servicio en Segundo Plano...")
    
    # 1. Verificar y abrir puerto 8000 en firewalld
    configure_firewall_port(8000)

    if sys.platform != "linux":
        print("  Nota: systemd está disponible en servidores Linux (Oracle Linux / Ubuntu). Omitiendo.")
        return False

    install_srv = input("\n  ¿Deseas registrar e iniciar Oracle-VectorDesk como servicio de systemd? [S/n]: ").strip().lower()
    if install_srv != 'n':
        try:
            from scripts.setup_systemd_service import setup_systemd
            return setup_systemd(start_now=True)
        except Exception as err:
            print(f"  [!] No se pudo activar el servicio systemd: {err}")
            return False
    return False


def main():
    print_banner()
    check_python_dependencies()
    user, password, dsn, wallet_dir, wallet_password = setup_database_config()
    execute_sql_initialization(user, password, dsn, wallet_dir, wallet_password)
    check_ollama_service()
    setup_knowledge_base()
    service_active = configure_systemd_service()

    print("\n================================================================================")
    print(" ¡DESPLIEGUE Y CONFIGURACIÓN COMPLETADOS CON ÉXITO! ")
    print("================================================================================")
    if service_active:
        print("\nEl agente ya está OPERATIVO EN SEGUNDO PLANO como servicio del sistema:")
        print("  • Ver estado:        sudo systemctl status oracle-vectordesk")
        print("  • Ver logs en vivo:  sudo journalctl -u oracle-vectordesk -f")
        print("  • Reiniciar:         sudo systemctl restart oracle-vectordesk")
    else:
        print("\nPara iniciar el servicio manualmente en primer plano:")
        print("  python3 run.py")
        print("\nO para instalarlo como servicio en segundo plano más adelante:")
        print("  python3 scripts/setup_systemd_service.py")

    print("\nPara ejecutar el benchmark de 20 preguntas:")
    print("  python3 scripts/run_benchmark.py")
    print("\n--------------------------------------------------------------------------------")
    print(" 🚀 Oracle-VectorDesk es un proyecto Open Source de TipsForCloud:")
    print("   🌐 Sitio Web Oficial: https://tipsforcloud.com")
    print("   📺 Canal de YouTube:  https://www.youtube.com/@TipsForCloud")
    print("   ⭐ Repositorio:       https://github.com/tipsforcloud/Oracle-VectorDesk")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
