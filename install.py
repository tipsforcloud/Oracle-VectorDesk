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


def run_ssh_command(ssh_host: str, ssh_user: str, ssh_key: str, command: str):
    """Ejecuta un comando bash remoto en el DBSystem a través de SSH."""
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5"]
    if ssh_key:
        key_p = Path(ssh_key).expanduser()
        if key_p.exists():
            cmd.extend(["-i", str(key_p)])
    cmd.append(f"{ssh_user}@{ssh_host}")
    cmd.append(command)

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        output = (res.stdout + "\n" + res.stderr).strip()
        return (res.returncode == 0), output
    except Exception as e:
        return False, str(e)


def run_ssh_sysdba_sql(ssh_host: str, ssh_user: str, ssh_key: str, pdb_name: str, sql_commands: str):
    """Ejecuta un bloque SQL como SYSDBA en el DBSystem mediante SSH."""
    pdb_clean = pdb_name.split(".")[0].upper()
    full_sql = f"""
ALTER SESSION SET CONTAINER = {pdb_clean};
{sql_commands}
EXIT;
"""
    remote_sh = f"""sudo su - oracle -c "sqlplus -s / as sysdba << 'EOF'
SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF
{full_sql}
EOF"
"""
    return run_ssh_command(ssh_host, ssh_user, ssh_key, remote_sh)


