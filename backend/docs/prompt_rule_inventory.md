# Prompt Rule Inventory

This inventory documents all engineering rules and constraints injected into the LLM prompts to ensure consistent CAD part generation.

## 1. Unit Rules
- **Canonical Unit**: Millimeters (mm).
- **Auto-Conversion**: Any input in meters, centimeters, inches, or feet must be converted to mm before being returned in the JSON parameters.
- **Precision**: Dimensions should be treated as floats.

## 2. Part-Specific Rules
### Plates
- Default shape: `rectangle`.
- Required parameters: `width`, `height`, `thickness`.
- Optional features: `hole_diameter`, `hole_spacing`.

### Gussets
- Default shape: `triangle`.
- Required parameters: `width`, `height`, `thickness`.
- Construction: Typically a right-angled triangle unless specified.

### Brackets
- Default shape: `L`.
- Required parameters: `width`, `height`, `leg_length`, `thickness`.

## 3. Extraction Logic
- **Action Selection**: 
    - `create`: New part or significant change.
    - `modify`: Incremental update to current part.
    - `checkout`: Reverting to a specific ID from session history.
- **Parameter Inheritance**: Modification requests must inherit all unchanged parameters from the current state.
- **Standard Names**: Always use internal standard names (e.g., `hole_diameter` instead of `bore`).
