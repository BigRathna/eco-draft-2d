"""API routes for Eco Draft 2D."""

import time
from typing import Dict, Any, Union, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import ValidationError, BaseModel

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
from app.services.checks import CheckEngine
from app.services.analysis import AnalyticAnalyzer
from app.services.lca import SimpleLCACalculator
from app.services.drawing import PDFDrawingGenerator
from app.services.io import FileExporter
from app.services.opt import NSGA2Optimizer
from app.schemas.parts import GeneratedPart
from app.services import nlp
from fastapi.responses import HTMLResponse
from app.services.session.store import tracker
from app.schemas.session import SessionGraph
from app.schemas.common import GeometryInfo, Point2D
from app.services.cad.importer import DxfImporter
from pydantic import BaseModel

class CheckoutRequest(BaseModel):
    version: str


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
        geometry, geometry_data, part_geometry = generator.generate_geometry()

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
            geometry_data=geometry_data,
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
        
        # Optionally run checks on part generation
        check_request = ManufacturabilityCheckRequest(
            part_type=request.part_type,
            geometry_data=geometry_data,
            manufacturing_process="laser_cutting",  # Defaulting, as we don't have this in basic request
            thickness=thickness,
            part_geometry=part_geometry
        )
        engine = CheckEngine()
        checks = engine.run(check_request)

        response_data = PartGenerateResponse(
            part=generated_part,
            files=exported_files,
            generation_time_ms=generation_time_ms,
            checks=checks
        )

        tracker.log_event(
            action_type="GENERATE",
            parameters=request.parameters.model_dump() if hasattr(request.parameters, 'model_dump') else request.parameters,
            geometry_data=geometry_data,
            metrics={"checking_rules": len(checks.results) if hasattr(checks, 'results') else 0}
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


@router.post("/part/upload", response_model=APIResponse[PartGenerateResponse])
async def upload_dxf_part(
    file: UploadFile = File(...)
) -> APIResponse[PartGenerateResponse]:
    """Import DXF files and inject them directly into root session streams."""
    try:
        content = await file.read()
        importer = DxfImporter(content)
        geometry_data = importer.extract_geometry()
        
        area_m2 = geometry_data.get("area", 0) / 1_000_000
        mass_kg = area_m2 * (5.0 / 1000) * 7850
        
        exporter = FileExporter(geometry_data)
        files = exporter.export_formats(["svg", "dxf"], part_type="imported_dxf")
        
        bounds = geometry_data.get("bounds", [0, 0, 100, 100])
        centroid_dict = geometry_data.get("centroid", {"x": 50, "y": 50})
        
        geometry_info = GeometryInfo(
            area=geometry_data.get("area", 0.0),
            perimeter=geometry_data.get("perimeter", 0.0),
            centroid=Point2D(x=centroid_dict.get("x", 0), y=centroid_dict.get("y", 0)),
            bounding_box=(
                Point2D(x=bounds[0], y=bounds[1]),
                Point2D(x=bounds[2], y=bounds[3])
            )
        )

        metadata = {
            "filename": file.filename,
            "imported": True
        }
        
        tracker.log_event(
            action_type="GENERATE",
            parameters=geometry_data.get("parameters", {}),
            geometry_data=geometry_data,
            metrics={"imported": True}
        )
        
        response_data = PartGenerateResponse(
            part={
                "part_type": "DXF Layout",
                "parameters": geometry_data.get("parameters", {}),
                "geometry_data": geometry_data,
                "material": "steel",
                "thickness": 5.0,
                "mass": mass_kg,
                "geometry_info": geometry_info
            },
            files=files,
            generation_time_ms=0.0
        )
        
        return APIResponse(
            success=True,
            message="DXF successfully uploaded.",
            data=response_data
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process uploaded DXF: {str(e)}"
        )


@router.post("/part/check", response_model=APIResponse[ManufacturabilityCheckResponse])
async def check_manufacturability(request: ManufacturabilityCheckRequest) -> APIResponse[ManufacturabilityCheckResponse]:
    """Perform manufacturability checks on part geometry."""
    try:
        engine = CheckEngine()
        result = engine.run(request)

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
            max_stress_mpa = first_result.max_stress  # It is already calculated in MPa
            
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
    if not settings.enable_lca:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Environmental LCA module is natively disabled by system configuration."
        )
        
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
        part_type = request.get("part_type")
        parameters = request.get("parameters", {})
        objectives = request.get("objectives", ["mass", "cost"])
        
        if not part_type:
            raise ValueError("part_type is required for optimization")
            
        from app.services.opt.simple_sampler import SimpleSamplerOptimizer
        
        optimizer = SimpleSamplerOptimizer(part_type, parameters, objectives)
        result = optimizer.run(num_samples=50)
        
        tracker.log_event(
            action_type="OPTIMIZE",
            parameters=parameters,
            metrics={"objectives": objectives, "samples": len(result.points)}
        )
        
        return APIResponse(
            success=True,
            message=f"Optimization completed. Found {len(result.points)} samples.",
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
def parse_chat_message(request: Dict[str, str]) -> Dict[str, Any]:
    """Parse a user chat message into structured engineering parameters using LLM."""
    user_message = request.get("message", "")
    print(f"📨 API: Received chat/parse request: '{user_message}'")
    
    if not user_message:
        return {"error": "No message provided."}
    try:
        # Parse the message using NLP
        print("🚀 API: Calling AI to parse message...")
        provider = request.get("provider", "gemini")
        intent = nlp.parse_engineering_request(user_message, provider=provider)
        print(f"✅ API: {provider.upper()} returned CadIntent: {intent}")
        
        if intent.action == "checkout" and getattr(intent, "target_id", None):
            checked_out = tracker.checkout_event(intent.target_id)
            if checked_out and checked_out.parameters:
                from app.services.cad import UniversalPartGenerator
                from app.services.io import FileExporter
                
                # Instantly rebuild lightweight SVG graph for fast-checkout
                p_type = checked_out.parameters.get("part_type", "plate")
                gen = UniversalPartGenerator(p_type, checked_out.parameters)
                _, geom_data, _ = gen.generate_geometry()
                exp = FileExporter(geom_data)
                svg_f = exp.export_formats(["svg"], p_type)[0]
                
                return {
                    "success": True, 
                    "data": {
                        "action": "checkout",
                        "target_event_id": checked_out.event_id,
                        "part_type": p_type,
                        "parameters": checked_out.parameters,
                        "cached_data": {
                            "version": checked_out.version,
                            "material": checked_out.parameters.get("material", "steel"),
                            "thickness": checked_out.parameters.get("thickness", 5.0),
                            "svg": svg_f["content_base64"]
                        }
                    }
                }
            
        tracker.log_event(
            action_type="NLP_INTENT",
            prompt=user_message,
            rationale=getattr(intent, "rationale", ""),
            parameters=intent.parameters.values
        )
        
        return {"success": True, "data": {
            "action": intent.action,
            "part_type": intent.parameters.type,
            "parameters": intent.parameters.values,
            "rationale": intent.rationale,
            "export_formats": ["svg", "dxf"]
        }}
    except Exception as e:
        print(f"❌ API: Error in chat/parse: {str(e)}")
        return {"success": False, "error": str(e)}

@router.get("/sessions/current/graph", response_model=APIResponse[SessionGraph])
async def get_session_graph() -> APIResponse[SessionGraph]:
    """Export the chronological telemetry graph of the active design session."""
    graph = tracker.export_graph()
    return APIResponse(
        success=True,
        message="Session graph exported successfully",
        data=graph
    )

@router.post("/sessions/current/checkout")
async def checkout_session_version(request: CheckoutRequest):
    """Directly checkout an older semantic version from the UI dropdown."""
    checked_out = tracker.checkout_event(request.version)
    if checked_out and checked_out.parameters:
        from app.services.cad.universal import UniversalPartGenerator
        from app.services.io.exporters import FileExporter
        from app.schemas.common import FileFormat
        
        p_type = checked_out.parameters.get("part_type", "plate")
        geom_data = checked_out.geometry_data or {}
        
        if not geom_data:
            gen = UniversalPartGenerator(p_type, checked_out.parameters)
            _, geom_data, _ = gen.generate_geometry()
            
        exp = FileExporter(geom_data)
        svg_f = exp.export_formats([FileFormat.SVG], p_type)[0]
        
        return APIResponse(
            success=True,
            message=f"Checked out version {checked_out.version}",
            data={
                "action": "checkout",
                "target_event_id": checked_out.event_id,
                "part_type": p_type,
                "parameters": checked_out.parameters,
                "geometry_data": geom_data,
                "cached_data": {
                    "version": checked_out.version,
                    "material": checked_out.parameters.get("material", "steel"),
                    "thickness": checked_out.parameters.get("thickness", 5.0),
                    "svg": svg_f.content_base64
                }
            }
        )
    raise HTTPException(status_code=404, detail="Version not found or has no geometric parameters")

@router.get("/sessions/current/visualize", response_class=HTMLResponse)
async def visualize_session_graph():
    """Returns an interactive HTML/JS visualization of the current session graph."""
    graph = tracker.export_graph()
    
    # Build nodes and edges for vis.js
    nodes = []
    edges = []
    
    for event in graph.events:
        nodes.append({
            "id": event.event_id,
            "label": f"{event.action_type}\n{event.timestamp.strftime('%H:%M:%S')}",
            "title": f"Prompt: {event.prompt or 'None'}\nRationale: {event.rationale or 'None'}",
            "shape": "box",
            "color": "#4f46e5" if event.action_type == "GENERATE" else "#10b981" if event.action_type == "OPTIMIZE" else "#f59e0b"
        })
        if event.parent_event_id:
            edges.append({
                "from": event.parent_event_id,
                "to": event.event_id,
                "arrows": "to"
            })
            
    import json
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Eco Draft 2D - Session Graph</title>
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <style type="text/css">
            body {{ font-family: sans-serif; background: #0f172a; color: white; margin: 0; padding: 0; }}
            #mynetwork {{ width: 100vw; height: 100vh; }}
            .header {{ position: absolute; top: 20px; left: 20px; z-index: 10; background: rgba(0,0,0,0.5); padding: 15px; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h3>Machine Learning Telemetry Graph</h3>
            <p>Session ID: {graph.session_id}</p>
        </div>
        <div id="mynetwork"></div>
        <script type="text/javascript">
            var nodes = new vis.DataSet({nodes_json});
            var edges = new vis.DataSet({edges_json});
            var container = document.getElementById('mynetwork');
            var data = {{ nodes: nodes, edges: edges }};
            var options = {{
                layout: {{ hierarchical: {{ direction: "UD", sortMethod: "directed" }} }},
                physics: {{ enabled: false }},
                nodes: {{ font: {{ color: '#ffffff' }} }}
            }};
            var network = new vis.Network(container, data, options);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
