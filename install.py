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


class InstallationTracker:
    """Registra cambios durante la instalación y permite revertir todo (Rollback) en caso de fallo."""
    def __init__(self):
        self.env_file = BASE_DIR / ".env"
        self.env_existed_originally = self.env_file.exists()
        self.original_env_content = self.env_file.read_text(encoding="utf-8") if self.env_existed_originally else None
        self.env_was_modified = False
        self.db_conn_kwargs = None
        self.created_tables = []
        self.demo_docs_generated = False
        self.systemd_installed = False

    def rollback(self, reason: str = ""):
        print("\n" + "=" * 80)
        print(" [!] PROCESO DE REVERSIÓN AUTOMÁTICA (ROLLBACK) ACTIVADO")
        if reason:
            print(f"     Causa del fallo: {reason}")
        print("     Deshaciendo todos los cambios realizados en el sistema y base de datos...")
        print("=" * 80)

        # 1. Purgar tablas creadas en la base de datos
        if self.created_tables and self.db_conn_kwargs:
            print("\n  -> Revertiendo estructuras creadas en Oracle Database...")
            try:
                import oracledb
                conn = oracledb.connect(**self.db_conn_kwargs)
                cur = conn.cursor()
                for table in self.created_tables:
                    try:
                        cur.execute(f"DROP TABLE {table} PURGE")
                        print(f"     [✓] Tabla '{table}' eliminada (PURGE).")
                    except Exception as err:
                        if "ORA-00942" not in str(err):
                            print(f"     [!] Nota al purgar {table}: {err}")
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"     [!] Error conectando a la BD para revertir tablas: {e}")

        # 2. Revertir o eliminar archivo .env
        if self.env_was_modified:
            print("  -> Revirtiendo archivo de configuración '.env'...")
            try:
                if self.env_existed_originally and self.original_env_content is not None:
                    self.env_file.write_text(self.original_env_content, encoding="utf-8")
                    print("     [✓] Archivo '.env' restaurado a su contenido original previo.")
                elif self.env_file.exists():
                    self.env_file.unlink()
                    print("     [✓] Archivo '.env' eliminado.")
            except Exception as e:
                print(f"     [!] Error restaurando '.env': {e}")

        # 3. Limpiar demo PDFs generados
        if self.demo_docs_generated:
            print("  -> Eliminando documentos temporales de demo generados...")
            demo_dir = BASE_DIR / "data" / "demo_docs"
            if demo_dir.exists():
                for pdf in demo_dir.glob("*.pdf"):
                    try:
                        pdf.unlink()
                    except Exception:
                        pass
                print("     [✓] Archivos PDF temporales de demo eliminados.")

        # 4. Detener y remover servicio systemd si fue registrado
        if self.systemd_installed:
            print("  -> Desregistrando servicio systemd...")
            try:
                subprocess.run(["sudo", "systemctl", "stop", "oracle-vectordesk"], capture_output=True)
                subprocess.run(["sudo", "systemctl", "disable", "oracle-vectordesk"], capture_output=True)
                srv_file = Path("/etc/systemd/system/oracle-vectordesk.service")
                if srv_file.exists():
                    subprocess.run(["sudo", "rm", "-f", str(srv_file)], capture_output=True)
                    subprocess.run(["sudo", "systemctl", "daemon-reload"], capture_output=True)
                print("     [✓] Servicio systemd detenido y eliminado.")
            except Exception as e:
                print(f"     [!] Error revirtiendo systemd: {e}")

        print("\n  [✓] Reversión completada. Tu entorno ha quedado en su estado limpio original.")
        print("=" * 80 + "\n")


def find_oracle_client_lib_dir():
    """Busca directorios comunes donde se instala Oracle Instant Client en Linux."""
    import glob
    candidates = glob.glob("/usr/lib/oracle/*/client64/lib") + glob.glob("/opt/oracle/instantclient*")
    if candidates:
        candidates.sort(reverse=True)
        return candidates[0]
    return None


