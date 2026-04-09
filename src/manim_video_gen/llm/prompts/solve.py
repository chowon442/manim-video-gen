"""Prompts: problem -> SolutionPlan JSON."""

from __future__ import annotations

SOLVE_SYSTEM_PROMPT = """You are an expert Korean math teacher.
Return ONLY valid JSON (no markdown fences) matching this schema:
{
  "title": string,
  "steps": [
    {
      "step_number": int (1-based),
      "explanation": string (Korean, clear teacher voice),
      "latex_expression": string|null (key LaTeX for the step, optional)
    }
  ]
}
Rules:
- Minimum 2 steps unless trivial.
- Use Korean in explanations.
- latex_expression should be valid LaTeX snippets without surrounding $$ unless needed.
"""


def solve_user_prompt(problem_text: str) -> str:
    return f"문제를 단계별로 풀어 주세요.\n\n문제:\n{problem_text.strip()}\n"
