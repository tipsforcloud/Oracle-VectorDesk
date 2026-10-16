# Changelog (Registro de Cambios)

Todos los cambios notables en el proyecto **Oracle-VectorDesk** se documentarán en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] - Planificado para v2.0

### 🚀 Rendimiento, Concurrencia y Escalabilidad sobre Máquinas Virtuales (VMs)

* **Caché Semántico Nativo en Oracle Database 26ai (DBSystem):**
  * Implementación de una tabla dedicada `SEMANTIC_RESPONSE_CACHE` con columna vectorial `QUERY_VECTOR VECTOR(768, FLOAT32)`, respuesta resuelta `CACHED_RESOLUTION CLOB`, contador de aciertos `HIT_COUNT` y fecha de expiración/validez.
  * Flujo de resolución anticipada: Al ingresar una consulta, se realiza una búsqueda de similitud coseno rápida contra la caché. Si la similitud es $\ge 0.95$, la respuesta validada se retorna en **menos de 10 ms** directamente desde el DBSystem de Oracle.
  * **Impacto esperado:** Alivia entre el **60% y el 75%** de la carga de inferencia en mesas de ayuda corporativas (donde las preguntas de soporte de Nivel 1 son altamente repetitivas), reservando la CPU del LLM únicamente para consultas inéditas o complejas.

* **Concurrencia Multi-Usuario en Ollama (`OLLAMA_NUM_PARALLEL`):**
  * Configuración del servicio de inferencia en la VM con `OLLAMA_NUM_PARALLEL=2` o `OLLAMA_NUM_PARALLEL=4`.
  * Habilita a Ollama para procesar múltiples secuencias simultáneas distribuyendo los núcleos de CPU (AMD EPYC / Intel Xeon) y la memoria RAM, eliminando el bloqueo secuencial cuando varios usuarios consultan al mismo tiempo.
  * Parámetros de estabilidad en VM: `OLLAMA_MAX_LOADED_MODELS=1` y `OLLAMA_KEEP_ALIVE=-1` para garantizar permanencia continua en RAM y evitar latencias de re-carga.

* **Connection Pooling en Capa de Datos (`oracledb.create_pool`):**
  * Transición de conexiones efímeras por petición a un pool administrado y reutilizable en memoria (`min=2, max=10, increment=1`).
  * Ahorro de ~50-100 ms de latencia por ticket al suprimir la negociación SSL/TLS y el handshake de autenticación SQL*Net en cada solicitud.

* **Streaming de Respuestas en Tiempo Real (Server-Sent Events / SSE):**
  * Nuevo endpoint `/api/v1/support/resolve/stream` con emisión progresiva token por token conforme el LLM los produce.
  * Reduce la latencia percibida por el usuario final a **< 250 ms** (en lugar de esperar los 3-4 segundos requeridos para la generación completa del párrafo).

* **Afinación de Hilos de CPU (`num_thread`) y KV-Cache:**
  * Asignación dinámica del parámetro `num_thread` en la carga del modelo para saturar de manera óptima los hilos físicos de la VM sin incurrir en penalizaciones por context switching.
  * Acotamiento del buffer de atención (*KV-Cache*) a 2048 tokens para reducir drásticamente el consumo de memoria y acelerar el cálculo de atención cruzada.

* **Búsqueda Híbrida en Oracle 26ai (Hybrid Search con RRF):**
  * Fusión de búsqueda léxica exacta (Oracle Text / BM25 para números de error `ORA-`, códigos de ticket y comandos de terminal) con búsqueda semántica vectorial densa (768d) mediante *Reciprocal Rank Fusion*.

* **Escalamiento Horizontal de Cómputo (Pool de VMs + OCI Load Balancer):**
  * Arquitectura desacoplada: Mantener una única base de datos centralizada (Oracle Database 26ai DBSystem) y desplegar un conjunto elástico de 2 a 4 instancias Compute VM detrás de un **OCI Private Load Balancer**.
  * Permite absorber picos de demanda masivos de cientos de usuarios corporativos simultáneos sin abandonar la arquitectura basada en VMs ni requerir GPU.

---

## [1.0.0] - 2026-10-16

### 🌟 Primer Release Oficial (Initial Production Release)

#### Agregado (Added)
* **Arquitectura RAG Integral sobre Oracle Cloud Infrastructure (OCI):**
  * Búsqueda vectorial nativa con **Oracle Database 26ai AI Vector Search** (`VECTOR(768, FLOAT32)` y `COSINE`).
  * Inferencia de lenguaje completamente local y privada sobre CPU en Compute VM (AMD EPYC) utilizando **Ollama**.
  * Generación de embeddings semánticos densos multilingües con `intfloat/multilingual-e5-base` (768 dimensiones).
* **Selector Multi-Modelo de LLM en Instalador (`install.py`):**
  * Menú interactivo para seleccionar el modelo ideal para la VM:
    * `qwen2.5:3b` (Recomendado para CPU 4 vCPUs / 16 GB RAM).
    * `qwen2.5:7b` (Para instancias con 8+ vCPUs / 32 GB RAM).
    * `llama3.2:3b` (Meta AI ligero).
    * `phi3.5:3.8b` (Microsoft Research).
    * Opción de ingresar modelo personalizado.
* **Detección Inteligente de Saludos y Cortesía Conversacional:**
  * Módulo `is_pure_greeting` con respuesta cálida instantánea (< 5 ms) que evita falsos escalamientos en interacciones de cortesía (*small-talk*).
* **Consola Interactiva de Chat en Terminal (`chat.py` / `scripts/chat_cli.py`):**
  * Cliente interactivo con colores ANSI, animación dinámica de espera (*spinner*), formato limpio de mensajes, visualización de fuentes citadas con porcentaje de similitud y métricas de rendimiento.
  * Soporte de comandos especiales: `exit`, `clear`, `ticket <id>`, `ticket reset` y `status`.
* **Telemetría de Rendimiento en Tiempo Real:**
  * Métrica de velocidad en la API REST y en el cliente: `tokens_generated` y `tokens_per_second`.
* **Control Anti-Alucinación Estricto (Safe Fallback):**
  * Umbral semántico calibrado (`SIMILARITY_THRESHOLD = 0.35`) que deriva automáticamente tickets a agentes humanos si la documentación no respalda la respuesta con certeza.
* **Trazabilidad y Auditoría Transaccional:**
  * Registro de cada interacción, contexto recuperado, confianza y tiempos en la tabla `AGENT_TICKETS_LOG` de Oracle Database 26ai.
* **Automatización y Operaciones:**
  * Script de benchmark con 20 casos de prueba automatizados (`scripts/run_benchmark.py`).
  * Script de ingesta documental de PDFs (`scripts/ingest_documents.py`).
  * Generador de PDFs sintéticos corporativos (`scripts/generate_demo_pdfs.py`).
  * Asistente interactivo de instalación paso a paso (`install.py`).
  * Asistente modular de desinstalación y limpieza (`uninstall.py`).
  * Script de mantenimiento y reinicio de base de datos (`scripts/reset_database.py`).
  * Servicio systemd para ejecución en segundo plano (`scripts/setup_systemd_service.py`).
* **Documentación Completa:**
  * `README.md` exhaustivo con diagramas de flujo y arquitectura.
  * Guía de referencia de API REST con ejemplos en Python, JS y cURL (`docs/api_reference.md`).
  * Guía de despliegue y bitácora técnica de lecciones aprendidas en OCI (`docs/deployment_guide.md`).
