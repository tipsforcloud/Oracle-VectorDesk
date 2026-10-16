# 📡 Especificación y Referencia de la API REST: Oracle-VectorDesk

> **Servicio:** Backend de Resolución de Tickets con IA y Búsqueda Vectorial Nativa  
> **Motor de Base de Datos:** Oracle Database 26ai / 23ai (AI Vector Search)  
> **Motor de Inferencia:** Ollama en CPU (`qwen3:4b` / `qwen2.5`)  
> **Puerto por Defecto:** `8000`  
> **Formato de Comunicación:** JSON (`application/json`)  

---

## 📑 1. Documentación Interactiva Integrada (Swagger y ReDoc)

Al estar construido sobre **FastAPI**, el agente expone interfaces gráficas interactivas para probar y explorar el API directamente desde el navegador web:

* **Swagger UI (Pruebas interactivas en vivo):**  
  👉 `http://<IP_DE_LA_VM>:8000/docs`
* **ReDoc (Documentación técnica estructurada):**  
  👉 `http://<IP_DE_LA_VM>:8000/redoc`
* **Especificación OpenAPI (JSON crudo):**  
  👉 `http://<IP_DE_LA_VM>:8000/openapi.json`

> **Nota de Acceso:** Si intentas acceder a `http://<IP_PUBLICA_O_PRIVADA>:8000/docs` desde tu navegador y no carga, asegúrate de que el puerto `8000/tcp` esté abierto en la **Security List de la VCN** y en el cortafuegos de la VM (`sudo firewall-cmd --permanent --add-port=8000/tcp && sudo firewall-cmd --reload`).

---

## 🔌 2. Catálogo de Endpoints

### 🟢 2.1 Verificación de Salud (`GET /health`)

Permite comprobar la operatividad del backend, la conexión activa con Oracle Database 26ai, el modelo de embeddings y el motor LLM.

#### Petición:
```http
GET /health HTTP/1.1
Host: localhost:8000
Accept: application/json
```

#### Ejemplo con cURL:
```bash
curl -X GET http://localhost:8000/health
```

#### Respuesta Exitosa (`200 OK`):
```json
{
  "status": "ok",
  "database": "Oracle Database 26ai AI Vector Search",
  "embedding_model": "intfloat/multilingual-e5-base (768 dims)",
  "llm_model": "qwen3:4b",
  "dsn": "dbhost9185.sub04051019361.sarizavcn.oraclevcn.com:1521/pdblab1.sub04051019361.sarizavcn.oraclevcn.com"
}
```

#### Campos de Respuesta:
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `status` | `string` | Estado general del servicio (`ok` o `error`). |
| `database` | `string` | Identificador del motor de base de datos vectorial utilizado. |
| `embedding_model` | `string` | Modelo de Sentence Transformers activo en memoria y sus dimensiones. |
| `llm_model` | `string` | Nombre del modelo LLM configurado en Ollama. |
| `dsn` | `string` | Cadena de conexión activa hacia Oracle Database 26ai. |

---

### 🚀 2.2 Resolución de Tickets RAG (`POST /api/v1/support/resolve`)

Punto de entrada principal para recibir preguntas técnicas de usuarios, consultar la base de conocimiento vectorial en Oracle Database 26ai y sintetizar la respuesta con el LLM en CPU.

#### Flujo de Ejecución Interno:
1. **Vectorización:** Convierte el texto `user_query` en un vector denso de 768 dimensiones tipo `float32` usando el modelo `intfloat/multilingual-e5-base` en CPU.
2. **Retrieval en Oracle 26ai:** Ejecuta un SQL con la función nativa `VECTOR_DISTANCE(embedding, :query_vec, COSINE)` ordenado ascendentemente con `FETCH FIRST 3 ROWS ONLY`.
3. **Control Anti-Alucinación:** Si el score semántico más alto es menor a `SIMILARITY_THRESHOLD` (`0.35` por defecto), el agente **no inventa información** y activa el escalamiento a soporte humano.
4. **Generación Aumentada (LLM):** Si supera el umbral, ensambla el contexto recuperado de Oracle en un prompt estricto y consulta a Ollama (`qwen3:4b`).
5. **Auditoría:** Registra la interacción, la pregunta, el contexto, la latencia en ms y el puntaje de similitud en la tabla `AGENT_TICKETS_LOG`.

#### Petición HTTP:
```http
POST /api/v1/support/resolve HTTP/1.1
Host: localhost:8000
Content-Type: application/json
Accept: application/json

{
  "ticket_id": "TCK-1001",
  "user_query": "¿Cuál es la línea telefónica y el código PIN de emergencia para soporte crítico fuera de horario?",
  "category": "Operaciones TI"
}
```

#### Esquema del Payload de Entrada (Request Body):
| Campo | Tipo | Requerido | Descripción | Ejemplo |
| :--- | :--- | :---: | :--- | :--- |
| `user_query` | `string` | **Sí** | Texto o consulta en lenguaje natural del usuario. | `"Olvidé mi contraseña de VPN"` |
| `ticket_id` | `string` | No | Identificador único del ticket (Jira, ServiceNow, Remedy, etc.). | `"INC-98214"` (Default: `TCK-1001`) |
| `category` | `string` | No | Categoría o etiqueta opcional para clasificación. | `"Infraestructura"` |

