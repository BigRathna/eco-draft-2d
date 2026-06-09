# Prompt Architectural Boundaries

This document defines the scope and boundaries of the NLP prompt system to ensure maintainability and prevent "prompt bloat".

## Out-of-Scope (Boundaries)

### 1. Geometric Validity Math
The prompt should **not** perform complex geometric calculations (e.g., calculating the Hypotenuse of a triangle or verifying if a hole fits inside a plate). These checks are handled by the `CheckEngine` in Phase 2.

### 2. Physical Simulation
The prompt is not responsible for predicting stress, strain, or weight. It only extracts parameters. Analysis is handled by the `AnalysisService`.

### 3. Optimization Logic
The prompt is not responsible for finding the "best" design. It only converts user requests like "optimize for mass" into structured optimization tasks.

### 4. CAD Export Generation
The prompt only produces the `CadIntent`. The actual generation of DXF/SVG files is strictly handled by the CAD primitives and exporters.

### 5. Final Manufacturability Approval
While the prompt sets default materials and dimensions, the final "Pass/Fail" on manufacturability is determined by the rule-based Check Engine, not the LLM's intuition.
