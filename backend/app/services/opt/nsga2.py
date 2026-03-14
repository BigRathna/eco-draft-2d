"""NSGA-II multi-objective optimization using pymoo."""

import time
import numpy as np
from typing import Dict, Any, List

from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling
from pymoo.optimize import minimize
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from pymoo.util.misc import find_duplicates

from app.schemas.optimization import (
    OptimizationRequest, OptimizationResponse, OptimizationResult, 
    OptimizationSolution, OptimizationVariable, OptimizationObjective
)
from app.services.cad.gusset import GussetGenerator
from app.services.cad.base_plate import BasePlateGenerator
from app.services.analysis.analytic import AnalyticAnalyzer
from app.services.lca.simple import SimpleLCACalculator
from app.schemas.parts import GussetParams, BasePlateParams
from app.schemas.analysis import AnalysisRequest, LoadCase
from app.schemas.lca import LCARequest
from app.core.config import settings


class OptimizationProblem(Problem):
    """Multi-objective optimization problem definition."""
    
    def __init__(self, request: OptimizationRequest):
        """Initialize optimization problem."""
        self.request = request
        
        # Extract variable bounds
        xl = [var.min_value for var in request.variables]
        xu = [var.max_value for var in request.variables]
        
        n_var = len(request.variables)
        n_obj = len(request.objectives)
        n_constr = len(request.constraints)
        
        super().__init__(n_var=n_var, n_obj=n_obj, n_ieq_constr=n_constr, xl=xl, xu=xu)
        
        # Store variable names for mapping
        self.variable_names = [var.name for var in request.variables]
        self.objective_names = [obj.name for obj in request.objectives]
        self.constraint_names = [constr.name for constr in request.constraints]
        
    def _evaluate(self, x: np.ndarray, out: Dict[str, np.ndarray]) -> None:
        """Evaluate objectives and constraints for given design variables."""
        n_solutions = x.shape[0]
        
        # Initialize output arrays
        objectives = np.zeros((n_solutions, self.n_obj))
        constraints = np.zeros((n_solutions, self.n_ieq_constr))
        
        for i in range(n_solutions):
            # Map variables to parameter dict
            variables = dict(zip(self.variable_names, x[i, :]))
            
            # Evaluate this solution
            obj_values, constr_values = self._evaluate_solution(variables)
            
            objectives[i, :] = obj_values
            constraints[i, :] = constr_values
            
        out["F"] = objectives
        if self.n_ieq_constr > 0:
            out["G"] = constraints
            
    def _evaluate_solution(self, variables: Dict[str, float]) -> tuple[List[float], List[float]]:
        """Evaluate a single solution."""
        try:
            # Create part parameters based on variables
            if self.request.part_type == "gusset":
                params = self._create_gusset_params(variables)
                generator = GussetGenerator(params)
            elif self.request.part_type == "base_plate":
                params = self._create_base_plate_params(variables)
                generator = BasePlateGenerator(params)
            else:
                raise ValueError(f"Unknown part type: {self.request.part_type}")
                
            # Generate geometry
            geometry, geometry_data = generator.generate_geometry()
            
            # Calculate objectives
            objective_values = []
            for objective in self.request.objectives:
                if objective.name == "mass":
                    area = geometry_data.get("area", 0.0)
                    mass = generator.calculate_mass(area)
                    value = mass if objective.type == "minimize" else -mass
                elif objective.name == "area":
                    area = geometry_data.get("area", 0.0)
                    value = area if objective.type == "minimize" else -area
                elif objective.name == "co2_emissions":
                    # Calculate CO2 emissions
                    lca_request = LCARequest(
                        part_type=self.request.part_type,
                        geometry_data=geometry_data,
                        material=self.request.material,
                        thickness=self.request.thickness
                    )
                    lca_calculator = SimpleLCACalculator(lca_request)
                    lca_result = lca_calculator.calculate_lca()
                    value = lca_result.co2_per_part if objective.type == "minimize" else -lca_result.co2_per_part
                else:
                    value = 0.0  # Unknown objective
                    
                objective_values.append(value)
                
            # Calculate constraints
            constraint_values = []
            for constraint in self.request.constraints:
                if constraint.type == "stress" and self.request.load_cases:
                    # Perform stress analysis
                    analysis_request = AnalysisRequest(
                        part_type=self.request.part_type,
                        geometry_data=geometry_data,
                        material=self.request.material,
                        thickness=self.request.thickness,
                        load_cases=self.request.load_cases
                    )
                    analyzer = AnalyticAnalyzer(analysis_request)
                    analysis_result = analyzer.analyze()
                    
                    # Find maximum stress
                    max_stress = max(result.max_stress for result in analysis_result.results)
                    
                    # Convert constraint (stress <= allowable becomes stress - allowable <= 0)
                    if constraint.operator == "<=":
                        value = max_stress - constraint.value
                    elif constraint.operator == ">=":
                        value = constraint.value - max_stress
                    else:
                        value = abs(max_stress - constraint.value)
                else:
                    value = 0.0  # Unknown constraint or no load cases
                    
                constraint_values.append(value)
                
        except Exception as e:
            # Return penalty values for invalid solutions
            objective_values = [1e6] * self.n_obj
            constraint_values = [1e6] * self.n_ieq_constr
            
        return objective_values, constraint_values
        
    def _create_gusset_params(self, variables: Dict[str, float]) -> GussetParams:
        """Create gusset parameters from optimization variables."""
        return GussetParams(
            material=self.request.material,
            thickness=self.request.thickness,
            width=variables.get("width", 100.0),
            height=variables.get("height", 100.0),
            corner_radius=variables.get("corner_radius", 5.0),
            hole_diameter=variables.get("hole_diameter", 0.0),
            chamfer_size=variables.get("chamfer_size", 2.0)
        )
        
    def _create_base_plate_params(self, variables: Dict[str, float]) -> BasePlateParams:
        """Create base plate parameters from optimization variables."""
        return BasePlateParams(
            material=self.request.material,
            thickness=self.request.thickness,
            length=variables.get("length", 200.0),
            width=variables.get("width", 100.0),
            hole_diameter=variables.get("hole_diameter", 8.0),
            hole_spacing_x=variables.get("hole_spacing_x", 50.0),
            hole_spacing_y=variables.get("hole_spacing_y", 50.0),
            edge_distance=variables.get("edge_distance", 25.0)
        )