def setup_database_config():
    print("\n[2/6] Configuración y Conexión a Oracle Database 26ai...")
    print("  Selecciona la modalidad de tu Base de Datos en OCI:")
    print("  1) Base Database Service en VM (Aprovisionamiento por SSH como SYSDBA) [Recomendado]")
    print("  2) Base Database Service en VM (Conexión Directa SQL*Net TCP)")
    print("  3) Autonomous AI Database Serverless (mTLS con Wallet zip/directorio)")

    db_flavor = input("  Modalidad [1/2/3, defecto 1]: ").strip()
    if not db_flavor:
        db_flavor = "1"

    wallet_dir = None
    wallet_password = None
    already_provisioned = False

    env_vars = load_existing_env()
    existing_dsn = env_vars.get("DB_DSN", "")
    existing_user = env_vars.get("DB_USER", "app_support")

    default_host = existing_dsn.split(":")[0] if ":" in existing_dsn else ""
    default_port = existing_dsn.split(":")[1].split("/")[0] if ":" in existing_dsn and "/" in existing_dsn else "1521"
    default_service = existing_dsn.split("/")[1] if "/" in existing_dsn else ""

    if db_flavor == "3":
        print("\n  -- Conexión a Oracle Autonomous AI Database (Serverless) --")
        wallet_dir = ask_input("  Ruta al directorio de la Wallet (descomprimida)", env_vars.get("WALLET_DIR", "/opt/oracle/wallet"))
        wallet_pwd_input = getpass.getpass("  Contraseña de la Wallet (opcional, Enter para omitir): ").strip()
        wallet_password = wallet_pwd_input if wallet_pwd_input else env_vars.get("WALLET_PASSWORD", None)
        full_dsn = ask_input("  Nombre del TNS Alias / Servicio", existing_dsn if existing_dsn and not ":" in existing_dsn else "vectordb_low")
        user = ask_input("  Usuario de la Base de Datos", env_vars.get("DB_USER", "ADMIN"))
        password = getpass.getpass("  Contraseña del Usuario DB: ")
        while not password:
            password = getpass.getpass("  La contraseña no puede estar vacía. Reingresa: ")

    elif db_flavor == "2":
        print("\n  -- Conexión Directa a Oracle Base Database Service (VM) --")
        prompt_host = "  Host / FQDN o IP del DBSystem"
        if not default_host:
            prompt_host += " (ej. 10.0.1.15 o dbhost.sub.yourvcn.oraclevcn.com)"
        host = ask_input(prompt_host, default_host)
        port = ask_input("  Puerto del Listener", default_port)
        prompt_svc = "  Nombre del Servicio / PDB"
        if not default_service:
            prompt_svc += " (ej. pdb1.sub.yourvcn.oraclevcn.com o FREEPDB1)"
        service = ask_input(prompt_svc, default_service)
        user = ask_input("  Usuario de la Base de Datos", existing_user)
        full_dsn = f"{host}:{port}/{service}"
        password = getpass.getpass("  Contraseña del Usuario DB: ")
        while not password:
            password = getpass.getpass("  La contraseña no puede estar vacía. Reingresa: ")

    else:
        # Opción 1: Aprovisionamiento Automático por SSH en DBSystem como SYSDBA
        print("\n  -- Aprovisionamiento Automático por SSH en DBSystem (SYSDBA) --")
        prompt_host = "  Host / FQDN o IP del DBSystem (SSH)"
        if not default_host:
            prompt_host += " (ej. 10.0.1.15 o dbhost.sub.yourvcn.oraclevcn.com)"
        ssh_host = ask_input(prompt_host, default_host)
        ssh_user = ask_input("  Usuario SSH del DBSystem", "opc")
        ssh_key = ask_input("  Ruta a la llave privada SSH (o Enter si usas agente/default)", "~/.ssh/id_rsa")
        port = ask_input("  Puerto del Listener", default_port)
        prompt_svc = "  Nombre del Servicio / PDB"
        if not default_service:
            prompt_svc += " (ej. pdb1.sub.yourvcn.oraclevcn.com o FREEPDB1)"
        service = ask_input(prompt_svc, default_service)
        user = ask_input("  Usuario de Base de Datos para el Agente", existing_user)
        password = getpass.getpass("  Contraseña para el Usuario DB: ")
        while not password:
            password = getpass.getpass("  La contraseña no puede estar vacía. Reingresa: ")

        ssh_success = False
        while not ssh_success:
            pdb_clean = service.split(".")[0].upper()
            full_dsn = f"{ssh_host}:{port}/{service}"

            print(f"\n  [1/4] Probando conexión SSH con {ssh_user}@{ssh_host} y verificando SYSDBA en {pdb_clean}...")
            test_sql = "SELECT banner_full FROM v$version WHERE ROWNUM = 1;"
            ok, out = run_ssh_sysdba_sql(ssh_host, ssh_user, ssh_key, pdb_clean, test_sql)
            if not ok or not out:
                print(f"\n  [!] No se pudo conectar vía SSH al DBSystem o ejecutar SQL*Plus:")
                print(f"      {out}")
                print("\n  🔍 Diagnóstico habitual en Oracle Cloud Infrastructure (OCI):")
                print("   - Por defecto, la Security List de la subred del DBSystem bloquea el puerto 22 (SSH).")
                print("   - Si no puedes abrir el puerto 22 en OCI, la Opción 2 permite conectarse directamente")
                print("     mediante el puerto 1521 (SQL*Net TCP) usando python-oracledb.")
                print("\n  ¿Cómo deseas proceder?")
                print("   1) Cambiar a la Opción 2: Conexión Directa SQL*Net por puerto 1521 [Recomendado]")
                print("   2) Reingresar datos de conexión SSH (Host, usuario o llave)")
                print("   3) Omitir validación SSH y continuar de todos modos")
                print("   4) Cancelar instalación")

                choice = input("  Selecciona una opción [1/2/3/4, por defecto 1]: ").strip()
                if choice == "2":
                    ssh_host = ask_input("  Host / FQDN o IP del DBSystem (SSH)", ssh_host)
                    ssh_user = ask_input("  Usuario SSH del DBSystem", ssh_user)
                    ssh_key = ask_input("  Ruta a la llave privada SSH", ssh_key)
                    continue
                elif choice == "3":
                    print("  Continuando sin validación previa de SSH...")
                    break
                elif choice == "4":
                    print("  Instalación cancelada.")
                    sys.exit(0)
                else:
                    print("\n  [i] Cambiando a Opción 2 (Conexión Directa SQL*Net TCP por puerto 1521)...")
                    db_flavor = "2"
                    host = ssh_host
                    already_provisioned = False
                    break
            else:
                first_line = [l.strip() for l in out.splitlines() if l.strip()]
                print(f"  [✓] Conexión SSH y SYSDBA exitosa. Motor: {first_line[0] if first_line else 'Oracle Database'}")
                ssh_success = True

        if db_flavor == "1":
            print(f"\n  [2/4] Verificando / Creando usuario '{user}' en {pdb_clean}...")
            create_user_sql = f"""
DECLARE
    v_count NUMBER;
BEGIN
    SELECT count(*) INTO v_count FROM all_users WHERE username = UPPER('{user}');
    IF v_count = 0 THEN
        EXECUTE IMMEDIATE 'CREATE USER {user} IDENTIFIED BY "{password}"';
        EXECUTE IMMEDIATE 'GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO {user}';
    ELSE
        EXECUTE IMMEDIATE 'ALTER USER {user} IDENTIFIED BY "{password}"';
        EXECUTE IMMEDIATE 'GRANT CONNECT, RESOURCE, UNLIMITED TABLESPACE TO {user}';
    END IF;
END;
/
"""
            ok_usr, out_usr = run_ssh_sysdba_sql(ssh_host, ssh_user, ssh_key, pdb_clean, create_user_sql)
            if ok_usr:
                print(f"  [✓] Usuario '{user}' configurado con privilegios y cuota en {pdb_clean}.")
            else:
                print(f"  [!] Nota al verificar usuario: {out_usr}")

            print(f"\n  [3/4] Inspeccionando tablas vectoriales existentes en esquema '{user}'...")
            check_tables_sql = f"""
SELECT table_name FROM all_tables WHERE owner = UPPER('{user}') AND table_name IN ('KNOWLEDGE_BASE', 'AGENT_TICKETS_LOG');
"""
            _, out_tbls = run_ssh_sysdba_sql(ssh_host, ssh_user, ssh_key, pdb_clean, check_tables_sql)
            found_tables = [line.strip() for line in out_tbls.splitlines() if line.strip() in ("KNOWLEDGE_BASE", "AGENT_TICKETS_LOG")]

            recreate_tables = True
            if found_tables:
                print(f"  [i] Tablas existentes detectadas en {user}: {', '.join(found_tables)}")
                print("      1) Conservar tablas y datos existentes.")
                print("      2) Eliminar tablas existentes (DROP PURGE) y crearlas limpias desde cero.")
                print("      3) Cancelar instalación.")
                action = input("      Selecciona una opción [1/2/3, por defecto 1]: ").strip()
                if action == "2":
                    print("      Purgando tablas previas por SSH...")
                    drop_sql = f"""
BEGIN
    FOR t IN (SELECT table_name FROM all_tables WHERE owner = UPPER('{user}') AND table_name IN ('KNOWLEDGE_BASE', 'AGENT_TICKETS_LOG')) LOOP
        EXECUTE IMMEDIATE 'DROP TABLE ' || UPPER('{user}') || '.' || t.table_name || ' PURGE';
    END LOOP;
END;
/
"""
                    run_ssh_sysdba_sql(ssh_host, ssh_user, ssh_key, pdb_clean, drop_sql)
                    recreate_tables = True
                elif action == "3":
                    print("      Instalación cancelada por el usuario.")
                    sys.exit(0)
                else:
                    print("      [✓] Conservando tablas y datos existentes.")
                    recreate_tables = False

            if recreate_tables:
                print(f"  Ejecutando DDL de tablas vectoriales en esquema '{user}'...")
                ddl_sql = f"""
ALTER SESSION SET CURRENT_SCHEMA = {user};
CREATE TABLE {user}.knowledge_base (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR2(255) NOT NULL,
    category VARCHAR2(100),
    source_doc VARCHAR2(255),
    content CLOB NOT NULL,
    embedding VECTOR(768, FLOAT32),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE {user}.agent_tickets_log (
    ticket_id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_query CLOB NOT NULL,
    retrieved_docs CLOB,
    top_similarity NUMBER(5, 4),
    generated_answer CLOB,
    escalated NUMBER(1) DEFAULT 0,
    latency_ms NUMBER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""
                ok_ddl, out_ddl = run_ssh_sysdba_sql(ssh_host, ssh_user, ssh_key, pdb_clean, ddl_sql)
                if ok_ddl:
                    print("  [✓] Estructuras vectoriales creadas exitosamente con VECTOR(768, FLOAT32).")
                else:
                    print(f"  [!] Nota en creación de tablas: {out_ddl}")

            print("\n  [4/4] Verificando parámetros de cifrado de red (sqlnet.ora) en DBSystem...")
            fix_sqlnet_cmd = """sudo su - oracle -c '
