import json
from pathlib import Path

from .config import settings
from .template_schema import CanonicalProgramTemplate


def load_program_template(template_id: str) -> dict:
    candidate = Path(settings.programs_dir) / f"{template_id}.json"
    if not candidate.exists():
        raise FileNotFoundError(f"Program template not found: {template_id}")

    raw = json.loads(candidate.read_text(encoding="utf-8"))
    validated = CanonicalProgramTemplate.model_validate(raw)
    return validated.model_dump()
