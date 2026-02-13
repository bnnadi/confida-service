# Confida API Service – Responsibility & Contract Enforcement

You are editing code in the **Confida API Service** (NOT the ai-service).

Your job is to orchestrate data flow, persistence, and retrieval for Confida.  
You are NOT allowed to do LLM work. You are NOT allowed to invent content.

Follow these rules strictly when writing, refactoring, or adding code.

---

## 1. Mission of this service

The API service is responsible for:
1. Receiving requests from the client / frontend.
2. Calling the ai-service to generate structured interview data.
3. Persisting and indexing that data (PostgreSQL + Qdrant).
4. Returning a clean, client-facing response.

In other words:  
**ai-service thinks, api-service stores + serves.**

---

## 2. High-level responsibilities

The API service MUST:

1. **Call the ai-service**
   - Send `role_name`, `job_description`, and optional `resume` to `POST /ai/questions/generate`.
   - Receive back `identifiers`, `questions`, and `embedding_vectors`.

2. **Persist to Postgres**
   - Upsert each question into the `Question` table.
   - Reuse existing questions if they already exist (dedupe by ID/text).
   - Assign stable DB UUIDs.

3. **Sync to Qdrant**
   - For every persisted question, store/update its embedding in Qdrant.
   - Attach metadata (skills, category, difficulty, etc.).
   - This is where write access to Qdrant happens — NOT in ai-service.

4. **Map IDs and build response**
   - Map ai-service question IDs → database question IDs.
   - Return the final `StructuredQuestionResponse` to the frontend.

5. **Enforce security / auth / tenancy**
   - Enforce that the user is allowed to request this.
   - (If you have multitenancy, this layer enforces it.)

---

## 3. What this service is NOT allowed to do

The API service MUST NOT:

1. **Call an LLM directly.**
   - No calls to Ollama here.
   - No calls to OpenAI, Anthropic, etc.
   - No prompt-building at this layer.
   - If you need new questions, you must ask the ai-service.

2. **Generate embeddings itself using an LLM.**
   - It can accept pre-computed embeddings from ai-service (preferred).
   - If it needs an embedding fallback, it can call a dedicated ai-service `/embeddings/generate` endpoint.
   - It CANNOT just hit OpenAI embeddings or similar.

3. **Do identifier extraction.**
   - It should never parse job descriptions or resumes with AI logic.
   - If you want identifiers like skills, tone, focus areas, seniority, etc. → ask the ai-service.

4. **Synthesize new interview questions.**
   - If you are composing or wording new questions in this repo, that’s a scope violation.
   - Questions come either from the database (existing questions) or from ai-service (new ones).

5. **Reach into ai-service internals.**
   - The contract is HTTP only.
   - Do not import ai-service Python modules or reuse ai-service helper classes.
   - The two services should work like separate deployable units.

---

## 4. Required endpoint behavior

### `/api/v1/questions/generate`

This endpoint is the “happy path.” It MUST:

1. Validate input (role_name, job_description, resume?).
2. Call `ai-service POST /ai/questions/generate`.
3. Get back:
   ```json
   {
     "identifiers": { ... },
     "questions": [
       {
         "id": "ai-svc-id-or-uuid",
         "text": "How do you handle async operations in Python?",
         "category": "technical",
         "skills": ["asyncio", "Python"],
         "difficulty": 3,
         "source": "from_library"
       }
     ],
     "embedding_vectors": {
       "ai-svc-id-or-uuid": [0.12, -0.44, 0.91]
     }
   }
   ```
4. Persist those questions in Postgres using `QuestionStoreService`.
   - Reuse existing rows if they already exist.
   - Create new ones if not.

5. Upsert those questions + embeddings into Qdrant.
   - Use the DB UUIDs as the canonical ID in Qdrant.

6. Build the final response to the frontend.
   - Include `identifiers`, `questions`, and `embedding_vectors`.
   - All `questions[*].question_id` should now point at the DB UUID.

This endpoint should be the single source of truth.
Any other “legacy” endpoints (like `/parse-jd`) must either:
- Delegate to this flow,
- Or be marked deprecated and throw.

---

## 5. Allowed services and modules

The API service MAY:

- Use `AIServiceClient` to talk to the ai-service.
  - Example: `ai_client.generate_questions_structured()`

- Use `QuestionStoreService` (or similar) to:
  - `persist_questions()` to Postgres
  - `sync_question_to_vector_store()` to Qdrant
  - Optionally `persist_and_sync_questions()` if you’ve consolidated

- Manage sessions / InterviewSession models if you have them:
  - Attach persisted questions to a session
  - Track which questions were used

- Apply auth and user context
  - e.g. “questions for THIS user’s prep session”

---

## 6. Disallowed patterns (hard fail in PR review)

Reject code if you see any of these in the API service:

❌ `import openai`, `import anthropic`, or any LLM client  
❌ Calling `ollama` directly  
❌ Inlining a prompt string like `"You are an AI interview assistant..."`  
❌ Generating embeddings by prompting a model directly  
❌ Doing semantic “analysis” of the job description  
❌ Deriving “tone”, “focus areas”, or “difficulty” from the text using AI logic  
❌ Writing “question generation” logic in Python here

Those belong in ai-service.

---

## 7. ID + embedding mapping rules

When you receive data from ai-service:
- ai-service returns each question with an `id` (either a known library UUID or a generated UUID).
- ai-service also returns `embedding_vectors` keyed by that same `id`.

Your job in the API service is to:

1. Persist each question to Postgres.
   - Get the DB UUID (say `db_id`).

2. Build a mapping from ai-service question ID → DB UUID.

3. Use that mapping to push embeddings into Qdrant under the DB UUID.

4. Return to the client using DB UUID as `question_id`.

In other words:
- ai-service ID = “question record in AI world”
- DB UUID = “question record in Confida world”
- You are responsible for translating between them.

---

## 8. Success criteria

Your work in this repo is considered correct when:

✅ `/api/v1/questions/generate` can:
   - call ai-service,
   - persist questions,
   - sync embeddings into Qdrant,
   - respond to the client

✅ The API service never:
   - calls an LLM
   - builds prompts
   - fabricates/rewrites interview questions itself

✅ The ai-service never:
   - touches Postgres
   - writes to Qdrant

✅ The contract is clean:
   - ai-service returns identifiers + questions + embeddings
   - api-service stores + maps + indexes + serves

If these are all true, the platform boundary is clean and scalable.
