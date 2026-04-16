"""
AutoDev AI – Planner Agent
Understands user intent and creates a structured project plan.
"""

import asyncio
from agents import BaseAgent

SYSTEM = """You are a senior software architect and project planner.
Analyze the user's prompt and produce a structured JSON project plan.

Respond ONLY with valid JSON:
{
  "summary": "one-line summary",
  "type": "web_app|cli|api|library",
  "language": "python|javascript|...",
  "framework": "flask|fastapi|express|...",
  "features": ["feature1", "feature2"],
  "database": "sqlite|postgres|none",
  "auth_required": true|false,
  "complexity": "simple|medium|complex"
}"""


class PlannerAgent(BaseAgent):
    async def run(self, ctx: dict, emit) -> dict:
        prompt = ctx["prompt"]
        await emit("planner", f"Understanding prompt: '{prompt[:60]}...'")
        await asyncio.sleep(0.5)

        raw = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._call_claude(SYSTEM, f"Plan this project: {prompt}")
        )
        plan = self._extract_json(raw)

        if not plan:
            # Fallback plan
            plan = {
                "summary": prompt[:80],
                "type": "web_app",
                "language": "python",
                "framework": "flask",
                "features": ["core functionality", "basic UI"],
                "database": "sqlite",
                "auth_required": False,
                "complexity": "medium",
            }

        await emit("planner", f"Project type: {plan.get('type', 'web_app')} | Framework: {plan.get('framework', 'flask')}")
        await emit("planner", f"Features identified: {', '.join(plan.get('features', [])[:4])}")
        return plan
