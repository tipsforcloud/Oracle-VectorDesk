#!/usr/bin/env python3
"""
Oracle-VectorDesk - Consola Interactiva de Chat (Terminal)
Permite interactuar en tiempo real con el Agente de Soporte RAG y visualizar
la respuesta generada, fuentes citadas de Oracle Database 26ai y métricas de inferencia.

Uso:
    python3 scripts/chat_cli.py
    python3 scripts/chat_cli.py --url http://10.0.0.5:8000
    python3 chat.py
"""

import sys
import os
import time
import argparse
import itertools
import threading
import requests
from typing import Optional, Dict, Any

# Habilitar soporte ANSI en terminales Windows
if os.name == 'nt':
    os.system('')
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Códigos de Color ANSI
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
WHITE = "\033[37m"
BG_DARK = "\033[48;5;236m"


class Spinner:
    """Animación simple en consola mientras el modelo procesa la consulta."""
    def __init__(self, message: str = "Consultando Oracle 26ai e infiriendo con LLM..."):
        self.message = message
        self.stop_running = False
        self.thread = None

    def _spin(self):
        spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        for char in itertools.cycle(spinner_chars):
            if self.stop_running:
                break
            sys.stdout.write(f"\r{CYAN}{char}{RESET} {self.message}")
            sys.stdout.flush()
            time.sleep(0.08)
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self.stop_running = False
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_running = True
        if self.thread:
            self.thread.join()


def print_banner(api_url: str, health_info: Optional[Dict[str, Any]] = None):
    """Imprime el banner inicial con estado del sistema."""
    terminal_width = min(os.get_terminal_size().columns if hasattr(os, 'get_terminal_size') else 80, 80)
    line = "═" * terminal_width

    print(f"\n{CYAN}{BOLD}{line}{RESET}")
    print(f"{CYAN}{BOLD}   ORACLE-VECTORDESK  |  Consola de Demostración & Chat RAG{RESET}")
    print(f"{DIM}   Oracle Database 26ai AI Vector Search + Local LLM Inference{RESET}")
    print(f"{CYAN}{BOLD}{line}{RESET}")

    if health_info:
        status_color = GREEN if health_info.get("status") == "ok" else YELLOW
        print(f" {BOLD}API Endpoint:{RESET}    {api_url}")
        print(f" {BOLD}Estado Servidor:{RESET} {status_color}{health_info.get('status', 'desconocido').upper()}{RESET}")
        print(f" {BOLD}Base de Datos:{RESET}   {health_info.get('database', 'N/A')}")
        print(f" {BOLD}Embedding Model:{RESET} {health_info.get('embedding_model', 'N/A')}")
        print(f" {BOLD}Modelo LLM:{RESET}      {health_info.get('llm_model', 'N/A')}")
    else:
        print(f" {BOLD}API Endpoint:{RESET}    {api_url} {YELLOW}(Sin conexión o pendiente de verificación){RESET}")

    print(f"{CYAN}{DIM}{line}{RESET}")
    print(f" {DIM}Comandos especiales: 'exit' o 'salir' para terminar | 'clear' para limpiar | 'ticket <id>'{RESET}")
    print(f"{CYAN}{DIM}{line}{RESET}\n")


