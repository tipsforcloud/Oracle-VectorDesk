#!/usr/bin/env python3
"""
Configurador del Servicio en Segundo Plano (systemd)
Instala y activa Oracle-VectorDesk como un servicio persistente del sistema operativo.
"""

import os
import sys
import shutil
import getpass
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def setup_systemd(start_now: bool = True):
    if sys.platform != "linux":
        print(f"Aviso: systemd solo está disponible en sistemas Linux (detectado: {sys.platform}).")
        return False

    if not shutil.which("systemctl"):
        print("Aviso: 'systemctl' no está disponible en este sistema operativo.")
        return False

    current_user = getpass.getuser()
    python_bin = sys.executable
    work_dir = str(BASE_DIR)

    service_name = "oracle-vectordesk.service"
    service_dest = Path("/etc/systemd/system") / service_name

    unit_content = f"""[Unit]
Description=Oracle-VectorDesk AI Support Agent (FastAPI + Oracle Database 26ai)
Documentation=https://github.com/tipsforcloud/Oracle-VectorDesk
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User={current_user}
WorkingDirectory={work_dir}
ExecStart={python_bin} {work_dir}/run.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""

    print(f"\nGenerando unidad systemd para '{service_name}'...")
    print(f"  Usuario:          {current_user}")
    print(f"  Directorio:       {work_dir}")
    print(f"  Binario Python:   {python_bin}")
    print(f"  Ruta de Servicio: {service_dest}")

    # Escribir el archivo en /etc/systemd/system (usar sudo si es necesario)
    try:
        if os.geteuid() == 0:
            with open(service_dest, "w", encoding="utf-8") as f:
                f.write(unit_content)
        else:
            temp_file = BASE_DIR / "service" / service_name
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(unit_content)
            subprocess.run(["sudo", "mv", str(temp_file), str(service_dest)], check=True)

        # Recargar daemon
        cmd_prefix = [] if os.geteuid() == 0 else ["sudo"]
        subprocess.run(cmd_prefix + ["systemctl", "daemon-reload"], check=True)
        print("  [✓] systemctl daemon-reload ejecutado.")

        if start_now:
            subprocess.run(cmd_prefix + ["systemctl", "enable", "--now", service_name], check=True)
            print(f"  [✓] Servicio '{service_name}' habilitado y arrancado en segundo plano.")
            
            # Verificar estado
            status = subprocess.run(["systemctl", "is-active", service_name], capture_output=True, text=True)
            state = status.stdout.strip()
            print(f"  [✓] Estado actual del servicio: {state.upper()}")

        print("\nComandos útiles para administrar el servicio:")
        print(f"  • Ver estado:     sudo systemctl status {service_name}")
        print(f"  • Ver logs en vivo: sudo journalctl -u {service_name} -f")
        print(f"  • Reiniciar:      sudo systemctl restart {service_name}")
        print(f"  • Detener:        sudo systemctl stop {service_name}")
        return True

    except Exception as e:
        print(f"Error al configurar el servicio systemd: {e}")
        return False


if __name__ == "__main__":
    setup_systemd(start_now=True)
