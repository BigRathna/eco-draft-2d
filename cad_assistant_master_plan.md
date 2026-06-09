# CAD Assistant Development Plan

## Purpose
Create a single, execution-ready plan that any contributing agent can follow to evolve the current Gemini-driven CAD assistant into a data-logged, testable, locally trainable system with optional retrieval and future fine-tuning.

This plan is written to be:
- **Sequential** so dependencies are respected.
- **Granular** so each agent can execute a bounded task.
- **Verifiable** so every milestone has acceptance criteria.
- **Complete** so nothing important is omitted.

---

## Current State Summary
The repository already includes:
- CAD schemas for intent and geometry.
- Provider-based NLP parsing via Gemini, Ollama, and OpenRouter.
- Universal part generation for common mechanical shapes.
- Rule-based design checks.
- Frontend chat and action workflows.
- In-memory session graph/history.

The system is **not yet** equipped with:
- Persistent session logging.
- Training-data export.
- Strict schema validation for all part parameters.
- Retrieval over engineering templates / standards.
- Local fine-tuned intent inference.
- A/B routing between providers.
- A durable evaluation harness.

---

## Target End State
The assistant should support this flow:

1. User gives a CAD request in chat.
2. The system parses the request into a strict typed intent.
3. The system retrieves relevant engineering templates, rules, or examples when needed.
4. The system generates the part geometry.
5. The system runs design checks and exports.
6. The system stores the entire interaction persistently.
7. The system can later export those logs into a training dataset.
8. The system can train a local intent model from the exported dataset.
9. The system can route between Gemini and local model via A/B testing.
10. The system can be evaluated on held-out prompts and regression suites.

---

## Guiding Principles
1. **Data first**: no fine-tuning before persistent logs exist.
2. **Structure over free text**: intent should become typed, not loosely typed.
3. **Prompt consistency**: all providers must share one prompt assembly pipeline.
4. **Deterministic checks outside the model**: rule engines should stay in code, not in prompts.
5. **Retrieval should serve engineering constraints**: templates, standards, and examples are higher value than prompt similarity alone.
6. **Every change must be measurable**: add tests and metrics for each milestone.
7. **Keep generation separate from intent**: the model should learn intent extraction, not geometry synthesis.

---

## Workstreams
The project is split into eight workstreams.

### Workstream A: Architecture and Prompt Consolidation
Goal: unify all LLM prompt assembly and provider-specific behavior.

### Workstream B: Persistent Logging and Session Store
Goal: capture every interaction in durable storage.

### Workstream C: Dataset Export Pipeline
Goal: turn logs into clean training data.

### Workstream D: Schema Hardening
Goal: make intent and part parameters strict and validated.

### Workstream E: Retrieval Layer
Goal: retrieve engineering templates, constraints, and examples.

### Workstream F: Local Intent Model
Goal: train and serve a local CadIntent extractor.

### Workstream G: Evaluation and A/B Testing
Goal: compare providers and protect quality.

### Workstream H: Deployment and Maintenance
Goal: make the system operable and reproducible.

---

# Phase 0: Baseline Audit and Freeze

## Objective
Create a stable baseline before changing behavior.

## Tasks
- Inventory all current prompt templates.
- Inventory all provider code paths.
- Inventory all schema files and generated output formats.
- Inventory all stateful components currently kept in memory.
- Record current test coverage.
- Record current known limitations.

## Deliverables
- `docs/baseline_audit.md`
- `docs/current_prompt_map.md`
- `docs/current_schema_map.md`
- `docs/current_state_map.md`

## Acceptance Criteria
- Every prompt source is listed.
- Every provider call path is documented.
- Every in-memory structure is documented.
- Baseline is versioned and reproducible.

## Agent Assignment
**Agent A0**: Audit and document current behavior without changing runtime logic.

---

# Phase 1: Prompt Consolidation and Provider Standardization

## Objective
Make prompt assembly explicit, centralized, and testable.

## Why this comes first
The system currently has duplicated or partially unused prompt logic. Without centralization, later evaluation and training data will be inconsistent.

## Tasks
1. Create a single prompt assembly module.
2. Move all reusable system instructions into named constants or template fragments.
3. Separate common instructions from provider-specific instructions.
4. Normalize message formatting for all providers.
5. Ensure Gemini, Ollama, and OpenRouter all consume the same logical prompt bundle.
6. Remove or deprecate unused prompt copies.
7. Add prompt snapshot tests.

## Required Prompt Layers
Use a layered prompt design:
- **System layer**: role, domain boundaries, strictness rules.
- **Task layer**: current user request.
- **Context layer**: chat history, selected material, current part, prior edits.
- **Constraint layer**: engineering rules, output format, schema requirements.
- **Provider layer**: any provider-specific formatting requirements.