def check_api_health(api_url: str) -> Optional[Dict[str, Any]]:
    """Verifica si la API REST está activa respondiendo en /health."""
    try:
        r = requests.get(f"{api_url.rstrip('/')}/health", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def format_response_box(resp: Dict[str, Any]):
    """Formatea la respuesta del agente con colores, fuentes y métricas de telemetría."""
    resolution = resp.get("suggested_resolution", "")
    confidence = resp.get("confidence_score", 0.0)
    sources = resp.get("sources", [])
    exec_time = resp.get("execution_time_ms", 0)
    tokens_gen = resp.get("tokens_generated")
    tokens_sec = resp.get("tokens_per_second")
    ticket_id = resp.get("ticket_id", "N/A")

    # Determinar etiqueta de confianza y color
    if confidence >= 0.70:
        conf_label = f"{GREEN}● ALTA ({confidence * 100:.1f}%){RESET}"
    elif confidence >= 0.50:
        conf_label = f"{YELLOW}▲ MEDIA ({confidence * 100:.1f}%){RESET}"
    else:
        conf_label = f"{RED}▼ BAJA ({confidence * 100:.1f}% - Escalamiento){RESET}"

    # Encabezado del Agente
    print(f"\n{MAGENTA}{BOLD}🤖 Agente de Soporte [Ticket: {ticket_id}] {RESET}| Confianza: {conf_label}")
    print(f"{DIM}{'─' * 70}{RESET}")

    # Cuerpo de la respuesta
    print(f"{WHITE}{resolution.strip()}{RESET}\n")

    # Fuentes citadas
    if sources:
        print(f"{BLUE}{BOLD}📚 Fuentes Citadas (Oracle Database 26ai):{RESET}")
        for src in sources:
            sim = src.get("similarity", 0.0) * 100
            title = src.get("title", "Desconocido")
            print(f"   {CYAN}▸{RESET} {BOLD}{title}{RESET} {DIM}(Similitud: {sim:.1f}%){RESET}")
        print()

    # Telemetría de Rendimiento
    telemetry_parts = [f"⏱  Tiempo: {exec_time} ms"]
    if tokens_gen is not None and tokens_gen > 0:
        telemetry_parts.append(f"🔢 Tokens: {tokens_gen}")
    if tokens_sec is not None and tokens_sec > 0:
        telemetry_parts.append(f"⚡ Velocidad: {tokens_sec:.1f} tok/s")

    telemetry_str = " | ".join(telemetry_parts)
    print(f"{DIM}{BG_DARK}  {telemetry_str}  {RESET}")
    print(f"{DIM}{'─' * 70}{RESET}\n")


def chat_loop(api_url: str, initial_ticket_prefix: str = "TCK"):
    """Bucle principal e interactivo de chat."""
    api_url = api_url.rstrip('/')
    resolve_endpoint = f"{api_url}/api/v1/support/resolve"

    # Verificar salud inicial
    health = check_api_health(api_url)
    print_banner(api_url, health)

    if not health:
        print(f"{YELLOW}⚠️  Aviso: No se pudo conectar al endpoint {api_url}/health.")
        print(f"Asegúrate de que el backend esté ejecutándose (ej. 'python3 run.py' o servicio systemd).{RESET}\n")

    ticket_counter = 1001
    custom_ticket_id = None

    while True:
        current_ticket = custom_ticket_id if custom_ticket_id else f"{initial_ticket_prefix}-{ticket_counter}"
        try:
            prompt_label = f"{GREEN}{BOLD}Tú [{current_ticket}]{RESET} > "
            user_input = input(prompt_label).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{CYAN}Cerrando sesión de chat. ¡Hasta pronto! 👋{RESET}\n")
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        # Comandos de salida
        if cmd in ["exit", "quit", "salir", ":q"]:
            print(f"\n{CYAN}Cerrando sesión de chat. ¡Hasta pronto! 👋{RESET}\n")
            break

        # Limpiar pantalla
        if cmd in ["clear", "cls", "limpiar"]:
            os.system('cls' if os.name == 'nt' else 'clear')
            print_banner(api_url, check_api_health(api_url))
            continue

        # Comando de ayuda
        if cmd in ["help", "ayuda", "/?"]:
            print(f"\n{YELLOW}{BOLD}Comandos Disponibles:{RESET}")
            print(f"  {BOLD}exit / salir{RESET}    : Terminar la sesión interactiva")
            print(f"  {BOLD}clear / limpiar{RESET} : Limpiar la pantalla de la consola")
            print(f"  {BOLD}ticket <id>{RESET}     : Fijar un ID de ticket específico (ej: ticket INC-9942)")
            print(f"  {BOLD}ticket reset{RESET}    : Volver a la numeración incremental automática")
            print(f"  {BOLD}health / status{RESET} : Consultar el estado del backend y modelos\n")
            continue

        # Comando para fijar ID de ticket
        if cmd.startswith("ticket "):
            arg = user_input.split(" ", 1)[1].strip()
            if arg.lower() == "reset":
                custom_ticket_id = None
                print(f"{CYAN}✓ Numeración de tickets restablecida a automática ({initial_ticket_prefix}-{ticket_counter}){RESET}\n")
            else:
                custom_ticket_id = arg
                print(f"{CYAN}✓ ID de ticket fijado a: '{custom_ticket_id}'{RESET}\n")
            continue

        # Comando para verificar estado
        if cmd in ["health", "status", "estado"]:
            h = check_api_health(api_url)
            print(f"\n{CYAN}{BOLD}Estado del Sistema:{RESET}")
            if h:
                for k, v in h.items():
                    print(f"  • {BOLD}{k}:{RESET} {v}")
            else:
                print(f"  {RED}No responde el endpoint /health en {api_url}{RESET}")
            print()
            continue

        # Enviar consulta al backend RAG
        payload = {
            "ticket_id": current_ticket,
            "user_query": user_input,
            "category": None
        }

        try:
            with Spinner("Consultando Oracle 26ai e infiriendo con LLM..."):
                start_req = time.time()
                resp = requests.post(resolve_endpoint, json=payload, timeout=90)
                client_ms = int((time.time() - start_req) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                format_response_box(data)
                if not custom_ticket_id:
                    ticket_counter += 1
            else:
                print(f"\n{RED}❌ Error del Servidor ({resp.status_code}):{RESET} {resp.text}\n")

        except requests.exceptions.ConnectionError:
            print(f"\n{RED}❌ Error de Conexión:{RESET} No se pudo conectar a '{resolve_endpoint}'.")
            print(f"{DIM}Verifica que el servicio esté corriendo con 'python3 run.py'.{RESET}\n")
        except requests.exceptions.Timeout:
            print(f"\n{RED}❌ Tiempo de espera agotado:{RESET} La inferencia tardó más de 90 segundos.\n")
        except Exception as e:
            print(f"\n{RED}❌ Error inesperado:{RESET} {str(e)}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Consola interactiva de chat para Oracle-VectorDesk (Soporte RAG)."
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("API_URL", "http://localhost:8000"),
        help="URL base de la API de Oracle-VectorDesk (default: http://localhost:8000 o env API_URL)"
    )
    parser.add_argument(
        "--ticket-prefix",
        default="TCK",
        help="Prefijo para la generación automática de IDs de tickets (default: TCK)"
    )
    args = parser.parse_args()

    chat_loop(api_url=args.url, initial_ticket_prefix=args.ticket_prefix)


if __name__ == "__main__":
    main()
