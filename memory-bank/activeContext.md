# Active Context

## Current Branch

`cleanup-test-suite`

## Recent Changes

- **Documentation reorganization** — Docs moved from project root to `docs/` (API_SERVICE_SCOPE, DATABASE_SETUP, DEVELOPMENT_SETUP, DUAL_MODE_FEATURES, POSTGRES_UPDATE_SUMMARY, README_DEPLOY)
- **Test suite cleanup** — Updates to `tests/conftest.py`, `tests/e2e/conftest.py`, `tests/integration/conftest.py`
- **Integration/e2e tests** — Changes to session endpoints, dashboard, scoring, answer audio persistence, complete interview flow
- **App changes** — Dependencies, admin router, files router, speech router

## Current Focus

Memory bank implementation and test suite stabilization.

## Next Steps

- [ ] Complete test suite cleanup and ensure all tests pass
- [ ] Merge `cleanup-test-suite` when ready
- [ ] Update memory bank as work progresses
