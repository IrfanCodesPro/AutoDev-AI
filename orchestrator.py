"""
AutoDev AI – Orchestrator
Coordinates the full agent pipeline end-to-end.
"""

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

from agents.planner_agent import PlannerAgent
from agents.architect_agent import ArchitectAgent
from agents.coding_agent import CodingAgent
from agents.testing_agent import TestingAgent
from agents.debugging_agent import DebuggingAgent
from agents.packaging_agent import PackagingAgent

DB_PATH = Path(__file__).parent.parent / "database" / "autodev.db"


class Orchestrator:
    AGENT_SEQUENCE = [
        ("planner",   "🧠 Planner Agent"),
        ("architect", "🏗️ Architect Agent"),
        ("coder",     "💻 Coding Agent"),
        ("tester",    "🧪 Testing Agent"),
        ("debugger",  "🔧 Debugging Agent"),
        ("packager",  "📦 Packaging Agent"),
    ]

    def __init__(self, project_id: str, api_key: str, queue: asyncio.Queue):
        self.project_id = project_id
        self.api_key = api_key
        self.queue = queue

    async def emit(self, agent_name: str, message: str, level: str = "info", extra: dict = None):
        now = datetime.utcnow().isoformat()
        payload = {
            "type": "log",
            "agent": agent_name,
            "message": message,
            "level": level,
            "timestamp": now,
            **(extra or {}),
        }
        await self.queue.put(payload)

        try:
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute(
                "INSERT INTO agent_logs (project_id, agent_name, message, level, timestamp) VALUES (?,?,?,?,?)",
                (self.project_id, agent_name, message, level, now),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    async def emit_status(self, agent_key: str, status: str, progress: int = 0):
        await self.queue.put({
            "type": "agent_status",
            "agent": agent_key,
            "status": status,
            "progress": progress,
        })

    async def run(self, prompt: str) -> dict:
        ctx = {"prompt": prompt, "project_id": self.project_id}

        await self.emit("orchestrator", f"🚀 Starting AutoDev AI pipeline for: {prompt[:80]}")
        await self.queue.put({"type": "pipeline_start", "agents": [a[0] for a in self.AGENT_SEQUENCE]})

        # Planner (large model)
        await self.emit_status("planner", "running", 10)
        await self.emit("planner", "Analyzing prompt and creating project plan...")
        agent = PlannerAgent(self.api_key, model="llama-3.3-70b-versatile")
        ctx["plan"] = await agent.run(ctx, self.emit)
        await self.emit("planner", "✅ Project plan complete", extra={"plan_summary": ctx["plan"].get("summary", "")})
        await self.emit_status("planner", "done", 100)

        # Architect (large model)
        await self.emit_status("architect", "running", 10)
        await self.emit("architect", "Designing system architecture and file structure...")
        agent = ArchitectAgent(self.api_key, model="llama-3.3-70b-versatile")
        ctx["architecture"] = await agent.run(ctx, self.emit)
        await self.emit("architect", "✅ Architecture designed", extra={"files": ctx["architecture"].get("files", [])})
        await self.emit_status("architect", "done", 100)

        # Coder (fast model)
        await self.emit_status("coder", "running", 10)
        await self.emit("coder", "Generating source code for all files...")
        agent = CodingAgent(self.api_key, model="llama-3.1-8b-instant")
        ctx["generated_files"] = await agent.run(ctx, self.emit)
        file_count = len(ctx["generated_files"])
        await self.emit("coder", f"✅ Generated {file_count} files")
        await self.emit_status("coder", "done", 100)

        # Tester (fast model)
        await self.emit_status("tester", "running", 10)
        await self.emit("tester", "Validating code structure and imports...")
        agent = TestingAgent(self.api_key, model="llama-3.1-8b-instant")
        ctx["test_results"] = await agent.run(ctx, self.emit)
        await self.emit("tester", f"✅ Testing complete — {ctx['test_results'].get('passed', 0)} checks passed")
        await self.emit_status("tester", "done", 100)

        # Debugger (fast model)
        await self.emit_status("debugger", "running", 10)
        await self.emit("debugger", "Reviewing code for issues and applying fixes...")
        agent = DebuggingAgent(self.api_key, model="llama-3.1-8b-instant")
        ctx["generated_files"] = await agent.run(ctx, self.emit)
        await self.emit("debugger", "✅ Code reviewed and optimized")
        await self.emit_status("debugger", "done", 100)

        # Packager (fast model)
        await self.emit_status("packager", "running", 10)
        await self.emit("packager", "Packaging project files...")
        agent = PackagingAgent(self.api_key, model="llama-3.1-8b-instant")
        final = await agent.run(ctx, self.emit)
        await self.emit("packager", "✅ Project packaged and ready for download")
        await self.emit_status("packager", "done", 100)

        await self.emit("orchestrator", "🎉 All agents complete! Project ready.", level="success")
        return {"files": ctx["generated_files"]}