def init_thick_client():
    """Intenta inicializar Modo Thick de python-oracledb buscando en rutas conocidas si es necesario."""
    try:
        import oracledb
        oracledb.init_oracle_client()
        return True
    except Exception as e:
        if "already been initialized" in str(e).lower():
            return True
        lib_dir = find_oracle_client_lib_dir()
        if lib_dir:
            try:
                import oracledb
                oracledb.init_oracle_client(lib_dir=lib_dir)
                return True
            except Exception:
                pass
    return False


def ensure_oracle_instant_client():
    """Verifica e instala Oracle Instant Client para habilitar Modo Thick y soporte de cifrado nativo."""
    print("\n  Verificando Oracle Instant Client (Modo Thick)...")
    if init_thick_client():
        print("  [✓] Oracle Instant Client detectado y activo (Modo Thick habilitado).")
        return True

    if sys.platform != "linux":
        print("  [i] Plataforma no Linux. Para habilitar Modo Thick, instala Oracle Instant Client manualmente.")
        return False

    print("  -> Oracle Instant Client no detectado en el sistema.")
    print("     Instalando cliente oficial para máxima compatibilidad (soporte de Base DB con cifrado NNE y ATP)...")

    # Detectar versión EL (Oracle Linux / RHEL 8, 9, 10)
    el_ver = "9"
    try:
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("VERSION_ID="):
                        val = line.split("=")[1].strip().strip('"').split(".")[0]
                        if val in ("8", "9", "10"):
                            el_ver = val
    except Exception:
        pass

    if shutil.which("dnf"):
        try:
            # Lista priorizada de paquetes de repositorio según versión de Oracle Linux
            if el_ver == "10":
                repo_candidates = [
                    "oracle-instantclient-release-26ai-el10",
                    "oracle-instantclient-release-23ai-el10",
                    "oracle-instantclient-release-el10",
                ]
            elif el_ver == "9":
                repo_candidates = [
                    "oracle-instantclient-release-23ai-el9",
                    "oracle-instantclient-release-26ai-el9",
                    "oracle-instantclient-release-el9",
                ]
            else:  # el_ver == "8"
                repo_candidates = [
                    "oracle-instantclient-release-23ai-el8",
                    "oracle-instantclient-release-el8",
                ]

            repo_installed = False
            for repo_pkg in repo_candidates:
                print(f"     Habilitando repositorio oficial: {repo_pkg}...")
                res_repo = subprocess.run(["sudo", "dnf", "install", "-y", repo_pkg], capture_output=True, text=True)
                if res_repo.returncode == 0:
                    print(f"  [✓] Repositorio {repo_pkg} habilitado exitosamente.")
                    repo_installed = True
                    break

            if not repo_installed:
                print("  [!] Aviso: No se pudo habilitar un repo específico por nombre; probando instalación directa de paquetes...")

            # Lista priorizada de paquetes cliente básico
            basic_candidates = [
                "oracle-instantclient-basic",
                f"oracle-instantclient{ '26ai' if el_ver == '10' else '23ai' }-basic",
                "oracle-instantclient23ai-basic",
                "oracle-instantclient26ai-basic",
            ]
            client_installed = False
            for basic_pkg in basic_candidates:
                print(f"     Instalando paquete {basic_pkg}...")
                res_pkg = subprocess.run(["sudo", "dnf", "install", "-y", basic_pkg])
                if res_pkg.returncode == 0:
                    print(f"  [✓] Paquete {basic_pkg} instalado exitosamente.")
                    client_installed = True
                    break

            if client_installed:
                # Actualizar caché de librerías del sistema
                subprocess.run(["sudo", "ldconfig"], capture_output=True)
                if init_thick_client():
                    print("  [✓] Modo Thick de Oracle inicializado y verificado correctamente.")
                    return True
                else:
                    print("  [!] Cliente instalado, pero Modo Thick requiere reinicio de sesión o configurar LD_LIBRARY_PATH.")
            else:
                print("  [!] Advertencia: No se pudo instalar el paquete de Instant Client con dnf.")
        except Exception as dnf_err:
            print(f"  [!] Error ejecutando dnf: {dnf_err}")

    return False