## Deliverables
- `backend/app/services/nlp/prompts.py`
- `backend/app/services/nlp/prompt_builder.py`
- Prompt snapshot tests.
- A markdown spec describing prompt assembly order.

## Acceptance Criteria
- A single code path builds prompts.
- All providers share the same logical content.
- Snapshot tests detect accidental prompt drift.
- Unused prompt files are removed or clearly deprecated.

## Agent Assignment
**Agent A1**: Consolidate prompt templates and build a canonical prompt builder.

---

# Phase 2: Schema Hardening

## Objective
Ensure intent parsing produces strongly typed, valid CAD data.

## Problem Statement
Current intent handling allows loose fields and broad value types. That makes downstream logic fragile and reduces training-data quality.

## Tasks
1. Replace broad parameter containers with typed parameter models.
2. Introduce discriminated unions for supported part types.
3. Define a canonical allowed-value set for actions and part categories.
4. Validate dimensions, units, and optional fields explicitly.
5. Add strict conversion for unknown or deprecated fields.
6. Separate raw model output from validated application intent.
7. Add schema tests for valid and invalid examples.

## Recommended Schema Structure
- `CadIntent`
- `CadAction`
- `BasePartParameters`
- `PlateParameters`
- `BracketParameters`
- `WasherParameters`
- `FlangeParameters`
- `GussetParameters`
- `PartGeometry`
- `ValidationIssue`

## Deliverables
- Updated schema module.
- Validation tests.
- Migration notes for downstream code.

## Acceptance Criteria
- Invalid fields fail or are explicitly normalized.
- Part-type-specific parameters are type checked.
- The generation layer receives validated models only.
- Tests cover both acceptance and rejection cases.

## Agent Assignment
**Agent A2**: Redesign and harden the CAD intent schema layer.

---

# Phase 3: Persistent Session Store

## Objective
Store all user interactions, model outputs, and system outcomes durably.

## Why this is critical
Without persistent storage, there is no reliable dataset for training or evaluation.

## Minimum Data to Store
For every interaction, store:
- session id
- user id or anonymous session key
- timestamp
- user prompt
- provider used
- prompt version hash
- raw model output
- validated CadIntent JSON
- generated geometry metadata
- export metadata
- check results
- user corrections
- final accepted result flag
- error reason, if any

## Tasks
1. Design a persistence schema.
2. Implement a storage backend, preferably SQLite first.
3. Add repository methods for create/read/update queries.
4. Add migration logic or initialization scripts.
5. Replace in-memory session-only state with persisted records.
6. Preserve in-memory cache only as a performance layer, not source of truth.
7. Add recovery behavior for restarts.

## Suggested Tables
- `sessions`
- `interactions`
- `prompt_versions`
- `generated_parts`
- `check_results`
- `user_corrections`
- `exports`
- `provider_runs`

## Deliverables
- SQLite schema or equivalent file-backed store.
- Repository layer.
- Migration/init scripts.
- Persistence tests.

## Acceptance Criteria
- Restarting the backend does not lose session history.
- Every generated part can be traced back to its source prompt.
- User corrections are stored and queryable.
- The store supports dataset export without manual reconstruction.

## Agent Assignment
**Agent A3**: Build the persistent session and interaction store.

---

# Phase 4: Dataset Export Pipeline

## Objective
Convert stored interactions into training-ready examples.

## Dataset Philosophy
The training set should teach **intent extraction**, not geometry generation.

## Data to Export
Each training example should ideally contain:
- raw user prompt
- structured target intent
- normalized parameters
- provider label
- success/failure label
- correction history
- prompt version
- context window summary

## Export Formats
- JSONL for supervised fine-tuning.
- Parquet or CSV for analysis.
- Separate validation and test splits.

## Tasks
1. Define a canonical export schema.
2. Implement filtering for low-quality examples.
3. Implement deduplication.
4. Normalize units and dimension formats.
5. Strip unsafe or non-generalizable content.
6. Split by session or template family to prevent leakage.
7. Produce reproducible dataset versions.

## Quality Filters
Exclude or downweight examples that are:
- unresolved or ambiguous without correction.
- malformed.
- generated with broken geometry.
- too similar to another sample.
- contaminated by prompt bugs.

## Deliverables
- `scripts/export_training_data.py`
- JSONL export schema.
- Dataset versioning notes.
- Example exported files.

## Acceptance Criteria
- A reproducible export can be generated from raw logs.
- The export is clean enough for supervised training.
- Train/validation/test splits are traceable.

## Agent Assignment
**Agent A4**: Build the export and dataset curation pipeline.

---

# Phase 5: Retrieval Layer

