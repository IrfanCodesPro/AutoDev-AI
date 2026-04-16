"""
AutoDev AI – Debugging Agent
Fixes any issues found during testing and improves code quality.
"""

import asyncio
from agents import BaseAgent

DEBUG_SYSTEM = """You are an expert debugger and code reviewer.
You will receive a file that may have issues. Fix all problems and return ONLY
the corrected, production-ready source code. No markdown, no explanations."""


class DebuggingAgent(BaseAgent):
    async def run(self, ctx: dict, emit) -> dict:
        files = ctx.get("generated_files", {})
        test_results = ctx.get("test_results", {})
        issues = test_results.get("issues", [])

        if not issues:
            await emit("debugger", "No critical issues found. Performing code quality review...")
        else:
            await emit("debugger", f"Found {len(issues)} issue(s) to fix...")

        fixed_files = dict(files)

        # Fix files with known issues
        files_to_fix = set()
        for issue in issues:
            for filename in files:
                if filename in issue:
                    files_to_fix.add(filename)

        # If quality score is low, also review main files
        quality = test_results.get("quality_score", 80)
        if quality < 70:
            for fn in list(files.keys())[:2]:
                files_to_fix.add(fn)

        for filename in files_to_fix:
            await emit("debugger", f"  🔧 Fixing {filename}...")
            content = files.get(filename, "")
            try:
                fixed = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda c=content, fn=filename: self._call_claude(
                        DEBUG_SYSTEM,
                        f"Fix and improve this file ({fn}):\n\n{c}",
                        max_tokens=3000,
                    )
                )
                # Strip markdown fences
                if fixed.startswith("```"):
                    lines = fixed.split("\n")
                    fixed = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
                fixed_files[filename] = fixed
                await emit("debugger", f"  ✅ {filename} fixed")
            except Exception as e:
                await emit("debugger", f"  ⚠️  Could not auto-fix {filename}: {e}", level="warning")
            await asyncio.sleep(0.2)

        if not files_to_fix:
            await emit("debugger", "  ✅ All files passed quality review")

        return fixed_files
