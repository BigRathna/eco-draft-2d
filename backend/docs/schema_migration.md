# Schema Migration: Phase 2 Hardening

## Overview
Phase 2 introduces strict, part-specific models for CAD intent extraction. This replaces the previous loose `Dict[str, Any]` parameters with strongly typed Pydantic models.

## Changes

### 1. Enums
- **CadAction**: `create`, `modify`, `checkout`.
- **PartType**: `plate`, `gusset`, `bracket`, `washer`, `flange`, etc.

### 2. Hardened Parameter Models
Every part type now has its own Pydantic model in `backend/app/schemas/cad.py`:
- `PlateParameters`
- `BracketParameters` (Includes L, T, and Angle shapes)
- `WasherParameters` (Includes Spacers)
- `FlangeParameters`
- `GussetParameters`

These models enforce:
- **Positive Dimensions**: `width`, `height`, `diameter` must be `> 0`.
- **Geometric Consitency**: e.g., `inner_diameter < outer_diameter`.
- **Discriminated Union**: `CadParameters` automatically selects the correct model based on the `type` field.

### 3. Intent Separation
- **`CadIntent.parameters`**: Now keeps the **raw** LLM output for logging and traceability.
- **`CadIntent.validated_parameters`**: Contains the cleaned, unit-normalized, and strictly-typed parameter model.

## Downstream Impacts
- **Geometry Service**: Should now consume `intent.validated_parameters` instead of `intent.parameters.values`.
- **Check Engine**: No longer needs to "build" `PartGeometry` from raw dicts as validation is prefix-enforced.

## Normalization Logic
Messy LLM output is handled by `app.services.nlp.normalization.py`:
- `dia` -> `diameter`
- `thk` -> `thickness`
- `inch` -> `mm` (scaled by 25.4)
- `ft` -> `mm` (scaled by 304.8)
