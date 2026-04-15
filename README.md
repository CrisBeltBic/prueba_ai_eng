# Bancolombia RAG Assistant

Asistente conversacional con Retrieval-Augmented Generation (RAG) sobre el url /personas de Bancolombia. El usuario/tester hace preguntas sobre productos y servicios, el agente busca en la base de conocimiento y responde con fuentes.

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    RUNTIME SERVICES                     │
│                                                         │
│  frontend  ──►  agent_service  ──►  chat_service        │
│  :8501          :8080               :8082               │
│                    │                                    │
│                    │ stdio (MCP)                        │
│               knowledge_server                          │
│                    │                                    │
│                    ▼                                    │
│            vector_store_service  ──►  ChromaDB          │
│                    :8084               :8000            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  INGESTION PIPELINE                     │
│  pipeline_runner ──► scraper_service ──► bancolombia.com│
│                  └──► vector_store_service              │
└─────────────────────────────────────────────────────────┘
```

Cada servicio tiene su propia responsabilidad y Dockerfile. El `knowledge_server` corre como **subprocess stdio** dentro del `agent_service` usando el protocolo MCP — sin puerto expuesto, comunicación por stdin/stdout.

Diagramas detallados en [docs/architecture.md](bancolombia-rag/docs/architecture.md).

---

## Flujo de una pregunta

1. Usuario escribe en el front
2. El front llama `POST /chat` al agent_service
3. El agente carga historial previo desde chat_service (para contexto del LLM, no para display)
4. El agente invoca la tool `search_knowledge_base` del knowledge_server (MCP stdio)
5. El knowledge_server consulta vector_store_service y este a un db vecitorizada agnostica (podria ser pgvector, weaviate pero es chroma la idea es que para el servicio sea indiferente)
6. El agente envía pregunta, contexto RAG y historial al LLM
7. El agent guarda los mensajes (user + assistant) en chat_service
8. Frontend muestra la respuesta con fuentes como links

> **Nota:** el front también consulta chat_service directamente al abrir una conversación pasada para ver el histirial
> desde el sidebar (`GET /chats/{id}/messages`) — eso es independiente del flujo del agente.

---

## Requisitos

- Docker y Docker Compose
- Una API key de Groq (gratuita en [console.groq.com](https://console.groq.com))

---

## Inicio rápido

### 1. Variables de entorno

```bash
cp bancolombia-rag/.env.example bancolombia-rag/.env
```

Edita `.env` y completa al menos:

```env
AGENT_API_SERVICE_KEY=una-clave-secreta-cualquiera
GROQ_API_KEY=tu_api_key_de_groq
```

### 2. Levantar el stack

```bash
cd bancolombia-rag
make run
# ó
docker compose up --build
```

Servicios disponibles:
| Servicio | URL |
|---|---|
| Frontend (UI) | http://localhost:8501 |
| Agent API | http://localhost:8080 |
| Chat API | http://localhost:8082 |
| Vector Store API | http://localhost:8084 |

### 3. Ingestión de datos (primera vez)

El asistente necesita que bancolombia.com esté indexado en ChromaDB. Corre el pipeline una sola vez:

```bash
make pipeline
# ó
docker compose --profile pipeline up --build pipeline_runner
```

El pipeline hace:
1. **Scraper** — BFS desde `/personas`, respeta `robots.txt`, guarda páginas en `pages.jsonl`
2. **Vector Store** — lee `pages.jsonl`, divide en chunks, genera embeddings con `sentence-transformers` y los sube a la vector db, en este caso ChromaDB

Cuando termina puedes verificar que hay datos:
```bash
curl http://localhost:8084/stats
```

### 4. Usar el asistente

Abre http://localhost:8501 y haz preguntas sobre productos Bancolombia.

---

## Cambiar de LLM

El agente es independiente del proveedor de LLM. Solo cambia `LLM_PROVIDER` en `.env` y reinicia:

```env
# Groq (default, gratuito)
LLM_PROVIDER=groq
GROQ_API_KEY=...
GROQ_MODEL=llama-3.3-70b-versatile

# Ollama (local, sin internet)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.1

NOTA: Ollama es para ejemplificar solo se impleto el funcionamiento para Groq pero la idea en si es que el por medio del Bridge implementado pueda ser cualquiera por si un dia sale una mejor LLM en terminos de capacidad y costos por ejemplo.
```

Cero cambios en el código — la abstracción `LLMClient` en `agent_service/src/agent/llm/` hace el switch transparente.

---

## Tests

Los tests corren dentro de los contenedores de cada servicio para no instalar dependencias pesadas (chromadb, sentence-transformers) localmente:

```bash
# Vector store
docker build -t vs-test bancolombia-rag/vector_store_service/
docker run vs-test pytest /app/tests/ -v

