# Current State Map

Baseline date: 2026-06-09  
Baseline commit: `dc03d02` (`QoL changes`) with uncommitted working-tree changes present.

## Backend In-Memory State

### Session Tracker

File: `backend/app/services/session/store.py`

Global singleton:

- `tracker = SessionTracker()`

In-memory fields:

- `session_id`: generated UUID at backend process startup.
- `start_time`: backend process startup time.
- `events`: list of `SessionEvent` objects.
- `current_event_id`: current branch tip / active event.

Behavior:

- Logs `INIT` on construction.
- Logs `NLP_INTENT`, `GENERATE`, and `OPTIMIZE` from current route paths.
- Exports session graph from memory.
- Supports checkout by event id prefix or semantic version string.
- Provides last 10 relevant events as text for prompt context.

Durability:

- Not persistent.
- Data is lost when the backend process restarts.
- Not scoped per user; the singleton is shared for the server process.

### NLP Rate Limiter

File: `backend/app/services/nlp/parser.py`

Module-level state:

- `_rate_lock`
- `_last_call_time`

Behavior:

- Serializes Gemini calls and enforces a minimum interval.
- State is process-local and resets on restart.

### Configuration Singleton

File: `backend/app/core/config.py`

Global singleton:

- `settings = Settings()`

State sources:

- `.env` file under `backend/.env`
- environment variables
- hardcoded defaults

Behavior:

- Loaded at module import time.
- `GEMINI_API_KEY` is read directly if `settings.gemini_api_key` is empty.

## Frontend In-Memory and Browser State

### Chat Component State

File: `frontend/src/components/Chat.tsx`

React state includes:

- `messages`
- `input`
- `selectedMaterial`
- `selectedLlm`
- `timeStrings`
- `showModificationHint`
- `lastParsedParameters`

Browser persistence:

- `messages` are stored in `localStorage` under `eco-draft-chat-history`.

### Frontend NLP Module State

File: `frontend/src/lib/nlp.ts`

Module-level variables:

- `conversationHistory`
- `currentPartContext`

Behavior:

- Adds lightweight context to outgoing prompts.
- Keeps only the last five frontend history entries.
- Resets only through `clearConversationHistory()` or page reload/module reload.

### Engineering Context

File: `frontend/src/lib/engineeringContext.tsx`

React context state stores current engineering data:

- `partType`
- `parameters`
- `geometryData`
- `material`
- `thickness`
- `manufacturingProcess`
- `loadCases`
- `quantity`

### Canvas State

File: `frontend/src/components/Canvas.tsx`

React state includes:

- zoom
- pan
- dragging state
- last pan position

### React Query Cache

Files:

- `frontend/src/app/providers.tsx`
- API consumers under `frontend/src/components/*`

State:

- A `QueryClient` instance is created client-side and caches API query results for the browser session.

## Filesystem / Generated Artifacts

The runtime returns exported content as base64 API fields. No durable generated-file store is currently documented or required by the route responses.

Local development artifacts present in the working tree include:

- `frontend/.next/`
- `frontend/node_modules/`
- `backend/**/__pycache__/`
- `.pytest_cache/`
- `cad_graphdb`

## Known State Limitations

- Backend session history is not persistent.
- Backend session history is process-global, not user/session isolated beyond the singleton id.
- Frontend and backend both maintain separate context/history, so they can diverge.
- Prompt history depends on generated session events, not a durable database.
- Gemini rate limiting is process-local and does not coordinate across multiple backend workers.