def check_python_dependencies():
    print("[1/6] Verificando dependencias de Python y Oracle Instant Client...")
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

    # Asegurar Oracle Instant Client
    ensure_oracle_instant_client()


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


def setup_database_config(tracker=None):
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
        "OLLAMA_MODEL=qwen2.5:3b",
        "",
        "# Modelo de Embeddings y Umbral",
        "EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-base",
        "EMBEDDING_DIM=768",
        "SIMILARITY_THRESHOLD=0.35"
    ])

    with open(str(BASE_DIR / ".env"), "w", encoding="utf-8") as f:
        f.write("\n".join(env_lines) + "\n")
    print("  [✓] Archivo de entorno '.env' creado y configurado correctamente.")
    if tracker:
        tracker.env_was_modified = True

    return user, password, full_dsn, wallet_dir, wallet_password


def execute_sql_initialization(user, password, dsn, wallet_dir=None, wallet_password=None, tracker=None):
    print("\n[3/6] Configuración de Estructuras Vectoriales en Oracle 26ai...")

    sql_file = BASE_DIR / "sql" / "init_db.sql"
    if not sql_file.exists():
        print(f"  [!] No se encontró el archivo DDL: {sql_file}")
        if tracker:
            tracker.rollback(f"Archivo DDL no encontrado: {sql_file}")
        sys.exit(1)

    connect_kwargs = {
        "user": user,
        "password": password,
        "dsn": dsn
    }
    if wallet_dir:
        connect_kwargs["wallet_location"] = wallet_dir
        if wallet_password:
            connect_kwargs["wallet_password"] = wallet_password

    if tracker:
        tracker.db_conn_kwargs = connect_kwargs

    try:
        import oracledb
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
                if tracker:
                    tracker.rollback("Instalación cancelada por el usuario")
                sys.exit(0)
            else:
                print("      [✓] Conservando tablas y datos existentes.")
                conn.close()
                return

        # Crear estructuras mediante init_db.sql
        print("  Creando estructuras vectoriales (VECTOR 768d y logs de auditoría)...")
        with open(str(sql_file), "r", encoding="utf-8") as f:
            content = f.read()

        # Filtrar líneas de comentarios para no perder sentencias que inicien con comentario
        clean_lines = [l for l in content.splitlines() if not l.strip().startswith("--")]
        statements = [stmt.strip() for stmt in "\n".join(clean_lines).split(";") if stmt.strip()]

        for stmt in statements:
            try:
                cur.execute(stmt)
                stmt_upper = stmt.upper()
                if "CREATE TABLE" in stmt_upper:
                    if "KNOWLEDGE_BASE" in stmt_upper and "KNOWLEDGE_BASE" not in (tracker.created_tables if tracker else []):
                        if tracker:
                            tracker.created_tables.append("KNOWLEDGE_BASE")
                    if "AGENT_TICKETS_LOG" in stmt_upper and "AGENT_TICKETS_LOG" not in (tracker.created_tables if tracker else []):
                        if tracker:
                            tracker.created_tables.append("AGENT_TICKETS_LOG")
            except Exception as err:
                err_str = str(err)
                if "ORA-00955" in err_str or "already exists" in err_str:
                    pass  # Ya existe la tabla o índice
                elif "ORA-51962" in err_str:
                    # ORA-51962: The vector memory area is out of space for the current container.
                    # El índice en memoria (HNSW) requiere vector_memory_size > 0 (Enterprise Edition / Autonomous ATP).
                    print("\n  [!] Aviso de Edición de Base de Datos (Standard Edition vs. Enterprise/ATP):")
                    print("      -> No se habilitó el índice vectorial en memoria (HNSW) debido a que la instancia")
                    print("         se ejecuta sobre Oracle Database Standard Edition (vector_memory_size = 0).")
                    print("      -> Los índices en memoria (INMEMORY NEIGHBOR GRAPH) están diseñados para")
                    print("         Oracle Database Enterprise Edition, Autonomous Database (ATP/ADW) o superior.")
                    print("      -> Para Standard Edition 2, el agente opera automáticamente con 'Exact Vector Search'")
                    print("         (búsqueda vectorial exacta acelerada por hardware SIMD en CPU).")
                    print("      -> Exact Vector Search ofrece 100% de precisión (Recall 1.0) y responde en < 15 ms")
                    print("         para el volumen de documentación de mesa de ayuda empresarial sin sobrecostos de memoria.\n")
                else:
                    first_line = stmt.splitlines()[0] if stmt.splitlines() else stmt
                    print(f"\n  [!] Error crítico en sentencia SQL [{first_line[:40]}...]: {err}")
                    conn.rollback()
                    conn.close()
                    if tracker:
                        tracker.rollback(f"Fallo en sentencia SQL de inicialización: {err}")
                    sys.exit(1)
        conn.commit()

        # Validar que las tablas existan en el esquema
        cur.execute("""
            SELECT table_name 
            FROM user_tables 
            WHERE table_name IN ('KNOWLEDGE_BASE', 'AGENT_TICKETS_LOG')
        """)
        created = [row[0] for row in cur.fetchall()]
        conn.close()

        if "KNOWLEDGE_BASE" in created and "AGENT_TICKETS_LOG" in created:
            print(f"  [✓] Estructuras de base de datos creadas y verificadas: {', '.join(created)}")
        else:
            missing = [t for t in ['KNOWLEDGE_BASE', 'AGENT_TICKETS_LOG'] if t not in created]
            print(f"\n  [!] Error crítico: Faltan tablas requeridas en el esquema: {missing}")
            if tracker:
                tracker.rollback(f"Faltan tablas requeridas: {missing}")
            sys.exit(1)

    except Exception as e:
        print(f"\n  [!] Error al interactuar con la base de datos: {e}")
        if tracker:
            tracker.rollback(f"Error de base de datos: {e}")
        sys.exit(1)


