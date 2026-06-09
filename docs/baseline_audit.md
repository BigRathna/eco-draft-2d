# Baseline Audit

Baseline date: 2026-06-09  
Baseline commit: `dc03d02` (`QoL changes`)  
Working tree: dirty; Phase 0 captures the current working tree without changing runtime logic.

## Scope

This document completes Phase 0: Baseline Audit and Freeze from `cad_assistant_master_plan.md`.

Related Phase 0 documents:

- `docs/current_prompt_map.md`
- `docs/current_schema_map.md`
- `docs/current_state_map.md`

## Current System Summary

The current application is a FastAPI + Next.js CAD assistant with:

- Gemini, Ollama, and OpenRouter NLP provider paths.
- A prompt-builder/adapters layer for prompt assembly.
- CAD intent, geometry, checks, drawing, LCA, optimization, session, and prompt schemas.
- Universal 2D part generation for common mechanical shapes.
- SVG/DXF export and PDF drawing generation.
- Rule-based manufacturability checks.
- Simple random-sampler optimization.
- Frontend chat, canvas, checks, analysis, LCA, and Pareto UI components.
- In-memory backend session graph.

## Phase 0 Task Checklist

### Inventory all current prompt templates

Status: complete.

Recorded in `docs/current_prompt_map.md`.

Prompt sources include:

- `backend/app/services/nlp/prompts.py`
- `backend/app/services/nlp/prompt_builder.py`
- `backend/app/services/nlp/adapters.py`
- `frontend/src/lib/nlp.ts`
- `frontend/src/components/Chat.tsx`

### Inventory all provider code paths

Status: complete.

Recorded in `docs/current_prompt_map.md`.

Provider paths include:

- Gemini through `_call_gemini(...)`.
- Ollama through `_call_openai_compatible(...)`.
- OpenRouter through `_call_openai_compatible(...)`.

### Inventory all schema files and generated output formats

Status: complete.

Recorded in `docs/current_schema_map.md`.

Schema files inventoried:

- `backend/app/schemas/cad.py`
- `backend/app/schemas/parts.py`
- `backend/app/schemas/common.py`
- `backend/app/schemas/checks.py`
- `backend/app/schemas/analysis.py`
- `backend/app/schemas/lca.py`
- `backend/app/schemas/drawing.py`
- `backend/app/schemas/optimization.py`
- `backend/app/schemas/optimization_simple.py`
- `backend/app/schemas/session.py`
- `backend/app/schemas/nlp.py`

Generated output formats inventoried:

- SVG
- DXF
- PDF
- JSON API responses
- HTML session visualization

### Inventory all stateful components currently kept in memory

Status: complete.

Recorded in `docs/current_state_map.md`.

Major stateful components:

- Backend `SessionTracker` singleton.
- Backend NLP rate limiter variables.
- Backend `settings` singleton.
- Frontend chat React state and `localStorage` history.
- Frontend NLP module-level context variables.
- Frontend engineering context.
- Frontend React Query cache.
- Frontend canvas state.

### Record current test coverage

Status: recorded as current baseline.

Command run:

```bash
pytest -q
```

Result:

- 2 passed
- 2 failed
- 5 warnings

Failing tests:

- `backend/tests/test_prompts.py::test_prompt_bundle_content`
- `backend/tests/test_prompts.py::test_provider_equivalence_logic`

Observed failure cause:

- Tests compare unstripped prompt constants against prompt-bundle output that strips layer content.

Coverage percentage:

- Not available in current baseline because the available test run fails before a useful coverage baseline is produced.
- No coverage report artifact was generated during Phase 0.

### Record current known limitations

Status: complete.

Known limitations:

- Backend session storage is in memory only.
- Session state is process-global and not durable.
- Prompt assembly is partly backend-driven and partly frontend-driven.
- Gemini and OpenAI-compatible paths do not receive identical provider payloads.
- Intent parameter validation remains loose for generic parts.
- `/chat/parse` uses plain dict request/response handling.
- Existing prompt tests fail.
- LCA endpoint is disabled by default.
- RAG, vector retrieval, training-data export, local fine-tuned intent model, A/B routing, and durable evaluation are not implemented.

## Reproducibility Notes

Baseline commands used:

```bash
rg -n "phase zero|phase 0|Phase Zero|Phase 0|zero" -S . --glob '!frontend/node_modules/**' --glob '!frontend/.next/**' --glob '!backend/**/__pycache__/**'
find backend/app/schemas -maxdepth 1 -type f -name '*.py' | sort
find backend/app/services -maxdepth 3 -type f -name '*.py' | sort
find backend/tests -type f -name 'test*.py' -print 2>/dev/null
pytest -q
```

Git baseline observed:

```text
 M .gitignore
 M backend/app/services/nlp/parser.py
 M backend/app/services/nlp/prompts.py
?? backend/app/schemas/nlp.py
?? backend/app/services/nlp/adapters.py
?? backend/app/services/nlp/prompt_builder.py
?? backend/docs/
?? backend/tests/
?? backend/tests_prompts.py
?? cad_assistant_master_plan.md
?? cad_graphdb
?? deep-research-report.md
```

Latest commits observed:

```text
dc03d02 QoL changes
e78a81f frintend
ac55549 Initial commit
```

## Phase 0 Acceptance Status

- Every prompt source is listed: complete.
- Every provider call path is documented: complete.
- Every in-memory structure is documented: complete.
- Baseline is versioned and reproducible: complete for current dirty working tree; clean freeze still requires committing or otherwise preserving this exact working tree.
