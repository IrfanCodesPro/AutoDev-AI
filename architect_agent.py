"""
AutoDev AI – Architect Agent
Designs the application structure and file list.
"""

import asyncio
from agents import BaseAgent

SYSTEM = """You are a software architect.
Given a project plan, design the complete file structure.

Respond ONLY with valid JSON:
{
  "files": ["app.py", "models.py", "templates/index.html", "static/style.css", "requirements.txt", "README.md"],
  "entry_point": "app.py",
  "description": "brief architecture description",
  "components": {
    "backend": ["list of backend files"],
    "frontend": ["list of frontend files"],
    "config": ["list of config files"]
  }
}

Include ALL files needed for a complete, runnable application."""


class ArchitectAgent(BaseAgent):
    async def run(self, ctx: dict, emit) -> dict:
        plan = ctx.get("plan", {})
        await emit("architect", f"Designing architecture for {plan.get('framework', 'app')}...")
        await asyncio.sleep(0.5)

        prompt = f"""
Project plan: {plan}
User request: {ctx['prompt']}

Design the complete file structure.
"""
        raw = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._call_claude(SYSTEM, prompt)
        )
        arch = self._extract_json(raw)

        if not arch or not arch.get("files"):
            # Sensible defaults based on plan
            fw = plan.get("framework", "flask")
            has_db = plan.get("database", "none") != "none"
            has_auth = plan.get("auth_required", False)
            files = ["app.py", "requirements.txt", "README.md",
                     "templates/index.html", "templates/base.html",
                     "static/style.css"]
            if has_db:
                files.insert(1, "models.py")
            if has_auth:
                files += ["templates/login.html", "templates/register.html"]
            arch = {
                "files": files,
                "entry_point": "app.py",
                "description": f"Standard {fw} project layout",
                "components": {"backend": ["app.py"], "frontend": ["templates/"], "config": ["requirements.txt"]},
            }

        for f in arch["files"][:5]:
            await emit("architect", f"  📄 {f}")
            await asyncio.sleep(0.1)
        if len(arch["files"]) > 5:
            await emit("architect", f"  ... and {len(arch['files'])-5} more files")

        return arch
