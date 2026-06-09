# Current Schema Map

Baseline date: 2026-06-09  
Baseline commit: `dc03d02` (`QoL changes`) with uncommitted working-tree changes present.

## Schema Files

### `backend/app/schemas/cad.py`
CAD intent and geometry models:

- `CadParameters`: `type: str`, `values: Dict[str, Any]`.
- `CadIntent`: `action` is limited to `create`, `modify`, `checkout`; includes optional `target_id`, `parameters`, and `rationale`.
- `CadState`: current part state container.
- `HoleFeature`: hole id, center, diameter.
- `PartGeometry`: canonical boundary, holes, material, and thickness.

Current strictness note: part type and parameter values are loose; arbitrary parameter keys and value types can pass through `CadParameters.values`.

### `backend/app/schemas/parts.py`
Part generation and export models:

- `BasePartParams`: material and thickness.
- `GussetParams`: typed gusset parameters.
- `BasePlateParams`: typed base-plate parameters.
- `GenericPartParams`: accepts extra fields.
- `PartGenerateRequest`: accepts typed gusset/base-plate params, generic params, or raw dicts.
- `GeneratedPart`: generated part metadata plus raw `geometry_data`.
- `ExportFile`: exported file metadata and base64 content.
- `PartGenerateResponse`: generated part, files, generation time, optional checks.

### `backend/app/schemas/common.py`
Shared primitives and enums:

- `Point2D`
- `Material`: `steel`, `aluminum`, `stainless_steel`
- `ManufacturingProcess`: `laser_cutting`, `waterjet`, `plasma`
- `FileFormat`: `dxf`, `svg`, `pdf`
- `APIResponse[T]`
- `GeometryInfo`
- `ValidationResult`

### `backend/app/schemas/checks.py`
Manufacturability schemas:

- `ManufacturabilityCheckRequest`
- `CheckResult`
- `ManufacturabilityCheckResponse`

### `backend/app/schemas/analysis.py`
Stress-analysis request and result models.

### `backend/app/schemas/lca.py`
Lifecycle assessment request and response models.

### `backend/app/schemas/drawing.py`
Technical drawing request/response models:

- `TitleBlock`
- `DrawingRequest`
- `DrawingResponse`

### `backend/app/schemas/optimization.py`
Full optimization schema set for NSGA-II-style requests and responses.

### `backend/app/schemas/optimization_simple.py`
Frontend-oriented simple optimization response:

- `OptimizationPoint`
- `SimpleOptimizationResponse`

### `backend/app/schemas/session.py`
Session graph models:

- `SessionEvent`
- `SessionGraph`

### `backend/app/schemas/nlp.py`
Prompt infrastructure models:

- `PromptLayer`
- `PromptBundle`
- `PromptVersion`

## API Response Envelope

Most typed endpoints return `APIResponse[T]`:

```json
{
  "success": true,
  "message": "...",
  "data": {},
  "errors": null
}
```

`/chat/parse` is an exception: it returns a plain dict with `success` and either `data` or `error`.

## Generated Output Formats

### Part Generation

Endpoint: `POST /api/v1/part/generate`

Output schema: `APIResponse[PartGenerateResponse]`

Generated payload includes:

- `part.part_type`
- `part.geometry_info`
- `part.geometry_data`
- `part.material`
- `part.thickness`
- `part.mass`
- `files[]`
- `generation_time_ms`
- `checks`

### Exported Files

`backend/app/services/io/exporters.py` supports:

- DXF via `FileFormat.DXF`
- SVG via `FileFormat.SVG`

Each exported file is represented as:

- `format`
- `filename`
- `content_base64`
- `size_bytes`

PDF export is produced through `backend/app/services/drawing/pdf.py` and returned by `POST /api/v1/drawing/build` as `DrawingResponse` with `content_base64`.

### DXF Upload

Endpoint: `POST /api/v1/part/upload`

Returns a generated-part-style response for imported DXF geometry and exports SVG/DXF previews.

### Checks

Endpoint: `POST /api/v1/part/check`

Output schema: `APIResponse[ManufacturabilityCheckResponse]`.

### Analysis

Endpoint: `POST /api/v1/part/analyze`

Current route returns simplified dict fields:

- `max_stress`
- `safety_factor`
- `critical_locations`

### LCA

Endpoint: `POST /api/v1/part/lca`

Disabled by default through `settings.enable_lca = False`.

### Optimization

Endpoint: `POST /api/v1/opt/run`

Output schema: `APIResponse[SimpleOptimizationResponse]`.

### Session Graph

Endpoints:

- `GET /api/v1/sessions/current/graph`
- `POST /api/v1/sessions/current/checkout`
- `GET /api/v1/sessions/current/visualize`

## Known Schema Limitations

- Intent parameters are not strict per part type.
- `GenericPartParams` allows additional fields.
- Some endpoints use raw `Dict[str, Any]` request/response structures.
- `/chat/parse` does not use an explicit Pydantic request/response schema.
- `PartGenerateRequest.parameters` allows raw dicts, which weakens validation.
