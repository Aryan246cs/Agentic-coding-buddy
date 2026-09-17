# AI App Builder Frontend

Modern React frontend for the AI-powered code generator.

## Features

- 🎨 Clean, dark-themed UI similar to Lovable/Replit
- 📁 File explorer with syntax-highlighted icons
- 💻 Monaco code editor with syntax highlighting
- 👁️ Live preview panel with iframe rendering
- ⚡ Real-time project generation

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the dev server:
```bash
npm run dev
```

The frontend will run on `http://localhost:5173`

## Backend Connection

The frontend expects a backend API running on `http://localhost:8000` with the following endpoint:

```
POST /generate
Body: { "prompt": "your project description" }
Response: { "files": { "index.html": "...", "style.css": "...", "script.js": "..." } }
```

## Running the Full Stack

Terminal 1 (Backend):
```bash
python api.py
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

## Tech Stack

- React + Vite
- TailwindCSS
- Monaco Editor
- Lucide Icons
- FastAPI (backend)