# Agent
docker build -t agent-test bancolombia-rag/agent_service/
docker run agent-test pytest /app/tests/ -v

# Chat
docker build -t chat-test bancolombia-rag/chat_service/
docker run chat-test pytest /app/tests/ -v
```

Los tests usan `MagicMock` / `AsyncMock` para aislar la lógica de negocio sin levantar ChromaDB ni PostgreSQL.

---

## CI

GitHub Actions corre en cada push y PR a `main`:

| Job | Qué hace |
|---|---|
| `lint` | `ruff check` sobre todo el código |
| `test-vector-store` | build + pytest del vector_store_service |
| `test-agent` | build + pytest del agent_service |
| `test-chat` | build + pytest del chat_service |

Ver [.github/workflows/ci.yml](.github/workflows/ci.yml).

---

## Estructura del proyecto

```
bancolombia-rag/
├── agent_service/       # Orquesta LLM + MCP + historial
│   └── src/
│       ├── agent/       # api, logic, llm/, mcp_client
│       ├── knowledge_server/  # MCP server (stdio subprocess)
│       └── capabilities.yaml  # scope, thresholds, tone — sin tocar código
├── chat_service/        # CRUD historial de conversaciones (PostgreSQL)
├── vector_store_service/ # Embeddings + ChromaDB
├── scraper_service/     # BFS crawler sobre bancolombia.com
├── frontend_service/    # Streamlit UI
├── pipeline_runner/     # Orquesta scraper → vector_store
├── postgres/            # Init SQL para chat_service
├── docs/
│   └── architecture.md  # Diagramas Mermaid
├── docker-compose.yml
├── Makefile
└── pyproject.toml       # ruff + mypy + pytest config
```

---

## Decisiones de diseño

**Arquitectura de microservicios** — cada servicio tiene una sola responsabilidad y puede escalar, desplegarse y testearse de forma independiente. El `scraper_service` puede correrse una sola vez sin afectar el resto del stack. El `vector_store_service` puede cambiar de proveedor de base de datos sin tocar el agente. Si el chat_service falla, el agente puede seguir respondiendo (sin historial). La separación también hace explícitas las dependencias entre componentes.

**Dos bases de datos, no una** — ChromaDB y PostgreSQL resuelven problemas distintos que ninguna DB generalista resuelve bien sola:
- *ChromaDB* está optimizada para similarity search sobre vectores de alta dimensión. Una DB relacional haría ese mismo query ordenes de magnitud más lento, presisamente por eso no use pgvector.
- *PostgreSQL* es la elección correcta para historial de chat: datos relacionales, queries por `chat_id`, orden cronológico garantizado, transacciones ACID. No tiene sentido indexar mensajes de texto en un vector store y tambien la use por preferencias personales pues la acostumbro a usar, ademas suele tener soporte para producción por lo que me parecio las mas adecuada.

**ChromaDB como vector store** — fácil de dockerizar (imagen oficial, volumen persistente), no requiere configuración de cluster, soporta cosine similarity nativamente y tiene cliente Python sin dependencias C++ externas. Para un MVP o prueba técnica es la opción con menor fricción. Si el volumen escala, el `vector_store_service` expone una interfaz (`VectorStore`) que permite migrar a Qdrant, Weaviate o pgvector cambiando solo el adaptador.

**`chat_id` como identificador de sesión** — el sistema no tiene autenticación de usuarios. El `chat_id` es un UUID que identifica una conversación, generado en el primer mensaje y devuelto al frontend. El frontend lo persiste en `session_state` y lo envía en cada request. Esto permite multi-sesión (varias conversaciones en paralelo) sin necesidad de login.

**Memoria en tres capas**
- *Corto plazo* — las últimas N turns del historial se incluyen en cada prompt (configurable en `capabilities.yaml`, `memory.history_turns`). El LLM las lee directamente como contexto.
- *Mediano plazo* — no implementado. La idea sería resumir conversaciones largas para comprimir el historial sin perder contexto relevante. Se dejó como mejora futura por una razón de privacidad: resumir implica que el agente "recuerda" entre sesiones por defecto, lo cual requiere consentimiento explícito del usuario.
- *Largo plazo* — la base de conocimiento en ChromaDB . Permanente, indexada una vez, consultada en cada pregunta via RAG, no es que se vectoricen las interacciones con el usuario para luego ahcer RAGA  eso si no se deja la información de la pag del banco en la db como data persistente.

**MCP via stdio, no HTTP** — el `knowledge_server` corre como subprocess del agente en vez de ser un servicio aparte. No hay latencia de red en cada tool call, no hay puerto extra que exponer, y el protocolo MCP es más expresivo que una API REST para describir tools a un LLM.

**LLM bridge pluggable** — `LLMClient` es un Protocol (duck typing). Cambiar de Groq a OpenAI a Ollama requiere solo cambiar una variable de entorno. Útil tanto para desarrollo local (Ollama, sin costo) como para producción (modelos comerciales).

**Tests en contenedor** — los servicios tienen dependencias pesadas (sentence-transformers descarga ~420 MB, chromadb tiene bindings C++). Correr pytest dentro del mismo Docker image que usará CI evita la clásica trampa de "pasa en local, falla en el servidor".

**Auth en un solo endpoint** — `X-API-Key` solo en `POST /chat`. El healthcheck de Docker (`GET /health`) no requiere key porque Docker lo llama internamente para saber si el contenedor está listo.

**Prompt construido en el agente, no en el MCP server** — el `knowledge_server` solo busca y retorna chunks con metadatos. La construcción del prompt (sistema + historial + contexto RAG + pregunta) ocurre en el `agent_service`. Esto mantiene el MCP server stateless y reutilizable: cualquier otro cliente MCP puede consumir las mismas tools sin heredar el prompt ni la lógica de negocio del agente de Bancolombia.

**Chunking recursivo por separadores naturales** — el chunker intenta dividir primero por párrafos (`\n\n`), luego por líneas (`\n`), luego por oraciones (`. `), luego por palabras (` `). Solo hace corte duro a nivel de caracteres si ningún separador produce más de un chunk. Tamaño: 512 caracteres con 64 de overlap. El overlap garantiza que el contexto no se pierda en los bordes del chunk — si una idea abarca el final de un chunk y el inicio del siguiente, ambos la contienen parcialmente.

**Embeddings: `paraphrase-multilingual-mpnet-base-v2`** — modelo de `sentence-transformers` que produce vectores de 768 dimensiones. Se eligió por tres razones: (1) soporta español nativamente — fue entrenado en 50+ idiomas incluyendo español; (2) corre localmente sin costo ni latencia de API; (3) el tamaño del modelo (~420 MB) es manejable en Docker. La indexación en ChromaDB usa similitud coseno, que normaliza la magnitud del vector y compara solo la dirección semántica.

**Scraping: decisiones de diseño**
- *Profundidad*: BFS desde `/personas` con límite configurable (`SCRAPER_MAX_PAGES`, default 60). BFS garantiza que las páginas más cercanas al inicio (las más importantes) se indexen primero.
- *JavaScript rendering*: el sitio de Bancolombia usa contenido estático en la sección `/personas`. Se usa `httpx` para fetching directo sin browser headless — más rápido y sin overhead de Playwright/Selenium. Si una página retorna contenido vacío, se descarta.
- *robots.txt*: se descarga y parsea al inicio de cada job con `urllib.robotparser`. Cada URL se verifica antes de hacer el request. Si `robots.txt` no está disponible, se continúa (sitio público, sin restricciones encontradas).
- *Rate limiting*: delay configurable entre requests (`SCRAPER_DELAY_SECONDS`) y semáforo de concurrencia para no saturar el servidor.

---

## CD

El pipeline de Continuous Deployment no está implementado — la prueba no especificaba un entorno destino. 

---

## Limitaciones conocidas

- **Sin autenticación de usuarios** — el sistema identifica conversaciones por `chat_id` (UUID), no por usuario. Cualquiera con la URL del frontend puede crear conversaciones. Para producción se requeriría un sistema de auth.
- **MCP subprocess por instancia** — el `knowledge_server` corre como subprocess dentro del contenedor del agente. Si el agente escala horizontalmente (múltiples réplicas), cada réplica lanza su propio subprocess.
- **Scraping estático** — el crawler no renderiza JavaScript. Páginas que cargan contenido dinámicamente (SPA con datos en cliente) no serán indexadas correctamente.
- **Conocimiento desactualizado** — la base de conocimiento refleja el sitio en el momento de la ingestión. No hay actualización automática. Requiere correr el pipeline manualmente cuando el contenido del sitio cambia.
- **Modelo de embeddings en español** — `paraphrase-multilingual-mpnet-base-v2` es bueno pero no es el estado del arte para español. Modelos como `text-embedding-3-large` de OpenAI o `embed-multilingual-v3.0` de Cohere darían mejor recall semántico en español a costo de latencia y precio por llamada de API.
