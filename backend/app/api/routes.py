"""API routes for Eco Draft 2D."""

import time
from typing import Dict, Any, Union

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from app.schemas import (
    PartGenerateRequest, PartGenerateResponse, GussetParams, BasePlateParams, GenericPartParams,
    ManufacturabilityCheckRequest, ManufacturabilityCheckResponse,
    AnalysisRequest, AnalysisResponse,
    LCARequest, LCAResponse,
    DrawingRequest, DrawingResponse,
    OptimizationRequest, OptimizationResponse,
    APIResponse
)
from app.schemas.optimization_simple import SimpleOptimizationResponse, OptimizationPoint
from app.services.cad import GussetGenerator, BasePlateGenerator, UniversalPartGenerator
from app.services.checks import ManufacturabilityChecker
from app.services.analysis import AnalyticAnalyzer
from app.services.lca import SimpleLCACalculator
from app.services.drawing import PDFDrawingGenerator
from app.services.io import FileExporter
from app.services.opt import NSGA2Optimizer
from app.schemas.parts import GeneratedPart
from app.services import nlp


# Create router
router = APIRouter()


@router.post("/part/generate", response_model=APIResponse[PartGenerateResponse])
async def generate_part(request: PartGenerateRequest) -> APIResponse[PartGenerateResponse]:
    """Generate 2D part geometry and export to specified formats."""
    try:
        start_time = time.time()

        # Create universal generator for any part type
        print(f"🏗️ API: Creating generator for part_type='{request.part_type}'")
        
        # Convert parameters to dict if needed
        if isinstance(request.parameters, dict):
            params_dict = request.parameters
        else:
            # Handle legacy Pydantic models
            params_dict = request.parameters.dict() if hasattr(request.parameters, 'dict') else dict(request.parameters)
        
        # Use universal generator for all part types
        generator = UniversalPartGenerator(request.part_type, params_dict)
        params = generator.params  # Get the processed parameters with defaults

        # Generate geometry
        geometry, geometry_data = generator.generate_geometry()

        # Calculate mass
        area = geometry_data.get("area", 0.0)
        mass = generator.calculate_mass(area)

        # Create geometry info from generator
        geometry_info = generator._calculate_geometry_info(geometry)

        # Create generated part info
        # Handle both dict-style and object-style parameter access
        material = params.get("material", "steel") if isinstance(params, dict) else getattr(params, "material", "steel")
        thickness = params.get("thickness", 5.0) if isinstance(params, dict) else getattr(params, "thickness", 5.0)
        
        generated_part = GeneratedPart(
            part_type=request.part_type,
            geometry_info=geometry_info,
            material=material,
            thickness=thickness,
            mass=mass
        )

        # Export to requested formats
        exporter = FileExporter(geometry_data)
        exported_files = exporter.export_formats(
            request.export_formats, request.part_type)

        end_time = time.time()
        generation_time_ms = (end_time - start_time) * 1000

        response_data = PartGenerateResponse(
            part=generated_part,
            files=exported_files,
            generation_time_ms=generation_time_ms
        )

        return APIResponse(
            success=True,
            message="Part generated successfully",
            data=response_data
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate part: {str(e)}"
        )


@router.post("/part/check", response_model=APIResponse[ManufacturabilityCheckResponse])
async def check_manufacturability(request: ManufacturabilityCheckRequest) -> APIResponse[ManufacturabilityCheckResponse]:
    """Perform manufacturability checks on part geometry."""
    try:
        checker = ManufacturabilityChecker(request)
        result = checker.check_manufacturability()

        return APIResponse(
            success=True,
            message="Manufacturability check completed",
            data=result
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform manufacturability check: {str(e)}"
        )


@router.post("/part/analyze", response_model=APIResponse[Dict[str, Any]])
async def analyze_stress(request: AnalysisRequest) -> APIResponse[Dict[str, Any]]:
    """Perform analytic stress analysis on part."""
    try:
        analyzer = AnalyticAnalyzer(request)
        result = analyzer.analyze()
        
        # Transform to simplified format expected by frontend
        # Get the first (or most critical) result
        if result.results:
            first_result = result.results[0]
            max_stress_pa = first_result.max_stress
            max_stress_mpa = max_stress_pa / 1e6  # Convert Pa to MPa
            
            # Create simplified response matching frontend expectations
            simplified = {
                "max_stress": max_stress_mpa,
                "safety_factor": first_result.safety_factor,
                "critical_locations": [
                    {
                        "x": first_result.stress_location.x,
                        "y": first_result.stress_location.y,
                        "stress": max_stress_mpa
                    }
                ]
            }
        else:
            # Default values if no results
            simplified = {
                "max_stress": 0.0,
                "safety_factor": 1000000.0,  # Very high safety factor
                "critical_locations": []
            }

        return APIResponse(
            success=True,
            message="Stress analysis completed",
            data=simplified
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform stress analysis: {str(e)}"
        )