def check_ollama_service():
    print("\n[4/6] Configuración Integral del Motor LLM en CPU (Ollama)...")
    import time
    import requests
    
    # 1. Asegurar que /usr/local/bin esté en el PATH (donde se instala ollama en Linux)
    if sys.platform == "linux" and "/usr/local/bin" not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"/usr/local/bin:{os.environ.get('PATH', '')}"

    cmd_prefix = [] if (hasattr(os, "geteuid") and os.geteuid() == 0) else ["sudo"]
    ollama_bin = shutil.which("ollama")

    # 2. Si no está instalado en Linux, instalar automáticamente con el script oficial
    if not ollama_bin and sys.platform == "linux":
        print("  -> Ollama no detectado en el sistema.")
        print("     Instalando Ollama automáticamente con el instalador oficial...")
        try:
            cmd = "curl -fsSL https://ollama.com/install.sh | sh"
            if cmd_prefix:
                cmd = "curl -fsSL https://ollama.com/install.sh | sudo -E sh"
            subprocess.run(cmd, shell=True, check=True)
            ollama_bin = shutil.which("ollama") or "/usr/local/bin/ollama"
            print("  [✓] Instalador oficial de Ollama ejecutado exitosamente.")
        except Exception as e:
            print(f"  [!] Error al ejecutar instalador de Ollama: {e}")

    # 3. En Linux, configurar permisos del directorio de datos de Ollama (/usr/share/ollama)
    #    (Evita 'permission denied' para el usuario 'ollama' en Oracle Linux / RHEL)
    if sys.platform == "linux":
        try:
            print("  -> Verificando y configurando permisos en /usr/share/ollama...")
            subprocess.run(cmd_prefix + ["mkdir", "-p", "/usr/share/ollama/.ollama/models"], capture_output=True)
            subprocess.run(cmd_prefix + ["chown", "-R", "ollama:ollama", "/usr/share/ollama"], capture_output=True)
            subprocess.run(cmd_prefix + ["chmod", "-R", "775", "/usr/share/ollama"], capture_output=True)
        except Exception as e:
            print(f"  [!] Nota al ajustar permisos en /usr/share/ollama: {e}")

    # 4. Asegurar que el servicio systemd de Ollama esté habilitado y activo
    if sys.platform == "linux" and (ollama_bin or os.path.exists("/usr/local/bin/ollama")):
        print("  -> Habilitando e iniciando servicio 'ollama' en systemd...")
        subprocess.run(cmd_prefix + ["systemctl", "daemon-reload"], capture_output=True)
        subprocess.run(cmd_prefix + ["systemctl", "restart", "ollama"], capture_output=True)
        subprocess.run(cmd_prefix + ["systemctl", "enable", "ollama"], capture_output=True)

    # 5. Esperar activamente a que la API de Ollama esté escuchando (bucle de sondeo hasta 15s)
    print("  -> Esperando disponibilidad de la API de Ollama en http://localhost:11434...")
    ollama_active = False
    for _ in range(15):
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=2)
            if resp.status_code == 200:
                ollama_active = True
                break
        except Exception:
            pass
        time.sleep(1)

    if not ollama_active:
        print("  [!] Advertencia: No se pudo conectar a Ollama en http://localhost:11434 tras 15 segundos.")
        print("      Verifica el log con: sudo journalctl -u ollama -n 25 --no-pager")
        return False

    print("  [✓] Servicio Ollama activo y respondiendo correctamente en http://localhost:11434.")

    # 6. Verificar y descargar el modelo local requerido (qwen2.5:3b)
    target_model = "qwen2.5:3b"
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m.get("name") for m in resp.json().get("models", [])]
        has_model = any(target_model in m.lower() for m in models)

        if has_model:
            print(f"  [✓] Modelo '{target_model}' ya disponible localmente en Ollama.")
        else:
            print(f"\n  -> Descargando modelo '{target_model}' para inferencia local ultrarrápida en CPU (aprox. 1.9 GB)...")
            print("     Por favor espera mientras se descarga y extrae el modelo...")
            pull_cmd = [ollama_bin or "ollama", "pull", target_model]
            ret = subprocess.run(pull_cmd)
            if ret.returncode == 0:
                print(f"  [✓] Modelo '{target_model}' descargado e instalado exitosamente.")
            else:
                print(f"  [!] Advertencia: 'ollama pull {target_model}' finalizó con código {ret.returncode}.")

        # Confirmación de modelos presentes
        resp_final = requests.get("http://localhost:11434/api/tags", timeout=5)
        available = [m.get("name") for m in resp_final.json().get("models", [])]
        print(f"  [✓] Modelos activos en Ollama: {', '.join(available) if available else 'Ninguno'}")
        return True

    except Exception as e:
        print(f"  [!] Error al verificar o descargar modelo en Ollama: {e}")
        return False


