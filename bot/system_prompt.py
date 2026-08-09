from __future__ import annotations

from pathlib import Path


DEFAULT_PROMPT_PATH = Path(__file__).with_name("system_prompt.txt")


def load_system_prompt(path: Path | None = None) -> str:
    prompt_path = DEFAULT_PROMPT_PATH if path is None else path
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise RuntimeError("generated system prompt is empty")
    return prompt