@router.post("/part/lca", response_model=APIResponse[LCAResponse])
async def calculate_lca(request: LCARequest) -> APIResponse[LCAResponse]:
    """Calculate life cycle assessment metrics."""
    try:
        calculator = SimpleLCACalculator(request)
        result = calculator.calculate_lca()

        return APIResponse(
            success=True,
            message="LCA calculation completed",
            data=result
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate LCA: {str(e)}"
        )


@router.post("/drawing/build", response_model=APIResponse[DrawingResponse])
async def generate_drawing(request: DrawingRequest) -> APIResponse[DrawingResponse]:
    """Generate technical drawing PDF with dimensions and title block."""
    try:
        generator = PDFDrawingGenerator(request)
        result = generator.generate_drawing()

        return APIResponse(
            success=True,
            message="Drawing generated successfully",
            data=result
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate drawing: {str(e)}"
        )


@router.post("/opt/run", response_model=APIResponse[SimpleOptimizationResponse])
async def run_optimization(request: Dict[str, Any]) -> APIResponse[SimpleOptimizationResponse]:
    """Run NSGA-II multi-objective optimization."""
    try:
        # For now, return mock optimization data for testing
        # TODO: Implement actual NSGA-II optimization with pymoo
        import random
        import numpy as np
        
        # Generate mock Pareto front
        num_points = 20
        points = []
        pareto_optimal = []
        
        for i in range(num_points):
            # Generate points with trade-offs
            mass = random.uniform(0.5, 5.0)
            cost = random.uniform(10, 100)
            strength = random.uniform(100, 500)
            carbon = random.uniform(0.1, 10.0)
            
            # Make some points Pareto optimal (lower mass/cost)
            if i < 8:
                mass *= 0.7
                cost *= 0.8
                pareto_optimal.append(i)
            
            point = OptimizationPoint(
                objectives={
                    "mass": mass,
                    "cost": cost,
                    "strength": strength,
                    "carbon_footprint": carbon
                },
                parameters={
                    "thickness": random.uniform(3, 10),
                    "width": random.uniform(50, 200),
                    "height": random.uniform(50, 200)
                }
            )
            points.append(point)
        
        result = SimpleOptimizationResponse(
            points=points,
            pareto_optimal=pareto_optimal,
            optimization_time_ms=random.uniform(1000, 5000)
        )
        
        return APIResponse(
            success=True,
            message="Optimization completed (mock data)",
            data=result
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run optimization: {str(e)}"
        )


@router.get("/materials", response_model=APIResponse[Dict[str, Any]])
async def get_materials() -> APIResponse[Dict[str, Any]]:
    """Get available materials and their properties."""
    from app.core.config import settings

    return APIResponse(
        success=True,
        message="Materials retrieved successfully",
        data=settings.materials
    )


@router.get("/manufacturing", response_model=APIResponse[Dict[str, Any]])
async def get_manufacturing_processes() -> APIResponse[Dict[str, Any]]:
    """Get available manufacturing processes and their constraints."""
    from app.core.config import settings

    return APIResponse(
        success=True,
        message="Manufacturing processes retrieved successfully",
        data=settings.manufacturing
    )


@router.post("/chat/parse")
async def parse_chat_message(request: Dict[str, str]) -> Dict[str, Any]:
    """Parse a user chat message into structured engineering parameters using LLM."""
    user_message = request.get("message", "")
    print(f"📨 API: Received chat/parse request: '{user_message}'")
    
    if not user_message:
        return {"error": "No message provided."}
    try:
        # Parse the message using NLP
        print("🚀 API: Calling Gemini AI to parse message...")
        result = nlp.parse_engineering_request(user_message)
        print(f"✅ API: Gemini AI returned: {result}")
        
        # Apply parameter defaults for missing required fields
        result = nlp.apply_parameter_defaults(result)
        print(f"🔧 API: After applying defaults: {result}")
        
        return {"success": True, "data": result}
    except Exception as e:
        print(f"❌ API: Error in chat/parse: {str(e)}")
        return {"success": False, "error": str(e)}