## Objective
Add retrieval for engineering templates, standards, and prior examples.

## Important Design Choice
Do **not** start with general-purpose vector search as the only strategy. For this domain, structured retrieval by part type, standard, material, and constraint class is often more useful.

## Retrieval Sources
- part templates
- dimension heuristics
- manufacturing constraints
- hole/edge distance rules
- part family examples
- engineering standards excerpts
- internal design patterns

## Retrieval Modes
1. **Structured retrieval**
   - by part type
   - by material
   - by manufacturing process
   - by constraint class

2. **Semantic retrieval**
   - embeddings over text snippets
   - useful for fuzzy natural language queries

3. **Hybrid retrieval**
   - structured first, semantic second

## Tasks
1. Define retrieval document schema.
2. Build a template library.
3. Build an index over templates and rules.
4. Add retrieval API for prompt-time injection.
5. Add a caching layer for embeddings or query results.
6. Add guardrails so retrieval does not inject irrelevant instructions.
7. Add tests for top-k relevance and injection correctness.

## Deliverables
- `backend/app/services/nlp/retrieval.py`
- `backend/app/services/nlp/templates/`
- Retrieval index builder.
- Retrieval tests.

## Acceptance Criteria
- The backend can fetch relevant templates based on intent.
- Retrieved content is inserted into prompts in a controlled way.
- Retrieval improves or at least does not degrade parsing accuracy on a benchmark set.

## Agent Assignment
**Agent A5**: Implement retrieval infrastructure and template library.

---

# Phase 6: Local Intent Model

## Objective
Train and serve a local model that maps prompt + context to CadIntent.

## Scope Control
The local model should handle:
- intent classification
- part family selection
- parameter extraction
- constraint interpretation

It should **not** be responsible for geometry generation.

## Training Inputs
- user prompt
- optional session context summary
- optional retrieval snippets
- optional current part state

## Training Targets
- strict CadIntent JSON

## Model Strategy
Start with lightweight supervised fine-tuning:
- base model with instruction-following ability
- parameter-efficient tuning such as LoRA or QLoRA
- deterministic JSON output format

## Tasks
1. Select a suitable base model.
2. Build a training script.
3. Implement tokenizer/data formatting.
4. Add validation during training.
5. Save adapters and config.
6. Build an inference wrapper.
7. Add schema validation on inference output.
8. Add fallback to cloud provider if local output fails.

## Deliverables
- training script
- inference service
- adapter artifacts
- config files
- evaluation results

## Acceptance Criteria
- The local model can produce valid CadIntent JSON on held-out prompts.
- Output passes schema checks at a target success rate.
- Fallback behavior is reliable when local inference fails.

## Agent Assignment
**Agent A6**: Build the local fine-tuning and inference path.

---

# Phase 7: A/B Routing and Evaluation Harness

## Objective
Measure whether the local model is ready to share traffic with Gemini.

## Evaluation Dimensions
- schema validity
- parameter accuracy
- intent accuracy
- geometry success rate
- check pass rate
- correction frequency
- latency
- cost
- user acceptance rate

## Routing Modes
- provider-only
- shadow mode
- percentage-based A/B
- fallback-only local mode

## Tasks
1. Implement provider router.
2. Add experiment assignment strategy.
3. Log every route decision.
4. Create offline evaluation scripts.
5. Create regression test prompts.
6. Compare providers on the same benchmark set.
7. Define a rollout threshold for promotion.

## Deliverables
- routing service
- evaluation harness
- benchmark prompt set
- comparison reports

## Acceptance Criteria
- Every request is traceable to a route decision.
- Local model and Gemini can be compared on the same evaluation suite.
- Promotion to production requires metric thresholds, not intuition.

## Agent Assignment
**Agent A7**: Implement A/B routing and evaluation.

---

# Phase 8: Frontend and UX Alignment

## Objective
Make the UI reflect the backend’s new capabilities and storage semantics.

## Tasks
1. Display provider used for each run.
2. Show validation warnings and check results clearly.
3. Surface retrieved templates or engineering hints when available.
4. Allow user corrections to be explicitly captured.
5. Show when a request used local model vs cloud model.
6. Show versioned prompt or model metadata in debug mode.
7. Add a clear state for retry/fallback outcomes.

## Deliverables
- chat UI updates
- correction capture UI
- debug metadata panel
- route/status indicators

## Acceptance Criteria
- Users can see what the system did and why.
- Corrections can be saved with a single action.
- Frontend and backend agree on payload schema.

## Agent Assignment
**Agent A8**: Update the frontend for observability and correction capture.

---

# Phase 9: Testing and Quality Gates

## Objective
Prevent regression at every layer.

