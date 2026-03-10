from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent.graph import agent
import pathlib
import re
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_project_path = None


def generate_project_name(prompt: str) -> str:
    words = prompt.lower().split()[:5]
    name = "_".join(words)
    name = re.sub(r"[^a-z0-9_]", "", name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{name}_{timestamp}"


class GenerateRequest(BaseModel):
    prompt: str


@app.get("/projects")
async def list_projects():
    """List all generated projects"""
    try:
        projects_dir = pathlib.Path.cwd() / "projects"
        if not projects_dir.exists():
            return {"projects": []}

        projects = []
        for project_path in sorted(projects_dir.iterdir(), reverse=True):
            if project_path.is_dir():
                projects.append(
                    {"name": project_path.name, "created": project_path.stat().st_ctime}
                )

        return {"projects": projects}
    except Exception as e:
        return {"error": str(e), "projects": []}


@app.get("/projects/{project_name}")
async def get_project_files(project_name: str):
    """Get files from a specific project"""
    global current_project_path
    try:
        project_path = pathlib.Path.cwd() / "projects" / project_name
        if not project_path.exists():
            return {"error": "Project not found", "files": {}}

        current_project_path = project_path

        files = {}
        for file_path in project_path.glob("**/*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(project_path)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        files[str(relative_path)] = f.read()
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

        return {"files": files, "project_name": project_name}
    except Exception as e:
        return {"error": str(e), "files": {}}


@app.post("/generate")
async def generate_project(request: GenerateRequest):
    """Generate project files from user prompt"""
    global current_project_path
    try:
        import agent.tools as tools_module

        project_name = generate_project_name(request.prompt)
        project_path = pathlib.Path.cwd() / "projects" / project_name
        project_path.mkdir(parents=True, exist_ok=True)

        original_project_root = tools_module.PROJECT_ROOT
        tools_module.PROJECT_ROOT = project_path

        try:
            result = agent.invoke(
                {"user_prompt": request.prompt}, {"recursion_limit": 100}
            )
        finally:
            tools_module.PROJECT_ROOT = original_project_root

        current_project_path = project_path

        files = {}
        if project_path.exists():
            for file_path in project_path.glob("**/*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(project_path)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            files[str(relative_path)] = f.read()
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")

        return {"files": files, "project_name": project_name}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"error": str(e), "files": {}}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
