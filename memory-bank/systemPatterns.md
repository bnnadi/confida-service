# System Patterns

## Application Architecture

### FastAPI + Routers

Entry point: `app/main.py`. Routers loaded via `load_routers()`:

- **Core:** auth, interview, sessions, files, speech, cache, health, analytics, scoring, dashboard, websocket, question_bank
- **Conditional:** admin (ENABLE_ADMIN_ROUTES), security (ENABLE_SECURITY_ROUTES)

Middleware stack (outer to inner): CORS, file upload, monitoring (optional), security headers, rate limiting, logging.

### Microservice Boundary

- **AIServiceClient** — HTTP client for ai-service. No LLM calls in api-service.
- **Contract:** `POST /ai/questions/generate`, `POST /embeddings/generate`, `POST /analyze/answer`
- **Data flow:** Client → API → ai-service (questions/embeddings) → Postgres + Qdrant → Client

### ID Mapping

1. ai-service returns questions with `question_id` (library UUID or null for new)
2. API persists to Postgres, gets DB UUID
3. Map ai-service ID → DB UUID
4. Store embeddings in Qdrant under DB UUID
5. Return DB UUID as `question_id` to client

## Dual-Mode Sessions

- **QuestionEngine** — `generate_questions_from_scenario()`, `generate_questions_from_job()`, `get_available_scenarios()`
- **SessionService** — `create_practice_session()`, `create_interview_session()`, `preview_*`, `get_available_scenarios()`
- **Modes:** practice (scenario_id) vs interview (job_title, job_description)

See [docs/DUAL_MODE_FEATURES.md](../docs/DUAL_MODE_FEATURES.md).

## Intelligent Question Selection

- **RoleAnalysisService** — Skill extraction, industry, seniority, tech stack from job description
- **QuestionDiversityEngine** — Category/difficulty balancing, tag diversity
- **IntelligentQuestionSelector** — Database-first selection, scoring, AI fallback
- **AI Fallback** — Generates questions when DB has insufficient variety
- **Benefit:** 80–90% reduction in AI API calls

See [docs/INTELLIGENT_QUESTION_SELECTION.md](../docs/INTELLIGENT_QUESTION_SELECTION.md).

## Vector Database (Qdrant)

- **Collections:** Job descriptions, questions, answers, user patterns
- **Vector size:** 1536 (OpenAI) or 384 (local)
- **Distance:** Cosine similarity
- **Flow:** PostgreSQL → embedding generation → Qdrant storage → semantic search
- **Services:** SemanticSearchService, embedding service, vector service

Note: vector_search router removed; semantic search via unified_vector_service / semantic_search_service.

See [docs/VECTOR_DATABASE_GUIDE.md](../docs/VECTOR_DATABASE_GUIDE.md).

## Async Database

- **Dual-mode:** Sync and async operations; selection via ASYNC_DATABASE_ENABLED
- **AsyncDatabaseManager** — Connection pooling, async engine
- **AsyncDatabaseMonitor** — Pool status, health checks, performance metrics
- **Endpoints:** Support both sync and async based on config

See [docs/ASYNC_DATABASE_GUIDE.md](../docs/ASYNC_DATABASE_GUIDE.md).

## TTS (Text-to-Speech)

- **Provider abstraction:** Coqui (free), ElevenLabs, PlayHT
- **Fallback chain** when primary unavailable
- **Factory pattern** for provider selection

See [docs/TTS_CONFIGURATION.md](../docs/TTS_CONFIGURATION.md).

## Key Services

| Service | Responsibility |
|---------|----------------|
| AIServiceClient | HTTP calls to ai-service |
| QuestionStoreService | Persist questions to Postgres, sync to Qdrant |
| SessionService | Session CRUD, practice/interview modes |
| HealthService | Database, dependencies health checks |
| semantic_search_service | Vector search, Qdrant integration |
| RoleAnalysisService | Job description analysis |
| QuestionDiversityEngine | Question set diversity |
| IntelligentQuestionSelector | Question selection logic |