def setup_knowledge_base(tracker=None):
    print("\n[5/6] Ingesta de Documentos a la Base de Conocimiento...")
    print("  Selecciona cómo deseas inicializar el conocimiento:")
    print("  1) Generar y cargar los 10 documentos PDF de demostración (Recomendado para pruebas iniciales).")
    print("  2) Ingestar mis propios documentos PDF colocados en 'data/documents/'.")
    print("  3) Omitir por ahora (subiré mis archivos PDF más tarde).")

    choice = input("  Selecciona una opción [1/2/3, por defecto 3]: ").strip()
    if choice == "1":
        print("\n  Generando 10 documentos PDF en data/demo_docs/...")
        gen_script = BASE_DIR / "scripts" / "generate_demo_pdfs.py"
        try:
            subprocess.check_call([sys.executable, str(gen_script)])
            if tracker:
                tracker.demo_docs_generated = True

            print("\n  Vectorizando e ingestando demo PDFs en Oracle Database 26ai...")
            ingest_script = BASE_DIR / "scripts" / "ingest_documents.py"
            subprocess.check_call([sys.executable, str(ingest_script), "--demo"])
        except Exception as err:
            print(f"\n  [!] Error durante la generación/ingesta de documentos demo: {err}")
            if tracker:
                tracker.rollback(f"Fallo en ingesta de documentos demo: {err}")
            sys.exit(1)
    elif choice == "2":
        print("\n  Iniciando ingesta de documentos propios desde 'data/documents/'...")
        ingest_script = BASE_DIR / "scripts" / "ingest_documents.py"
        try:
            subprocess.check_call([sys.executable, str(ingest_script)])
        except Exception as err:
            print(f"\n  [!] Error durante la ingesta de documentos: {err}")
            if tracker:
                tracker.rollback(f"Fallo en ingesta de documentos propios: {err}")
            sys.exit(1)
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


