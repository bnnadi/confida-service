# Progress

## Implemented

### Core Features

- **Authentication** — JWT, login/logout, password validation
- **Sessions** — Practice and interview modes, scenario-based and job-based
- **Interview flow** — Parse JD, generate questions, analyze answers
- **Enhanced 100-point scoring** — 5 categories, 17 sub-dimensions, grade tiers (Excellent, Strong, Average, At Risk)
- **Dashboard & analytics** — Performance trends, data aggregation
- **Question bank** — Global structure, migration, seeding from sample data
- **Intelligent Question Selection** — Role analysis, diversity engine, 80–90% AI call reduction
- **TTS** — Coqui, ElevenLabs, PlayHT with provider abstraction and fallback
- **Speech-to-text** — Transcription via ai-service
- **Real-time feedback** — WebSocket for live speech analysis (pace, clarity, filler words)
- **Vector search** — Qdrant integration, semantic search
- **Async database** — Dual-mode sync/async, connection pooling, monitoring
- **PostgreSQL default** — Development uses Postgres (not SQLite) for production parity
- **Rate limiting** — Memory or Redis backend
- **Admin routes** — Health, services, models, rate limits (conditional)
- **Security headers** — Middleware
- **File upload** — Documents, audio; answer audio persistence

### Test Coverage

- **Unit:** scoring utils/models, question bank, TTS, dashboard, data aggregator, voice cache, answer audio persistence
- **Integration:** interview, session, dashboard, auth, scoring, speech, admin, files, websocket, API endpoints
- **E2E:** complete interview flow
- **CI:** `scripts/run_ci_tests_locally.sh`

See [docs/TESTING_GUIDE.md](../docs/TESTING_GUIDE.md), [docs/SCORING_TESTS_README.md](../docs/SCORING_TESTS_README.md).

## Future / Planned

- Database schema migration for enhanced scoring data
- Progress tracking across scoring dimensions
- Analytics for dimension improvement over time
- Dimension-specific coaching tips
- Redis integration for WebSocket message queuing and scaling

## Known Issues

_Placeholder — update as issues are discovered or resolved._