## Test Layers
### Unit tests
- schema validation
- prompt assembly
- retrieval ranking
- persistence repository methods
- export formatting
- routing decisions

### Integration tests
- end-to-end request flow
- provider fallback
- session persistence after restart
- dataset export from stored interactions
- local model inference + validation

### Regression tests
- known prompts that previously failed
- edge-case dimensions
- ambiguous requests
- material-specific constraints

### Performance tests
- parsing latency
- retrieval latency
- export throughput
- storage write/read throughput

## Quality Gates
A change may merge only if:
- tests pass
- prompt snapshots match intentionally changed versions
- schema checks pass
- persistence tests pass
- dataset export is reproducible

## Agent Assignment
**Agent A9**: Build and maintain the test suite and release gates.

---

# Phase 10: Deployment and Operations

## Objective
Make the system safe to run, inspect, and evolve.

## Tasks
1. Version prompt templates.
2. Version datasets.
3. Version model artifacts.
4. Version retrieval indexes.
5. Add logging with trace ids.
6. Add metrics for failures and latency.
7. Add feature flags for provider routing.
8. Add backup/export for the persistent store.
9. Document local setup and reproduction steps.

## Deliverables
- operational runbook
- artifact versioning scheme
- backup procedure
- recovery procedure
- environment configuration docs

## Acceptance Criteria
- A clean deployment can be reproduced from versioned artifacts.
- Backups can restore the session store.
- Debugging a failed request is possible from logs and stored traces.

## Agent Assignment
**Agent A10**: Own operationalization, versioning, and release procedure.

---

# Detailed Task Order
The work should proceed in this order:

1. Baseline audit.
2. Prompt consolidation.
3. Schema hardening.
4. Persistent storage.
5. Dataset export.
6. Retrieval layer.
7. Local model training.
8. A/B routing.
9. Frontend observability.
10. Testing and release hardening.
11. Deployment and maintenance.

This order is deliberate:
- You cannot train well without logs.
- You cannot compare providers without stable schemas.
- You cannot debug routing without consistent prompts.
- You cannot trust retrieval without a known template library.

---

# Cross-Cutting Requirements

## 1. Version Everything
Version these artifacts independently:
- prompts
- schemas
- datasets
- model weights/adapters
- retrieval indexes
- routing config
- export scripts

## 2. Keep Raw and Normalized Data Separate
Store both:
- raw model output
- validated normalized intent

This protects you from losing information during curation.

## 3. Make Fallbacks Explicit
Every failure should resolve into one of:
- retry
- schema correction
- fallback provider
- user clarification
- hard failure with reason

## 4. Prefer Structured Configuration Over Hidden Logic
Avoid hardcoding prompt fragments, route rules, or templates in multiple files.

## 5. Trace Every Generated Part
Every generated geometry artifact should be linkable back to:
- user request
- prompt version
- provider/model
- retrieval context
- validation result

---

# Definition of Done by Milestone

## Milestone 1: Logging Foundation
Done when:
- persistence works
- interactions survive restart
- logs are queryable

## Milestone 2: Clean Dataset Export
Done when:
- training JSONL can be exported reproducibly
- samples are filtered and deduplicated
- train/validation/test splits exist

## Milestone 3: Strict Intent Layer
Done when:
- invalid intent shapes are rejected
- downstream generation receives typed parameters only

## Milestone 4: Retrieval Prototype
Done when:
- template retrieval is available and measurable
- prompt injection is controlled

## Milestone 5: Local Intent Model
Done when:
- local model can match or approach cloud provider quality on held-out intent tasks
- fallback path is stable

## Milestone 6: A/B Evaluation
Done when:
- routing is measurable
- metrics support promotion or rollback decisions

---

# Suggested Agent Operating Contract
Every agent should follow the same contract.

## Before starting
- Read the current baseline docs.
- Identify dependencies.
- State the files to change.
- State the acceptance criteria.

## During implementation
- Make small, reviewable commits or patches.
- Add tests with the change.
- Avoid unrelated refactors.
- Preserve backward compatibility unless the plan explicitly allows a breaking change.

## Before handing off
- Run the relevant tests.
- Document what changed.
- Document any known limitation.
- List follow-up tasks if the change is partial.

---

# Recommended Immediate Next Actions
The next three actions should be:
1. Consolidate prompts into one builder.
2. Replace in-memory session state with persistent storage.
3. Export clean training data from real interactions.

These three unblock almost everything else.

---

# Final Summary
This project should be built in a data-centric order:
- stabilize the prompt layer,
- harden the schema,
- persist every interaction,
- export training data,
- add retrieval,
- train a local model,
- evaluate against the cloud baseline,
- and only then expand routing and optimization.

That sequence gives you a system that is measurable, trainable, and maintainable.

