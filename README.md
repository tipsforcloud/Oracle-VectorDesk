# Oracle-VectorDesk 🛡️🤖

[![Oracle Database](https://img.shields.io/badge/Oracle_Database-26ai_|_23ai-F80000?logo=oracle&logoColor=white)](https://www.oracle.com/database/)
[![Oracle Cloud Infrastructure](https://img.shields.io/badge/OCI-Compute_E6_(CPU--only)-F80000?logo=oracle&logoColor=white)](https://cloud.oracle.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/Ollama-Qwen_2.5_7B-000000?logo=ollama&logoColor=white)](https://ollama.com)
[![Embeddings](https://img.shields.io/badge/Embeddings-multilingual--e5--base_(768d)-blue)](https://huggingface.co/intfloat/multilingual-e5-base)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Agente autónomo de soporte técnico empresarial y Helpdesk de Nivel 1** con arquitectura RAG (*Retrieval-Augmented Generation*), impulsado de forma nativa por **Oracle Database 26ai (AI Vector Search)** e inferencia local en CPU sobre **Oracle Cloud Infrastructure (OCI)**. 
> 
> **Ultra bajo costo:** Diseñado para operar por **~\$130 - \$190 USD / mes** sin requerir GPUs costosas.

---

## 🌟 Características Principales

* **"Bring AI to the Data":** Todo el conocimiento corporativo reside y se consulta dentro de Oracle Database 26ai mediante columnas nativas `VECTOR(768, FLOAT32)` y la función `VECTOR_DISTANCE(..., COSINE)`. Los datos sensibles de la empresa nunca viajan a nubes de terceros ni a bases de datos vectoriales externas.
* **100% Inferencia en CPU (Sin GPUs):** Ejecuta **Qwen 2.5 7B Instruct** cuantizado (Q4_K_M) sobre procesadores AMD EPYC en instancias `VM.Standard.E6.Flex`, manteniendo costos fijos y predecibles.
* **Tolerancia Cero a la Alucinación:** Incorpora un umbral estricto de similitud semántica (`similarity < 0.35`). Si la consulta del usuario no tiene respaldo documental comprobado en Oracle, el agente **no inventa** y escala automáticamente el caso a soporte humano.
* **Auditoría Empresarial Nativa:** Cada interacción, latencia en milisegundos, nivel de confianza y contexto recuperado se persiste automáticamente en la tabla `AGENT_TICKETS_LOG`.
* **Dataset Demo Completo:** Incluye un generador de 10 documentos PDF corporativos y una suite automatizada de benchmark con 20 preguntas reales para evaluar precisión y tiempos de respuesta.

---

## 📐 Diagrama de Arquitectura

```mermaid
flowchart TD
    subgraph Canales ["Canales de Entrada"]
        User["Usuario / Mesa de Ayuda / Jira / Slack / Teams"]
    end

    subgraph OCI_VCN ["OCI Virtual Cloud Network (VCN Privada)"]
        subgraph VM_Compute ["OCI Compute E6 (VM.Standard.E6.Flex - 2 OCPUs, 32 GB RAM)"]
            API["API REST Backend (FastAPI / Uvicorn :8000)"]
            EmbedModel["Modelo Embeddings CPU\nintfloat/multilingual-e5-base (768d)"]
            Ollama["Motor LLM en CPU (Ollama)\nqwen2.5:7b-instruct-q4_K_M"]
        end

        subgraph Oracle_DB ["Oracle Database 26ai (Base DB o Autonomous DB Serverless)"]
            KB_Table[("Tabla KNOWLEDGE_BASE\nColumna VECTOR(768, FLOAT32)\nExact Vector Search con SIMD")]
            Audit_Table[("Tabla AGENT_TICKETS_LOG\nAuditoría, Métricas y Tiempos")]
        end
    end

    User -->|POST /api/v1/support/resolve| API
    API -->|1. Vectoriza consulta 'query: ...'| EmbedModel
    EmbedModel -->|Vector float32[768]| API
    API -->|2. SQL con VECTOR_DISTANCE(..., COSINE)| KB_Table
    KB_Table -->|3. Top 3 artículos + similitud| API
    
    API -->|¿Similitud < 0.35?| Escalar["Escalar a Humano (Safe Fallback)"]
    Escalar --> User
    
    API -->|4. Prompt estricto + Contexto recuperado| Ollama
    Ollama -->|5. Respuesta resolutiva precisa| API
    API -->|6. Inserta log de auditoría| Audit_Table
    API -->|7. JSON con respuesta + fuentes| User
```

---

## 🚀 Despliegue Rápido en OCI

### 1. Inicializar la Base de Datos (Oracle Database 26ai)
En tu Pluggable Database (`PDBLAB1`) o Autonomous Database:
```sql
@init_db.sql
```
Esto creará la tabla `KNOWLEDGE_BASE` con la columna vectorial y la tabla de auditoría `AGENT_TICKETS_LOG`.

### 2. Configurar la Instancia Compute en OCI (Oracle Linux 10)
```bash
# Actualizar e instalar dependencias base
sudo dnf update -y
sudo dnf install -y python3 python3-pip git curl

# Instalar Ollama y descargar el modelo optimizado para CPU
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b-instruct-q4_K_M

# Abrir el puerto 8000 en el firewall del sistema operativo
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### 3. Clonar y Configurar el Proyecto
```bash
git clone https://github.com/tipsforcloud/Oracle-VectorDesk.git
cd Oracle-VectorDesk

# Instalar PyTorch CPU ligero primero (evita descargar 4 GB de CUDA innecesarios)
pip3 install --break-system-packages torch --index-url https://download.pytorch.org/whl/cpu

# Instalar librerías de la aplicación
pip3 install --break-system-packages -r requirements.txt
pip3 install --break-system-packages reportlab pypdf

# Configurar variables de conexión
cp .env.example .env
nano .env
```

### 4. Generar Documentos e Ingestar en Oracle 26ai
```bash
# 1. Genera 10 PDFs de prueba con políticas corporativas realistas
python3 generate_sample_pdfs.py

# 2. Vectoriza e inserta los PDFs en Oracle Database 26ai
python3 ingest_pdfs.py
```

### 5. Iniciar el Backend API
```bash
python3 agent.py
```

---

## 🧪 Pruebas y Validación

### Probar Salud del Servicio
```bash
curl http://localhost:8000/health
```
```json
{
  "status": "ok",
  "database": "Oracle Database 26ai AI Vector Search",
  "embedding_model": "intfloat/multilingual-e5-base (768 dims)",
  "llm_model": "qwen2.5:7b-instruct-q4_K_M"
}
```

### Resolver un Ticket Real
```bash
curl -X POST http://localhost:8000/api/v1/support/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TCK-1001",
    "user_query": "¿Cuál es la línea telefónica y el código PIN de emergencia para activar la guardia de soporte crítico fuera de horario?"
  }'
```

*Respuesta:*
```json
{
  "ticket_id": "TCK-1001",
  "user_query": "¿Cuál es la línea telefónica y el código PIN de emergencia para activar la guardia de soporte crítico fuera de horario?",
  "suggested_resolution": "Para activar la guardia de soporte crítico en incidentes de Severidad 1 (P1) fuera de horario, se debe marcar la línea internacional +1-800-555-0199 e ingresar el PIN de emergencia 9911.\n\nSi necesitas asistencia adicional, comunícate con la línea del SOC en la ext. 9111.",
  "confidence_score": 0.8807,
  "sources": [
    {
      "id": 9,
      "title": "Horarios Guardias Escalamiento Soporte Critico",
      "similarity": 0.8807
    }
  ],
  "execution_time_ms": 32150
}
```

### Ejecutar el Benchmark Completo (20 Preguntas)
```bash
python3 run_benchmark.py
```

---

## 📂 Estructura del Repositorio

```text
Oracle-VectorDesk/
├── docs_demo/                   # 10 Documentos PDF de políticas de TI generados
├── agent.py                     # API Backend en FastAPI + búsqueda vectorial Oracle + Ollama
├── ingest.py                    # Script de ingesta básica
├── ingest_pdfs.py               # Ingesta y vectorización de archivos PDF con pypdf
├── generate_sample_pdfs.py      # Generador de PDFs corporativos con ReportLab
├── init_db.sql                  # DDL de Oracle Database 26ai (Tablas e Índices Vectoriales)
├── benchmark_questions.json     # 20 preguntas de evaluación y ground-truth
├── run_benchmark.py             # Ejecutor del benchmark y reporte de métricas
├── guia_despliegue_paso_a_paso.md # Manual técnico completo y troubleshooting
├── requirements.txt             # Dependencias Python
├── .env.example                 # Plantilla de variables de entorno
└── .gitignore                   # Exclusiones de seguridad
```

---

## 📄 Licencia
Este proyecto se distribuye bajo la licencia **MIT**. Consulta el archivo `LICENSE` para más información.
