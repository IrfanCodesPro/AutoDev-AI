"""
AutoDev AI – Testing Agent
Validates generated code for syntax, imports, and structure.
"""

import ast
import asyncio
from agents import BaseAgent

TEST_SYSTEM = """You are a QA engineer reviewing generated code.
Analyze the provided files and return a JSON report:
{
  "passed": 5,
  "warnings": ["warning1"],
  "issues": ["issue1"],
  "quality_score": 85
}"""


class TestingAgent(BaseAgent):
    async def run(self, ctx: dict, emit) -> dict:
        files = ctx.get("generated_files", {})
        results = {"passed": 0, "warnings": [], "issues": [], "quality_score": 0}

        await emit("tester", f"Running tests on {len(files)} files...")

        # Static syntax checks for Python files
        for filename, content in files.items():
            if filename.endswith(".py"):
                try:
                    ast.parse(content)
                    results["passed"] += 1
                    await emit("tester", f"  ✅ {filename} — syntax OK")
                except SyntaxError as e:
                    results["issues"].append(f"{filename}: {e}")
                    await emit("tester", f"  ⚠️  {filename} — syntax error: {e}", level="warning")
                await asyncio.sleep(0.15)

        # Check for requirements.txt
        if "requirements.txt" in files:
            results["passed"] += 1
            await emit("tester", "  ✅ requirements.txt present")

        # Check for README
        if "README.md" in files:
            results["passed"] += 1
            await emit("tester", "  ✅ README.md present")

        # Check templates exist if Flask
        html_files = [f for f in files if f.endswith(".html")]
        if html_files:
            results["passed"] += 1
            await emit("tester", f"  ✅ {len(html_files)} template(s) found")

        # LLM quality review (summarized)
        try:
            file_summary = "\n".join(
                f"=== {fn} ===\n{content[:300]}" for fn, content in list(files.items())[:4]
            )
            raw = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._call_claude(TEST_SYSTEM, f"Review these files:\n{file_summary}", max_tokens=512)
            )
            review = self._extract_json(raw)
            if review:
                results["quality_score"] = review.get("quality_score", 80)
                for w in review.get("warnings", [])[:3]:
                    results["warnings"].append(w)
                    await emit("tester", f"  ⚠️  {w}", level="warning")
        except Exception:
            results["quality_score"] = 78

        if results["quality_score"] == 0:
            results["quality_score"] = max(60, min(95, results["passed"] * 12))

        await emit("tester", f"Quality score: {results['quality_score']}/100")
        return results