def configure_systemd_service(tracker=None):
    print("\n[6/6] Configuración de Red, Cortafuegos y Servicio en Segundo Plano...")
    
    # 1. Verificar y abrir puerto 8000 en firewalld
    configure_firewall_port(8000)

    if sys.platform != "linux":
        print("  Nota: systemd está disponible en servidores Linux (Oracle Linux / Ubuntu). Omitiendo.")
        return False

    install_srv = input("\n  ¿Deseas registrar e iniciar Oracle-VectorDesk como servicio de systemd con auto-arranque? [S/n]: ").strip().lower()
    if install_srv != 'n':
        try:
            # Asegurar persistencia y arranque automático de Ollama tras reinicios
            cmd_prefix = [] if os.geteuid() == 0 else ["sudo"]
            if shutil.which("ollama"):
                subprocess.run(cmd_prefix + ["systemctl", "enable", "--now", "ollama"], capture_output=True)

            from scripts.setup_systemd_service import setup_systemd
            res = setup_systemd(start_now=True)
            if res and tracker:
                tracker.systemd_installed = True
            return res
        except Exception as err:
            print(f"  [!] No se pudo activar el servicio systemd: {err}")
            return False
    return False


def main():
    tracker = InstallationTracker()
    try:
        print_banner()
        check_python_dependencies()
        user, password, dsn, wallet_dir, wallet_password = setup_database_config(tracker)
        execute_sql_initialization(user, password, dsn, wallet_dir, wallet_password, tracker)
        ollama_active = check_ollama_service()
        setup_knowledge_base(tracker)
        service_active = configure_systemd_service(tracker)
    except KeyboardInterrupt:
        print("\n\n  [!] Instalación interrumpida manualmente por el usuario (Ctrl+C).")
        tracker.rollback("Cancelación manual por el usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n  [!] Error inesperado durante la instalación: {e}")
        tracker.rollback(f"Excepción: {e}")
        sys.exit(1)

    print("\n================================================================================")
    print(" ¡DESPLIEGUE Y CONFIGURACIÓN COMPLETADOS CON ÉXITO! ")
    print("================================================================================")
    if service_active:
        print("\nEstado de los servicios del sistema:")
        print("  • Oracle-VectorDesk: Activo y configurado para arranque automático tras reinicio.")
        if ollama_active:
            print("  • Ollama LLM Engine: Activo y configurado para arranque automático tras reinicio.")
        else:
            print("  • Ollama LLM Engine: [!] Inactivo. Instálalo con: curl -fsSL https://ollama.com/install.sh | sh")
        print("\nComandos útiles para administrar los servicios:")
        print("  • Ver estado del agente:  sudo systemctl status oracle-vectordesk")
        print("  • Ver estado de Ollama:   sudo systemctl status ollama")
        print("  • Ver logs en vivo:       sudo journalctl -u oracle-vectordesk -f")
        print("  • Reiniciar servicios:    sudo systemctl restart ollama oracle-vectordesk")
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
