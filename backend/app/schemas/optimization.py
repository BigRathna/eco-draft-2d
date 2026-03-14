"""Schemas for multi-objective optimization."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from .common import Material, ManufacturingProcess
from .analysis import LoadCase


class OptimizationConstraint(BaseModel):
    """Constraint for optimization."""
    name: str = Field(..., description="Constraint name")
    type: str = Field(..., description="Constraint type (stress, deflection, etc.)")
    value: float = Field(..., description="Constraint value")
    operator: str = Field("<=", description="Constraint operator (<=, >=, ==)")
    

class OptimizationVariable(BaseModel):
    """Design variable for optimization."""
    name: str = Field(..., description="Variable name")
    min_value: float = Field(..., description="Minimum value")
    max_value: float = Field(..., description="Maximum value")
    initial_value: Optional[float] = Field(None, description="Initial value")
    

class OptimizationObjective(BaseModel):
    """Optimization objective."""
    name: str = Field(..., description="Objective name")
    type: str = Field(..., description="Objective type (minimize, maximize)")
    weight: float = Field(1.0, description="Objective weight", gt=0)
    

class OptimizationRequest(BaseModel):
    """Request for multi-objective optimization."""
    part_type: str = Field(..., description="Type of part to optimize")
    material: Material = Field(..., description="Part material")
    manufacturing_process: ManufacturingProcess = Field(..., description="Manufacturing process")
    thickness: float = Field(..., description="Part thickness in mm", gt=0)
    
    # Design variables
    variables: List[OptimizationVariable] = Field(..., description="Design variables", min_items=1)
    
    # Objectives
    objectives: List[OptimizationObjective] = Field(
        default=[
            OptimizationObjective(name="mass", type="minimize"),
            OptimizationObjective(name="co2_emissions", type="minimize")
        ],
        description="Optimization objectives"
    )
    
    # Constraints
    constraints: List[OptimizationConstraint] = Field(default_factory=list, description="Design constraints")
    
    # Load cases for stress constraints
    load_cases: List[LoadCase] = Field(default_factory=list, description="Load cases for stress analysis")
    
    # Algorithm settings
    population_size: int = Field(100, description="Population size", gt=0)
    generations: int = Field(50, description="Number of generations", gt=0)
    crossover_prob: float = Field(0.9, description="Crossover probability", ge=0, le=1)
    mutation_prob: float = Field(0.1, description="Mutation probability", ge=0, le=1)
    

class OptimizationSolution(BaseModel):
    """Single solution from optimization."""
    variables: Dict[str, float] = Field(..., description="Design variable values")
    objectives: Dict[str, float] = Field(..., description="Objective function values")
    constraints: Dict[str, float] = Field(..., description="Constraint values")
    feasible: bool = Field(..., description="Whether solution is feasible")
    rank: int = Field(..., description="Pareto rank")
    crowding_distance: float = Field(..., description="Crowding distance")
    

class OptimizationResult(BaseModel):
    """Result of optimization run."""
    solutions: List[OptimizationSolution] = Field(..., description="Pareto optimal solutions")
    best_compromise: OptimizationSolution = Field(..., description="Best compromise solution")
    convergence_data: Dict[str, List[float]] = Field(..., description="Convergence history")
    statistics: Dict[str, Any] = Field(..., description="Optimization statistics")
    

class OptimizationResponse(BaseModel):
    """Response from optimization."""
    result: OptimizationResult = Field(..., description="Optimization results")
    algorithm_info: Dict[str, Any] = Field(..., description="Algorithm information")
    optimization_time_ms: float = Field(..., description="Time taken for optimization in milliseconds")
    total_evaluations: int = Field(..., description="Total function evaluations")
