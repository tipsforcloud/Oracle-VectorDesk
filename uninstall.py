#!/usr/bin/env python3
"""
Asistente Interactivo de Desinstalación y Limpieza Completa (Uninstall Wizard)
Oracle-VectorDesk: Enterprise Support & Helpdesk RAG on Oracle Database 26ai

Permite desaprovisionar de forma limpia y controlada:
1. Servicio en segundo plano (systemd: oracle-vectordesk.service)
2. Estructuras / esquemas en Oracle Database 26ai (Base DB VM / Autonomous)
3. Modelos LLM descargados en Ollama (qwen3:4b, qwen2.5, etc.)
4. Servicio y binario de Ollama
5. Archivos de configuración locales (.env y datasets de demo)
"""

import os
import sys
import shutil
import getpass
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Inicializar Modo Thick si Oracle Instant Client está disponible
try:
    import oracledb
    oracledb.init_oracle_client()
except Exception:
    pass


def print_banner():
    print(r"""
================================================================================
   ____                  _        __     __        _             ____            _    
  / __ \                | |       \ \   / /       | |           |  _ \          | |   
 | |  | |_ __ __ _  ___ | | ___    \ \_/ /__  ___ | |_ ___  _ __| | | |___  ___| | __
 | |  | | '__/ _` |/ __|| |/ _ \    \   / _ \/ __|| __/ _ \| '__| | | / _ \/ __| |/ /
 | |__| | | | (_| | (__ | |  __/     | |  __/ (__ | || (_) | |  | |_| |  __/\__ \   < 
  \____/|_|  \__,_|\___||_|\___|     |_|\___|\___| \__\___/|_|  |____/ \___||___/_|\_\\
                                                                                      
      Desinstalador y Desaprovisionamiento Completo (Uninstall Wizard)
      TipsForCloud | 🌐 https://tipsforcloud.com | 📺 https://www.youtube.com/@TipsForCloud
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


def load_local_env():
    """Carga variables del archivo .env si existe."""
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


def uninstall_systemd_service():
    print("\n[1/4] Removiendo Servicio del Sistema Operativo (systemd)...")
    if sys.platform != "linux":
        print("  Nota: systemd no está presente en esta plataforma. Omitiendo.")
        return

    service_name = "oracle-vectordesk.service"
    service_path = Path("/etc/systemd/system") / service_name

    cmd_prefix = [] if os.geteuid() == 0 else ["sudo"]

    try:
        # Detener y deshabilitar
        subprocess.run(cmd_prefix + ["systemctl", "stop", service_name], capture_output=True)
        subprocess.run(cmd_prefix + ["systemctl", "disable", service_name], capture_output=True)
        print(f"  [✓] Servicio '{service_name}' detenido y deshabilitado.")

        if service_path.exists():
            if os.geteuid() == 0:
                service_path.unlink()
            else:
                subprocess.run(["sudo", "rm", "-f", str(service_path)], check=True)
            subprocess.run(cmd_prefix + ["systemctl", "daemon-reload"], capture_output=True)
            print(f"  [✓] Archivo de unidad '{service_path}' eliminado.")
        else:
            print(f"  [i] La unidad '{service_path}' no estaba registrada.")

        # Verificar y cerrar puerto 8000 en firewalld si está abierto
        if shutil.which("firewall-cmd"):
            qp = subprocess.run(cmd_prefix + ["firewall-cmd", "--query-port=8000/tcp"], capture_output=True, text=True)
            if qp.returncode == 0 and "yes" in qp.stdout.lower():
                close_fw = input("\n  ¿Deseas cerrar el puerto 8000/tcp en firewalld? [S/n]: ").strip().lower()
                if close_fw != 'n':
                    subprocess.run(cmd_prefix + ["firewall-cmd", "--permanent", "--remove-port=8000/tcp"], capture_output=True)
                    subprocess.run(cmd_prefix + ["firewall-cmd", "--reload"], capture_output=True)
                    print("  [✓] Puerto 8000/tcp cerrado y firewalld recargado.")
    except Exception as e:
        print(f"  [!] Nota al remover servicio systemd o cortafuegos: {e}")


def clean_oracle_database(env_vars: dict):
    print("\n[2/4] Limpieza de Recursos en Oracle Database 26ai...")
    clean_db = input("  ¿Deseas purgar los recursos creados en Oracle Database? [S/n]: ").strip().lower()
    if clean_db == 'n':
        print("  [i] Limpieza de Base de Datos omitida por el usuario.")
        return

    print("  Selecciona el nivel de limpieza que deseas aplicar:")
    print("  1) Borrar únicamente las tablas de la aplicación (KNOWLEDGE_BASE y AGENT_TICKETS_LOG) [Recomendado]")
    print("  2) Borrar completamente el usuario y esquema de la BD (DROP USER ... CASCADE)")
    print("  3) Omitir")

    action = input("  Opción [1/2/3, por defecto 1]: ").strip()
    if action == "3":
        print("  [i] Limpieza de BD omitida.")
        return

    # Obtener credenciales desde .env o pedir interactivamente
    default_user = env_vars.get("DB_USER", "app_support")
    default_dsn = env_vars.get("DB_DSN", "")
    wallet_dir = env_vars.get("WALLET_DIR", None)
    wallet_password = env_vars.get("WALLET_PASSWORD", None)

    prompt_dsn = "  DSN de Conexión"
    if not default_dsn:
        prompt_dsn += " (ej. dbhost.sub.yourvcn.oraclevcn.com:1521/pdb1.sub.yourvcn.oraclevcn.com)"
    dsn = ask_input(prompt_dsn, default_dsn)

    if action == "2":
        # Opción DROP USER CASCADE ejecutado vía SQL*Net con usuario administrativo
        print("\n  -- Borrado Completo de Usuario (DROP USER CASCADE) --")
        dba_user = ask_input("  Usuario con permisos DBA en la PDB (ej. SYSTEM o ADMIN)", "SYSTEM")
        dba_password = getpass.getpass("  Contraseña del Usuario DBA: ")
        user_to_drop = ask_input("  Usuario a eliminar", default_user)

        confirm = input(f"  ¿Confirmas ejecutar 'DROP USER {user_to_drop} CASCADE' en {dsn}? [s/N]: ").strip().lower()
        if confirm == 's':
            try:
                import oracledb
                connect_kwargs = {
                    "user": dba_user,
                    "password": dba_password,
                    "dsn": dsn
                }
                if wallet_dir:
                    connect_kwargs["wallet_location"] = wallet_dir
                    if wallet_password:
                        connect_kwargs["wallet_password"] = wallet_password

                conn = oracledb.connect(**connect_kwargs)
                cur = conn.cursor()
                cur.execute(f"DROP USER {user_to_drop} CASCADE")
                conn.close()
                print(f"  [✓] Usuario '{user_to_drop}' y sus tablas eliminados exitosamente (CASCADE).")
            except Exception as e:
                print(f"  [!] Error al eliminar usuario por SQL: {e}")
        else:
            print("  Operación de borrado de usuario cancelada.")
        return

    # Opción 1: Borrar tablas KNOWLEDGE_BASE y AGENT_TICKETS_LOG
    print("\n  -- Purga de Tablas Vectoriales --")
    user = ask_input("  Usuario de Base de Datos", default_user)
    password = env_vars.get("DB_PASSWORD", "")
    if not password:
        password = getpass.getpass("  Contraseña del Usuario DB: ")

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
        for t in ["KNOWLEDGE_BASE", "AGENT_TICKETS_LOG"]:
            try:
                cur.execute(f"DROP TABLE {t} PURGE")
                print(f"  [✓] Tabla '{t}' eliminada exitosamente (PURGE).")
            except Exception as e:
                if "ORA-00942" in str(e):
                    print(f"  [i] La tabla '{t}' no existía en el esquema.")
                else:
                    print(f"  [!] Nota al eliminar '{t}': {e}")
        conn.commit()
        conn.close()
        print("  [✓] Base de datos limpia de estructuras de Oracle-VectorDesk.")
    except Exception as e:
        print(f"  [!] No se pudo conectar a la BD para purgar tablas: {e}")


def clean_ollama_and_models(env_vars: dict):
    print("\n[3/4] Gestión de Modelos y Servicio Ollama...")
    
    # 1. Eliminar modelos descargados
    del_models = input("  ¿Deseas eliminar los modelos LLM descargados para el agente (qwen3:4b, etc.)? [S/n]: ").strip().lower()
    if del_models != 'n':
        models_to_check = ["qwen3:4b", "qwen2.5:7b-instruct-q4_K_M", "qwen2.5:3b"]
        for m in models_to_check:
            try:
                res = subprocess.run(["ollama", "rm", m], capture_output=True, text=True)
                if res.returncode == 0:
                    print(f"  [✓] Modelo '{m}' eliminado de Ollama.")
            except Exception:
                pass

    # 2. Desinstalar Ollama por completo
    del_ollama = input("\n  ¿Deseas desinstalar COMPLETAMENTE el servicio y binario de Ollama de esta máquina? [s/N]: ").strip().lower()
    if del_ollama == 's':
        print("  Desinstalando Ollama del sistema operativo...")
        cmd_prefix = [] if os.geteuid() == 0 else ["sudo"]
        
        # Detener servicio
        subprocess.run(cmd_prefix + ["systemctl", "stop", "ollama"], capture_output=True)
        subprocess.run(cmd_prefix + ["systemctl", "disable", "ollama"], capture_output=True)
        
        # Eliminar archivo de servicio
        for srv in ["/etc/systemd/system/ollama.service", "/usr/lib/systemd/system/ollama.service"]:
            if os.path.exists(srv):
                subprocess.run(cmd_prefix + ["rm", "-f", srv], capture_output=True)
        subprocess.run(cmd_prefix + ["systemctl", "daemon-reload"], capture_output=True)

        # Eliminar binarios
        for b in ["/usr/local/bin/ollama", "/usr/bin/ollama"]:
            if os.path.exists(b):
                subprocess.run(cmd_prefix + ["rm", "-f", b], capture_output=True)

        # Eliminar carpetas y cachés
        subprocess.run(cmd_prefix + ["rm", "-rf", "/usr/share/ollama"], capture_output=True)
        user_home = Path.home()
        subprocess.run(cmd_prefix + ["rm", "-rf", str(user_home / ".ollama")], capture_output=True)
        subprocess.run(cmd_prefix + ["rm", "-rf", "/root/.ollama"], capture_output=True)

        print("  [✓] Servicio, binarios y almacenamiento de Ollama eliminados del sistema.")
    else:
        print("  [i] El binario y servicio de Ollama se conservan en la máquina.")


def clean_local_workspace():
    print("\n[4/4] Limpieza de Archivos de Configuración y Temporales...")
    clean_files = input("  ¿Deseas eliminar el archivo de entorno '.env' y PDFs de demostración locales? [S/n]: ").strip().lower()
    if clean_files != 'n':
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            env_file.unlink()
            print("  [✓] Archivo '.env' eliminado.")

        demo_docs = BASE_DIR / "data" / "demo_docs"
        if demo_docs.exists():
            for f in demo_docs.glob("*.pdf"):
                f.unlink()
            print("  [✓] Archivos PDF generados en 'data/demo_docs/' eliminados.")

        # Limpiar __pycache__
        for p in BASE_DIR.rglob("__pycache__"):
            shutil.rmtree(p, ignore_errors=True)
        print("  [✓] Cachés de Python eliminadas.")


def main():
    print_banner()
    print("ADVERTENCIA: Este asistente desinstalará los componentes de Oracle-VectorDesk,")
    print("detendrá servicios y puede eliminar datos y modelos locales.")
    confirm = input("¿Deseas proceder con la desinstalación? [s/N]: ").strip().lower()
    if confirm != 's':
        print("Operación cancelada. No se realizaron cambios en el sistema.")
        sys.exit(0)

    env_vars = load_local_env()

    uninstall_systemd_service()
    clean_oracle_database(env_vars)
    clean_ollama_and_models(env_vars)
    clean_local_workspace()

    print("\n================================================================================")
    print(" ¡DESINSTALACIÓN Y DESAPROVISIONAMIENTO COMPLETADOS CON ÉXITO! ")
    print("================================================================================")
    print("El entorno ha sido restaurado a su estado previo.")
    print("Si deseas eliminar también el código fuente del proyecto, ejecuta:")
    print("  cd .. && rm -rf Oracle-VectorDesk")
    print("\n--------------------------------------------------------------------------------")
    print(" TipsForCloud | 🌐 https://tipsforcloud.com | 📺 https://www.youtube.com/@TipsForCloud")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
