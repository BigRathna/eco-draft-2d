# Baseline: Phase 1 Prompt Architecture (v0.1.0)

This document serves as the official baseline for the CAD Assistant Prompt System as of the completion of Phase 1.

## 1. Versioning
- **Prompt Version**: `0.1.0` (Hardcoded in `prompts.py`)
- **Integrity Tracking**: Every `PromptBundle` generates a SHA-256 hash of its normalized layers for exact-state tracking.

## 2. Core Architecture
- **Canonical Bundle**: `PromptBundle` schema in `app/schemas/nlp.py`.
- **Modular Layers**: Assembled by `PromptBuilder` (`app/services/nlp/prompt_builder.py`).
- **Adapter Logic**: Decoupled via `ProviderAdapter` (`app/services/nlp/adapters.py`).

## 3. Engineering Constraints (v0.1.0)
- **Units**: 1000mm base unit. Explicit multi-unit conversion rules included in all prompts.
- **Parts**: Support for `plate`, `gusset`, `bracket`, `washer`, `flange`, `spacer`.
- **Extraction**: JSON-only extraction for OpenAI-compatible models; Tool-use for Gemini.

## 4. Test Baseline
The following tests define the functional contract for this version:
- `backend/tests/test_prompts.py`: Unit tests for layer assembly and version stability.
- `backend/tests/test_nlp_integration.py`: End-to-end mocking of provider payloads and context survival.

## 5. Adapter Contracts
- **GeminiAdapter**: Produces a concatenated string of all layers.
- **OpenAICompatibleAdapter**: Produces a 2-message list (Role: System, Content: All Layers + JSON Schema | Role: User, Content: User Message).

---
*This baseline is archived to ensure regression testing remains possible after Phase 2 schema hardening alters prompt constraints.*
