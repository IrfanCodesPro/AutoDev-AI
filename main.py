"""
AutoDev AI - Autonomous Software Developer
FastAPI Backend Entry Point
"""

import asyncio
import json
import os
import sqlite3
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import Orchestrator

# ── App Setup ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "database" / "autodev.db"
PROJECTS_DIR = BASE_DIR / "generated_projects"
PROJECTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AutoDev AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
frontend_path = BASE_DIR / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            prompt TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            completed_at TEXT,
            zip_path TEXT
        );

        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            agent_name TEXT,
            message TEXT,
            level TEXT DEFAULT 'info',
            timestamp TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );

        CREATE TABLE IF NOT EXISTS generated_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            filename TEXT,
            content TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
    """)
    conn.commit()
    conn.close()


init_db()

# In-memory store for SSE streams
active_streams: dict[str, asyncio.Queue] = {}


# ── Models ────────────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    prompt: str
    api_key: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    index = BASE_DIR / "frontend" / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "AutoDev AI API running"}


@app.post("/api/generate")
async def generate_project(req: GenerateRequest):
    """Start project generation pipeline."""
    project_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    conn = get_db()
    conn.execute(
        "INSERT INTO projects (id, prompt, status, created_at) VALUES (?, ?, ?, ?)",
        (project_id, req.prompt, "running", now),
    )
    conn.commit()
    conn.close()

    # Create SSE queue for this project
    queue: asyncio.Queue = asyncio.Queue()
    active_streams[project_id] = queue

    # Run orchestrator in background
    api_key = req.api_key or os.getenv("GROQ_API_KEY", "")
    asyncio.create_task(
        run_orchestrator(project_id, req.prompt, api_key, queue)
    )

    return {"project_id": project_id, "status": "started"}


async def run_orchestrator(project_id: str, prompt: str, api_key: str, queue: asyncio.Queue):
    """Run the agent orchestrator and emit events."""
    try:
        orch = Orchestrator(project_id=project_id, api_key=api_key, queue=queue)
        result = await orch.run(prompt)

        # Save generated files to DB
        conn = get_db()
        for filename, content in result.get("files", {}).items():
            conn.execute(
                "INSERT INTO generated_files (project_id, filename, content) VALUES (?, ?, ?)",
                (project_id, filename, content),
            )

        # Create ZIP
        zip_path = PROJECTS_DIR / f"{project_id}.zip"
        project_dir = PROJECTS_DIR / project_id
        project_dir.mkdir(exist_ok=True)

        for filename, content in result.get("files", {}).items():
            file_path = project_dir / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in project_dir.rglob("*"):
                if file_path.is_file():
                    zf.write(file_path, file_path.relative_to(project_dir))

        now = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE projects SET status=?, completed_at=?, zip_path=? WHERE id=?",
            ("completed", now, str(zip_path), project_id),
        )
        conn.commit()
        conn.close()

        await queue.put({"type": "complete", "project_id": project_id, "files": list(result.get("files", {}).keys())})

    except Exception as e:
        conn = get_db()
        conn.execute("UPDATE projects SET status=? WHERE id=?", ("failed", project_id))
        conn.commit()
        conn.close()
        await queue.put({"type": "error", "message": str(e)})
    finally:
        await queue.put(None)  # Sentinel


@app.get("/api/stream/{project_id}")
async def stream_events(project_id: str):
    """SSE endpoint for real-time agent updates."""
    queue = active_streams.get(project_id)
    if not queue:
        raise HTTPException(404, "Stream not found")

    async def event_generator():
        try:
            while True:
                item = await asyncio.wait_for(queue.get(), timeout=120.0)
                if item is None:
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    break
                yield f"data: {json.dumps(item)}\n\n"
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'timeout'})}\n\n"
        finally:
            active_streams.pop(project_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/projects")
async def list_projects():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, prompt, status, created_at, completed_at FROM projects ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/projects/{project_id}/files")
async def get_project_files(project_id: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT filename, content FROM generated_files WHERE project_id=?", (project_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/projects/{project_id}/logs")
async def get_project_logs(project_id: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT agent_name, message, level, timestamp FROM agent_logs WHERE project_id=? ORDER BY id",
        (project_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/projects/{project_id}/download")
async def download_project(project_id: str):
    conn = get_db()
    row = conn.execute("SELECT zip_path FROM projects WHERE id=?", (project_id,)).fetchone()
    conn.close()
    if not row or not row["zip_path"]:
        raise HTTPException(404, "Project not ready or not found")
    zip_path = Path(row["zip_path"])
    if not zip_path.exists():
        raise HTTPException(404, "ZIP file missing")
    return FileResponse(str(zip_path), media_type="application/zip", filename=f"project_{project_id[:8]}.zip")


@app.get("/api/stats")
async def get_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM projects").fetchone()["c"]
    completed = conn.execute("SELECT COUNT(*) as c FROM projects WHERE status='completed'").fetchone()["c"]
    running = conn.execute("SELECT COUNT(*) as c FROM projects WHERE status='running'").fetchone()["c"]
    conn.close()
    return {"total_projects": total, "completed": completed, "running": running, "agents": 6}
