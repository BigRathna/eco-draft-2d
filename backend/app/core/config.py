"""
Core configuration settings for the Eco Draft 2D application.
"""
from typing import Optional
import os
from pathlib import Path

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Eco Draft 2D"
    app_version: str = "0.1.0"
    app_description: str = "FastAPI backend for co-creative 2D CAD + engineering diagrams with sustainability metrics"

    # API settings
    api_prefix: str = "/api/v1"
    debug: bool = False
    gemini_api_key: str = ""

    # CORS settings
    backend_cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "http://100.80.24.79:3000",
        "http://100.80.24.79:3002",
        "http://100.80.24.79:3003",
    ]

    # File storage settings
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_extensions: set[str] = {".json", ".csv", ".txt"}

    # CAD settings
    default_units: str = "mm"
    precision: int = 6

    # Material properties database
    materials: dict[str, dict] = {
        "steel": {
            "density": 7850,  # kg/m³
            "yield_strength": 250e6,  # Pa
            "ultimate_strength": 400e6,  # Pa
            "elastic_modulus": 200e9,  # Pa
            "co2_factor": 1.85,  # kg CO2 / kg material
        },
        "aluminum": {
            "density": 2700,  # kg/m³
            "yield_strength": 270e6,  # Pa
            "ultimate_strength": 310e6,  # Pa
            "elastic_modulus": 70e9,  # Pa
            "co2_factor": 8.24,  # kg CO2 / kg material
        },
        "stainless_steel": {
            "density": 8000,  # kg/m³
            "yield_strength": 300e6,  # Pa
            "ultimate_strength": 600e6,  # Pa
            "elastic_modulus": 200e9,  # Pa
            "co2_factor": 2.90,  # kg CO2 / kg material
        },
    }

    # Manufacturing constraints
    manufacturing: dict[str, dict] = {
        "laser_cutting": {
            "min_kerf": 0.1,  # mm
            "max_kerf": 0.5,  # mm
            "min_radius": 0.2,  # mm
            "min_hole_diameter": 1.0,  # mm
            "min_ligament": 0.8,  # mm
        },
        "waterjet": {
            "min_kerf": 0.5,  # mm
            "max_kerf": 1.5,  # mm
            "min_radius": 0.1,  # mm
            "min_hole_diameter": 2.0,  # mm
            "min_ligament": 1.5,  # mm
        },
        "plasma": {
            "min_kerf": 1.0,  # mm
            "max_kerf": 6.0,  # mm
            "min_radius": 2.0,  # mm
            "min_hole_diameter": 10.0,  # mm
            "min_ligament": 3.0,  # mm
        },
    }

    # Optimization settings
    optimization: dict = {
        "population_size": 100,
        "generations": 50,
        "crossover_prob": 0.9,
        "mutation_prob": 0.1,
    }

    class Config:
        env_file = ".env"
        env_prefix = "ECO_DRAFT_"


# Create settings instance with custom GEMINI_API_KEY loading
settings = Settings()
# Override gemini_api_key to load directly from environment (not using ECO_DRAFT_ prefix)
if not settings.gemini_api_key:
    settings.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
