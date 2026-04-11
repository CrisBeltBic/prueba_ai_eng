# Architecture

## Diagram 1 — General Architecture

```mermaid
flowchart LR
    User([User])
    LLM([LLM API])
    Web([Bancolombia Web])

    subgraph Online
        Front[frontend_service]
        subgraph agent_service
            Agent[agent]
            MCP[knowledge_server\nstdio subprocess]
        end
        Chat[chat_service]
        VectorStore[vector_store_service]
        VectorDB[(vector_database\nChromaDB)]
        ChatDB[(chat_database\nPostgreSQL)]
    end

    subgraph Pipeline
        Scraper[scraper_service]
        PipelineRunner[pipeline_runner]
    end

    User --> Front
    Front --> Agent
    Front --> Chat
    Agent --> MCP
    Agent --> Chat
    Agent --> LLM
    MCP --> VectorStore
    VectorStore --> VectorDB
    Chat --> ChatDB
    PipelineRunner --> Scraper
    PipelineRunner --> VectorStore
    Scraper --> Web
```

---

## Diagram 2 — Query Flow

```mermaid
sequenceDiagram
    actor U as User
    box Internal Services
        participant F as frontend_service
        participant A as agent_service
        participant K as knowledge_server (stdio)
        participant V as vector_store_service
        participant C as chat_service
    end
    box External
        participant L as LLM API
    end

    U->>F: question
    F->>A: POST /chat
    A->>C: GET /chats/{id}/messages
    A->>K: search_knowledge_base (MCP tool)
    K->>V: POST /search
    V-->>K: chunks + sources
    K-->>A: context + sources
    A->>L: question + context + history
    L-->>A: answer
    A->>C: POST /chats/messages (user + assistant)
    A-->>F: answer + sources
    F-->>U: answer + sources
```

---

## Diagram 3 — Ingestion Flow

```mermaid
sequenceDiagram
    participant P as pipeline_runner
    participant S as scraper_service
    participant V as vector_store_service
    participant D as vector_database

    P->>S: POST /scraper/start
    P->>S: GET /scraper/status (poll)
    S->>S: BFS crawl bancolombia.com/personas
    S-->>P: phase=done

    P->>V: POST /ingest/start
    P->>V: GET /ingest/status (poll)
    V->>V: chunk + embed + upsert
    V->>D: store vectors
    V-->>P: phase=done
```