---

### 📤 Respuestas de la API

#### Escenario A: Resolución Automática Exitosa (`200 OK`)
Ocurre cuando la documentación en Oracle 26ai tiene respaldo suficiente para contestar con alta certeza (`confidence_score >= 0.35`):

```json
{
  "ticket_id": "TCK-1001",
  "user_query": "¿Cuál es la línea telefónica y el código PIN de emergencia para soporte crítico fuera de horario?",
  "suggested_resolution": "Para activar la guardia de soporte crítico fuera de horario, debes seguir estos pasos:\n\n1. Llama a la línea telefónica de emergencia internacional: +1-800-555-0199.\n2. Cuando la operadora automatizada lo solicite, ingresa el código PIN de emergencia: 9911.\n3. Como canal alterno en caso de fallas, puedes contactar la extensión interna 9111 del SOC corporativo.",
  "confidence_score": 0.8807,
  "sources": [
    {
      "id": 10,
      "title": "POL-TI-10: Procedimiento de Activación de Guardias y Soporte Crítico Fuera de Horario",
      "similarity": 0.8807
    },
    {
      "id": 4,
      "title": "POL-TI-04: Protocolo de Gestión de Incidentes P1 y Crisis Tecnológicas",
      "similarity": 0.6124
    }
  ],
  "execution_time_ms": 4820
}
```

#### Escenario B: Escalamiento a Humano / Safe Fallback (`200 OK`)
Ocurre cuando la consulta del usuario no tiene respaldo documental verificado en Oracle Database (`confidence_score < 0.35`):

```json
{
  "ticket_id": "TCK-9999",
  "user_query": "¿Cómo solicito vacaciones para la próxima semana en el portal de nómina?",
  "suggested_resolution": "No se encontró documentación suficiente en la base de conocimiento para resolver este ticket automáticamente. Se escala a un agente humano de soporte.",
  "confidence_score": 0.1824,
  "sources": [],
  "execution_time_ms": 140
}
```

---

## 💻 3. Ejemplos de Integración en Distintos Lenguajes

### 🐍 Python (`requests`)
```python
import requests

url = "http://localhost:8000/api/v1/support/resolve"
payload = {
    "ticket_id": "JIRA-4029",
    "user_query": "Mi cuenta de Active Directory está bloqueada por intentos fallidos",
    "category": "Cuentas y Accesos"
}

response = requests.post(url, json=payload, timeout=60)
data = response.json()

print(f"Confianza: {data['confidence_score'] * 100:.1f}%")
print(f"Resolución:\n{data['suggested_resolution']}")
print("Fuentes consultadas:")
for src in data["sources"]:
    print(f" - [{src['similarity']}] {src['title']}")
```

### 🟨 JavaScript / Node.js (`fetch`)
```javascript
const response = await fetch("http://localhost:8000/api/v1/support/resolve", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    ticket_id: "SLACK-8812",
    user_query: "¿Cuál es el procedimiento para solicitar acceso a la VPN corporativa?"
  })
});

const result = await response.json();
console.log("Respuesta del Agente:", result.suggested_resolution);
```

### 🐚 Bash con cURL
```bash
curl -X POST http://localhost:8000/api/v1/support/resolve \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "INC-001",
    "user_query": "Requiero desbloquear mi usuario de red tras exceder los intentos de contraseña"
  }'
```

---

## 🔒 4. Manejo de Errores y Códigos HTTP

| Código | Significado | Causa Típica | Solución |
| :---: | :--- | :--- | :--- |
| `200` | OK | Petición procesada exitosamente (con resolución o escalamiento). | N/A |
| `422` | Unprocessable Entity | Formato JSON incorrecto o falta el campo requerido `user_query`. | Revisa la estructura del JSON enviado. |
| `500` | Internal Server Error | Falla de conexión con Oracle Database 26ai o problema al calcular el vector en CPU. | Revisa las credenciales en `.env` y el estado del DBSystem Listener. |
| `502` | Bad Gateway | El backend no pudo comunicarse con el servicio Ollama (`http://localhost:11434`). | Verifica que Ollama esté activo: `systemctl status ollama`. |

---

## 📊 5. Trazabilidad y Auditoría en Base de Datos

Cada petición procesada por el endpoint `/api/v1/support/resolve` queda registrada de forma transaccional e inmutable en la tabla `AGENT_TICKETS_LOG` de tu Oracle Database 26ai:

```sql
SELECT ticket_id, top_similarity, escalated, latency_ms, created_at 
FROM agent_tickets_log 
ORDER BY created_at DESC 
FETCH FIRST 10 ROWS ONLY;
```

Esto permite a los administradores generar tableros de métricas en Oracle APEX, PowerBI u OCI OpenSearch para medir:
* Tasa de resolución automática (% sin escalar).
* Latencia promedio por tipo de consulta.
* Artículos de la base de conocimiento más consultados.
