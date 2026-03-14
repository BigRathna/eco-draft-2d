# ECO-Draft 2D Frontend

A modern Next.js frontend for the eco-draft-2d FastAPI backend, providing an AI-powered mechanical part design interface with environmental impact analysis.

## 🚀 Features

### Conversational Design Interface
- **ChatGPT-style UI** for natural language part descriptions
- **Markdown rendering** for assistant responses
- **Action buttons** for quick operations (check manufacturability, analyze stress, etc.)
- **Persistent conversation history** stored in local storage
- **Example prompts** to get users started

### Interactive Canvas
- **SVG rendering** of 2D part outlines from backend
- **Zoom and pan controls** with mouse wheel and drag
- **Fit to screen** and reset view functionality
- **Grid overlay** for design reference
- **Responsive design** that adapts to different screen sizes

### Analysis Dashboard
- **Manufacturability Checks**: Green/red badges showing pass/warning/fail status
- **Stress Analysis**: Safety factor display with recommendations
- **Lifecycle Assessment (LCA)**: CO₂ footprint, material mass, and recyclability scores
- **Pareto Front Visualization**: Interactive scatter plot for multi-objective optimization

### Design System
- **Tailwind CSS** with shadcn/ui components for consistent styling
- **Dark/Light mode** toggle with system preference detection
- **Responsive layout** with collapsible analytics panel
- **Professional color scheme** with accessibility considerations

## 🛠 Tech Stack

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **State Management**: React Query (TanStack Query)
- **Charts**: Recharts
- **Markdown**: react-markdown
- **Icons**: Lucide React
- **Notifications**: Sonner

## 📋 Prerequisites

- Node.js 18+ and npm
- Running eco-draft-2d FastAPI backend at `http://localhost:8000`

## 🚀 Quick Start

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env.local
   # Edit .env.local to set NEXT_PUBLIC_API_URL if different from default
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

4. **Open browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## 🏗 Project Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout with providers
│   │   ├── page.tsx            # Main application page
│   │   └── providers.tsx       # React Query setup
│   ├── components/
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── Chat.tsx           # Conversational interface
│   │   ├── Canvas.tsx         # SVG rendering and interactions
│   │   ├── Checks.tsx         # Manufacturability analysis
│   │   ├── Analysis.tsx       # Stress analysis display
│   │   ├── LCA.tsx           # Environmental impact metrics
│   │   ├── ParetoChart.tsx   # Optimization visualization
│   │   └── theme-provider.tsx # Dark/light mode support
│   └── lib/
│       └── api.ts            # Backend API client with types
├── public/                   # Static assets
├── .env.example             # Environment variables template
└── package.json
```

## 🔌 Backend Integration

The frontend connects to the following eco-draft-2d API endpoints:

- **POST** `/api/part/generate` - Generate part SVG from description
- **GET** `/api/part/check` - Check manufacturability
- **GET** `/api/part/analyze` - Perform stress analysis
- **GET** `/api/part/lca` - Get lifecycle assessment data
- **GET** `/api/drawing/build` - Download PDF drawing
- **POST** `/api/opt/run` - Run multi-objective optimization

## 💡 Usage Guide

### Creating a Part
1. Type a natural language description in the chat input
2. Example: *"Make me a gusset with 5mm thickness and larger holes"*
3. The assistant will generate the part and show it in the canvas

### Analysis Workflow
1. After generating a part, use the action buttons to:
   - **Check Manufacturability** - Review DFM guidelines
   - **Analyze Stress** - View safety factors and critical locations
   - **View LCA Data** - See environmental impact metrics
   - **Run Optimization** - Explore design trade-offs

### Exporting Results
- Click **Export PDF** to download technical drawings
- Use browser tools to save the chat conversation
- Screenshots can capture the complete analysis dashboard

## 🎨 Customization

### Themes
- Toggle between light/dark modes using the header button
- System theme automatically detects OS preference
- Theme preference is stored in localStorage

### Environment Variables
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000  # Backend API base URL
```

### Styling
- Modify `tailwind.config.js` for custom colors and spacing
- Update `src/app/globals.css` for global styles
- Add custom shadcn/ui components with `npx shadcn@latest add <component>`

## 🚧 Development

### Available Scripts
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

### Adding Features
1. **New API Endpoints**: Add to `src/lib/api.ts` with proper TypeScript types
2. **UI Components**: Create in `src/components/` following the existing patterns
3. **Analysis Widgets**: Follow the structure of existing components like `Checks.tsx`

## 🤝 Contributing

1. Follow the existing code style and TypeScript patterns
2. Use shadcn/ui components when possible for consistency
3. Add proper error handling and loading states
4. Test with the actual backend API
5. Update this README if adding significant features

---

**Happy designing! 🎯 Create sustainable mechanical parts with AI assistance.**
