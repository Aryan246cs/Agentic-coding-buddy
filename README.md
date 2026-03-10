# Coder Buddy

An AI-powered coding agent that takes your project ideas and automatically generates complete web applications with HTML, CSS, and JavaScript.

## What It Does

Give it a prompt like "create a birthday card website" and it will:
1. Plan the project (features, tech stack, files needed)
2. Design the implementation steps
3. Write all the code files for you

## How to Use

### Option 1: CLI Mode

1. Install dependencies:
```bash
uv sync
```

2. Set up your API key in `.env`:
```
GROQ_API_KEY=your_api_key_here
```

3. Run the agent:
```bash
python main.py
```

4. Enter your project idea when prompted

### Option 2: Web UI Mode

1. Install backend dependencies:
```bash
uv sync
pip install fastapi uvicorn
```

2. Install frontend dependencies:
```bash
cd frontend
npm install
```

3. Start the backend API:
```bash
python api.py
```

4. In a new terminal, start the frontend:
```bash
cd frontend
npm run dev
```

5. Open `http://localhost:5173` in your browser

## Project Structure

- `main.py` - Entry point, handles user input
- `agent/graph.py` - Main agent workflow (planner → architect → coder)
- `agent/states.py` - Data models for plans and tasks
- `agent/prompts.py` - Prompts for each agent
- `agent/tools.py` - File operations (read, write, list files)

## How It Works

The agent uses three specialized AI agents in sequence:

1. **Planner Agent** - Analyzes your prompt and creates a project plan with features, tech stack, and files
2. **Architect Agent** - Breaks down the plan into step-by-step implementation tasks
3. **Coder Agent** - Writes the actual code for each file using the tasks

## Requirements

- Python 3.11+
- Groq API key (free tier works)
- Dependencies: langchain, langgraph, langchain-groq

## Example Prompts

- "Create a simple calculator web app"
- "Build a todo list with local storage"
- "Make a birthday card with animations"
- "Create a portfolio landing page"

Keep prompts simple and focused on single-page web apps for best results.
