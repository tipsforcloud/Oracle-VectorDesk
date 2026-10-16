#!/usr/bin/env python3
"""
Acceso Directo a la Consola de Chat Interactiva de Oracle-VectorDesk
Ejecutar con: python3 chat.py
"""

import sys
import os

# Asegurar que el directorio raíz y scripts estén en el PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from scripts.chat_cli import main

if __name__ == "__main__":
    main()
