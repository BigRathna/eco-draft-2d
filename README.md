# Eco Draft 2D

Eco Draft 2D is a comprehensive engineering design platform that helps you create 2D CAD geometry (like gussets and base plates) while evaluating manufacturability, stress, and sustainability metrics (like CO₂ impact).

## Key Features

- **2D Geometry Generation**: Create customizable parts and export them to DXF, SVG, or PDF drawings.
- **Engineering Analysis**: Includes manufacturability checks and analytic stress analysis.
- **Sustainability Metrics**: Life cycle assessment (LCA) tools for monitoring carbon footprint and material efficiency.
- **Optimization**: Multi-objective optimization (NSGA-II) to balance physical mass and CO₂ emissions.

## Getting Started

The project consists of a FastAPI backend and a Next.js frontend.

### Prerequisites
- Python 3.9+ 
- Node.js (for frontend development)

### Quick Start (Backend)
```bash
git clone https://github.com/eco-draft/eco-draft-2d.git
cd eco-draft-2d
make install
make dev
```
The API runs at `http://localhost:8000` with interactive docs available at `/api/v1/docs`.

### Quick Start (Frontend)
```bash
cd frontend
npm install
npm run dev
```

For more command options (formatting, linting, testing), run `make help` in the root directory.

## License
Apache License 2.0
