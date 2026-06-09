# Current Prompt Map

Baseline date: 2026-06-09  
Baseline commit: `dc03d02` (`QoL changes`) with uncommitted working-tree changes present.

## Active Runtime Prompt Flow

The active NLP entry point is `backend/app/services/nlp/parser.py`.

1. `parse_engineering_request(user_message, provider)` receives the frontend message and provider name.
2. It reads session history from `tracker.get_context_summary()`.
3. It infers `is_modification` from the current-part marker or session-history contents.
4. It builds a canonical prompt bundle with `create_prompt_builder(...)` from `backend/app/services/nlp/prompt_builder.py`.
5. It transforms the bundle through `get_adapter(provider)` from `backend/app/services/nlp/adapters.py`.
6. It calls either Gemini or the OpenAI-compatible provider path.
7. It applies defaults and returns `CadIntent`.

## Prompt Sources

### `backend/app/services/nlp/prompts.py`
Canonical prompt fragments currently used by the prompt builder:

- `SYSTEM_ROLE`: role and objective for the CAD assistant.
- `TASK_CREATE`: create/checkout extraction instructions.
- `TASK_MODIFY`: modification instructions and examples.
- `SUPPORTED_PARTS`: supported part-type list.
- `SUPPORTED_PARAMETERS`: supported parameter names and categories.
- `UNIT_RULES`: millimeter canonical unit and unit-conversion examples.
- `JSON_SCHEMA`: JSON shape requested from the model.
- `JSON_ONLY_CRITICAL`: JSON-only output instruction.

### `backend/app/services/nlp/prompt_builder.py`
Builds ordered prompt layers:

1. `system`
2. `task`
3. `history`, when session history is present
4. `parts`
5. `params`
6. `units`

It returns a `PromptBundle` with a version hash.

### `backend/app/services/nlp/adapters.py`
Provider formatting layer:

- `GeminiAdapter`: returns `bundle.build_full_string()`.
- `OpenAICompatibleAdapter`: returns two chat messages and appends `JSON_SCHEMA` plus `JSON_ONLY_CRITICAL` to the system content.

### Frontend Context Prompting

`frontend/src/lib/nlp.ts` mutates the user message before it reaches the backend:

- Adds `[Current part: ...] Modification request: ...` for likely modification requests.
- Adds `[Previous: ...] Now: ...` for follow-up context in some cases.
- Stores frontend conversation context in module-level variables.

`frontend/src/components/Chat.tsx` also appends material selection text when a material is selected:

- `. The material MUST be steel.`
- `. The material MUST be aluminum.`
- `. The material MUST be stainless_steel.`

## Provider Call Paths

### Gemini

Files:

- `backend/app/services/nlp/parser.py`
- `backend/app/services/nlp/adapters.py`

Flow:

1. `GeminiAdapter.transform(...)` returns a plain string prompt.
2. `_call_gemini(system_prompt, user_message)` concatenates prompt and user message.
3. Request is sent to `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent`.
4. Request includes a function declaration named `engineering_part`.
5. Parser accepts either function-call args or JSON extracted from text.

Known behavior:

- Gemini does not receive `JSON_SCHEMA` from `OpenAICompatibleAdapter`.
- Gemini relies on the function declaration plus common prompt layers.

### Ollama

Files:

- `backend/app/services/nlp/parser.py`
- `backend/app/services/nlp/adapters.py`

Flow:

1. `OpenAICompatibleAdapter.transform(...)` returns OpenAI-style messages.
2. `_call_openai_compatible(payload, provider)` sends messages to `http://localhost:11434/v1/chat/completions`.
3. Model is hardcoded as `llama3`.
4. Request includes `response_format: {"type": "json_object"}`.

### OpenRouter

Files:

- `backend/app/services/nlp/parser.py`
- `backend/app/services/nlp/adapters.py`

Flow:

1. `OpenAICompatibleAdapter.transform(...)` returns OpenAI-style messages.
2. `_call_openai_compatible(payload, provider)` sends messages to `https://openrouter.ai/api/v1/chat/completions`.
3. Model is hardcoded as `meta-llama/llama-3-8b-instruct`.
4. Request includes `response_format: {"type": "json_object"}`.

## Prompt Tests

Active test file:

- `backend/tests/test_prompts.py`

Stale or incompatible root-level test file:

- `backend/tests_prompts.py`

Current baseline result from `pytest -q`:

- 2 passed
- 2 failed
- 5 warnings

Failures are caused by exact substring assertions that compare unstripped prompt constants against stripped prompt-bundle output.

## Known Prompt Limitations

- Provider behavior is not fully equivalent: Gemini receives a function declaration but not the explicit `JSON_SCHEMA` adapter suffix.
- Modification detection is heuristic and currently checks for `[Current part:` or the word `Created` in session history.
- Frontend mutates prompt text before backend parsing, so not all context assembly is centralized in backend prompt builder.
- Prompt snapshot testing is present but currently failing.
