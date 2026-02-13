# Project Brief

## Core Mission

Confida API Service is an **orchestration layer** for AI-powered interview coaching. It receives requests from clients, calls the ai-service for structured interview data, persists and indexes that data, and returns clean responses.

**Key principle:** ai-service thinks, api-service stores + serves.

## Scope

### This Service MUST

1. **Call the ai-service** — Send `role_name`, `job_description`, optional `resume` to `POST /ai/questions/generate`. Receive `identifiers`, `questions`, `embedding_vectors`.
2. **Persist to Postgres** — Upsert questions into the Question table, dedupe by ID/text, assign stable DB UUIDs.
3. **Sync to Qdrant** — Store/update embeddings for each question with metadata. API service owns Qdrant writes.
4. **Map IDs** — Translate ai-service question IDs → DB UUIDs → Qdrant. Return DB UUIDs to client.
5. **Enforce auth/tenancy** — Ensure user is allowed to request data.

### This Service MUST NOT

- Call any LLM directly (OpenAI, Anthropic, Ollama)
- Generate embeddings itself (except via ai-service `/embeddings/generate` fallback)
- Parse job descriptions or resumes with AI logic
- Synthesize or invent interview questions
- Import ai-service Python modules — HTTP contract only

## Contract Summary

- **Question generation:** `POST {AI_SERVICE_URL}/ai/questions/generate`
- **Embedding fallback:** `POST {AI_SERVICE_URL}/embeddings/generate` when `embedding_vectors` missing
- **Answer analysis:** `POST {AI_SERVICE_URL}/analyze/answer`
- **Question sources:** `from_library` (existing in DB) or `newly_generated` (AI-created)

See [docs/API_SERVICE_SCOPE.md](../docs/API_SERVICE_SCOPE.md) and [docs/AI_SERVICE_CONTRACT.md](../docs/AI_SERVICE_CONTRACT.md) for full details.

## Success Criteria

- `/api/v1/questions/generate` calls ai-service, persists questions, syncs to Qdrant, responds to client
- API service never calls LLMs, builds prompts, or fabricates questions
- ai-service never touches Postgres or writes to Qdrant