for f in $(find /u01/app/oracle -name sqlnet.ora 2>/dev/null); do
    if grep -qi "SQLNET.ENCRYPTION_SERVER" "$f"; then
        sed -i "s/SQLNET.ENCRYPTION_SERVER.*=.*/SQLNET.ENCRYPTION_SERVER = ACCEPTED/gI" "$f"
        sed -i "s/SQLNET.CRYPTO_CHECKSUM_SERVER.*=.*/SQLNET.CRYPTO_CHECKSUM_SERVER = ACCEPTED/gI" "$f"
    fi
done
'"""
            run_ssh_command(ssh_host, ssh_user, ssh_key, fix_sqlnet_cmd)
            print("  [✓] sqlnet.ora verificado para permitir conexión Thin de python-oracledb.")

            already_provisioned = True

    print(f"\n  Validando conectividad TCP directa con Oracle 26ai en: {full_dsn}...")
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
        print(f"  [✓] ¡Conexión directa TCP exitosa desde la máquina del agente!")
    except Exception as e:
        print(f"\n  [!] Advertencia: No se pudo conectar directamente por TCP a la base de datos: {e}")
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

    return user, password, full_dsn, wallet_dir, wallet_password, already_provisioned


def execute_sql_initialization(user, password, dsn, wallet_dir=None, wallet_password=None, already_provisioned=False):
    print("\n[3/6] Configuración de Estructuras Vectoriales en Oracle 26ai...")
    if already_provisioned:
        print("  [✓] Estructuras vectoriales y usuario creados previamente vía SSH en el DBSystem.")
        return

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
    user, password, dsn, wallet_dir, wallet_password, already_provisioned = setup_database_config()
    execute_sql_initialization(user, password, dsn, wallet_dir, wallet_password, already_provisioned)
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
    print("================================================================================\n")


if __name__ == "__main__":
    main()
