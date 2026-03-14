"""Pydantic schemas for Eco Draft 2D API."""

from .parts import (
    PartGenerateRequest,
    PartGenerateResponse,
    BasePartParams,
    GussetParams,
    BasePlateParams,
    GenericPartParams,
)
from .checks import (
    ManufacturabilityCheckRequest,
    ManufacturabilityCheckResponse,
    CheckResult,
)
from .analysis import (
    AnalysisRequest,
    AnalysisResponse,
    StressResult,
)
from .lca import (
    LCARequest,
    LCAResponse,
    MaterialData,
)
from .drawing import (
    DrawingRequest,
    DrawingResponse,
    TitleBlock,
)
from .optimization import (
    OptimizationRequest,
    OptimizationResponse,
    OptimizationResult,
)
from .common import (
    Point2D,
    Material,
    ManufacturingProcess,
    FileFormat,
    APIResponse,
)

__all__ = [
    # Parts
    "PartGenerateRequest",
    "PartGenerateResponse", 
    "BasePartParams",
    "GussetParams",
    "BasePlateParams",
    "GenericPartParams",
    # Checks
    "ManufacturabilityCheckRequest",
    "ManufacturabilityCheckResponse",
    "CheckResult",
    # Analysis
    "AnalysisRequest",
    "AnalysisResponse",
    "StressResult",
    # LCA
    "LCARequest",
    "LCAResponse",
    "MaterialData",
    # Drawing
    "DrawingRequest",
    "DrawingResponse",
    "TitleBlock",
    # Optimization
    "OptimizationRequest",
    "OptimizationResponse",
    "OptimizationResult",
    # Common
    "Point2D",
    "Material",
    "ManufacturingProcess",
    "FileFormat",
    "APIResponse",
]
