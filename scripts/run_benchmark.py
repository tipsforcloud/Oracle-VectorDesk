"""
Script de Evaluación y Benchmark del Agente RAG en Oracle Database 26ai
Ejecuta las 20 preguntas de prueba contra la API de soporte y genera
un informe detallado con tiempos de inferencia, similitud vectorial y calidad de respuesta.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path

# Agregar raíz al sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config import BENCHMARK_FILE

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1/support/resolve")


def run_benchmark(limit=None):
    if not os.path.exists(str(BENCHMARK_FILE)):
        print(f"Error: No se encontró el archivo de benchmark: {BENCHMARK_FILE}")
        sys.exit(1)

    with open(str(BENCHMARK_FILE), "r", encoding="utf-8") as f:
        questions = json.load(f)

    if limit:
        questions = questions[:limit]

    print("================================================================================")
    print(" INICIO DE EVALUACIÓN BENCHMARK - AGENTE RAG EN ORACLE DATABASE 26ai ")
    print("================================================================================")
    print(f"Endpoint de evaluación: {API_URL}")
    print(f"Total de preguntas a evaluar: {len(questions)}\n")

    results = []
    total_time_ms = 0
    resolved_count = 0
    escalated_count = 0

    for item in questions:
        q_id = item["id"]
        code = item["doc_code"]
        topic = item["topic"]
        query = item["question"]

        print(f"--------------------------------------------------------------------------------")
        print(f"[{q_id}/{len(questions)}] [{code}] Tema: {topic}")
        print(f"Pregunta: {query}")

        payload = {
            "ticket_id": f"BENCH-{q_id:03d}",
            "user_query": query,
            "category": topic
        }

        start_req = time.time()
        try:
            resp = requests.post(API_URL, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  -> ERROR de conexión al endpoint: {e}")
            continue

        latency_ms = data.get("execution_time_ms", int((time.time() - start_req) * 1000))
        total_time_ms += latency_ms
        score = data.get("confidence_score", 0.0)
        resolution = data.get("suggested_resolution", "")
        sources = data.get("sources", [])

        is_escalated = "Se escala a un agente humano" in resolution
        if is_escalated:
            escalated_count += 1
            status_tag = "🔴 ESCALADO A HUMANO (Sin contexto)"
        else:
            resolved_count += 1
            status_tag = "🟢 AUTO-RESUELTO CON RAG"

        print(f"Resultado: {status_tag} | Similitud: {score:.4f} | Tiempo: {latency_ms:,} ms")
        if sources:
            source_titles = [f"{s.get('title')} ({s.get('similarity', 0):.2f})" for s in sources]
            print(f"Fuentes Oracle 26ai: {' | '.join(source_titles)}")
        print(f"\nRespuesta generada:\n{resolution}\n")

        results.append({
            "id": q_id,
            "code": code,
            "topic": topic,
            "status": "resolved" if not is_escalated else "escalated",
            "score": score,
            "latency_ms": latency_ms
        })

    avg_time = int(total_time_ms / len(results)) if results else 0
    print("================================================================================")
    print(" RESUMEN EJECUTIVO DEL BENCHMARK")
    print("================================================================================")
    print(f"Total Evaluados: {len(results)}")
    print(f"Auto-Resueltos con Éxito (RAG): {resolved_count}")
    print(f"Escalados a Humano: {escalated_count}")
    print(f"Latencia Promedio: {avg_time:,} ms por ticket (Inferencia en CPU)")
    print("================================================================================\n")


if __name__ == "__main__":
    limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_benchmark(limit=limit_arg)