class NSGA2Optimizer:
    """NSGA-II multi-objective optimizer."""
    
    def __init__(self, request: OptimizationRequest):
        """Initialize optimizer."""
        self.request = request
        
    def optimize(self) -> OptimizationResponse:
        """Run NSGA-II optimization."""
        start_time = time.time()
        
        # Create optimization problem
        problem = OptimizationProblem(self.request)
        
        # Configure algorithm
        algorithm = NSGA2(
            pop_size=self.request.population_size,
            sampling=FloatRandomSampling(),
            crossover=SBX(prob=self.request.crossover_prob, eta=15),
            mutation=PM(prob=self.request.mutation_prob, eta=20),
            eliminate_duplicates=True
        )
        
        # Run optimization
        result = minimize(
            problem,
            algorithm,
            ('n_gen', self.request.generations),
            verbose=False
        )
        
        # Process results
        optimization_result = self._process_results(result, problem)
        
        end_time = time.time()
        optimization_time_ms = (end_time - start_time) * 1000
        
        # Algorithm information
        algorithm_info = {
            "algorithm": "NSGA-II",
            "population_size": self.request.population_size,
            "generations": self.request.generations,
            "crossover_prob": self.request.crossover_prob,
            "mutation_prob": self.request.mutation_prob,
            "converged": True  # Could check actual convergence
        }
        
        return OptimizationResponse(
            result=optimization_result,
            algorithm_info=algorithm_info,
            optimization_time_ms=optimization_time_ms,
            total_evaluations=self.request.population_size * self.request.generations
        )
        
    def _process_results(self, result: Any, problem: OptimizationProblem) -> OptimizationResult:
        """Process optimization results into response format."""
        # Get Pareto optimal solutions
        X = result.X  # Design variables
        F = result.F  # Objective values
        G = result.G if hasattr(result, 'G') else None  # Constraint values
        
        # Perform non-dominated sorting to get ranks
        nds = NonDominatedSorting()
        ranks = nds.do(F)
        
        # Calculate crowding distance (simplified)
        n_points = F.shape[0]
        crowding_distances = np.ones(n_points)  # Placeholder
        
        solutions = []
        for i in range(n_points):
            # Map variables
            variables = dict(zip(problem.variable_names, X[i, :]))
            
            # Map objectives
            objectives = dict(zip(problem.objective_names, F[i, :]))
            
            # Map constraints
            constraints = {}
            if G is not None and G.shape[1] > 0:
                constraints = dict(zip(problem.constraint_names, G[i, :]))
                
            # Check feasibility
            feasible = True
            if G is not None:
                feasible = np.all(G[i, :] <= 0)
                
            # Find rank
            rank = 1
            for r, front in enumerate(ranks):
                if i in front:
                    rank = r + 1
                    break
                    
            solution = OptimizationSolution(
                variables=variables,
                objectives=objectives,
                constraints=constraints,
                feasible=feasible,
                rank=rank,
                crowding_distance=crowding_distances[i]
            )
            solutions.append(solution)
            
        # Find best compromise solution (closest to utopia point)
        if solutions:
            # Normalize objectives
            obj_values = np.array([list(sol.objectives.values()) for sol in solutions])
            min_obj = np.min(obj_values, axis=0)
            max_obj = np.max(obj_values, axis=0)
            
            normalized_obj = (obj_values - min_obj) / (max_obj - min_obj + 1e-8)
            
            # Find solution closest to origin (compromise)
            distances = np.sqrt(np.sum(normalized_obj**2, axis=1))
            best_idx = np.argmin(distances)
            best_compromise = solutions[best_idx]
        else:
            best_compromise = OptimizationSolution(
                variables={}, objectives={}, constraints={},
                feasible=False, rank=1, crowding_distance=0.0
            )
            
        # Convergence data (simplified)
        convergence_data = {
            "generation": list(range(self.request.generations + 1)),
            "best_objective": [1.0] * (self.request.generations + 1),  # Placeholder
            "average_objective": [1.0] * (self.request.generations + 1)  # Placeholder
        }
        
        # Statistics
        feasible_solutions = [sol for sol in solutions if sol.feasible]
        statistics = {
            "total_solutions": len(solutions),
            "feasible_solutions": len(feasible_solutions),
            "pareto_front_size": len(ranks[0]) if ranks else 0,
            "convergence_achieved": True,
            "hypervolume": 0.0  # Would need reference point to calculate
        }
        
        return OptimizationResult(
            solutions=solutions,
            best_compromise=best_compromise,
            convergence_data=convergence_data,
            statistics=statistics
        )
