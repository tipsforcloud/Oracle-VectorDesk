"""
Punto de Entrada para Iniciar el Servidor de Oracle-VectorDesk
Ejecutar con: python3 run.py
"""

import sys
import uvicorn

if __name__ == "__main__":
    print("================================================================================")
    print(" INICIANDO ORACLE-VECTORDESK - BACKEND API (FASTAPI) ")
    print("================================================================================")
    uvicorn.run("src.agent:app", host="0.0.0.0", port=8000, reload=False)
