import json
from pathlib import Path

from .config import settings


def load_program_template(template_id: str) -> dict:
    candidate = Path(settings.programs_dir) / f"{template_id}.json"
    if not candidate.exists():
        raise FileNotFoundError(f"Program template not found: {template_id}")
    return json.loads(candidate.read_text(encoding="utf-8"))
