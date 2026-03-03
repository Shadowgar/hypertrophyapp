import json
from pathlib import Path
from pydantic import ValidationError

from .config import settings
from .template_schema import CanonicalProgramTemplate


PROGRAM_DESCRIPTIONS: dict[str, str] = {
    "full_body_v1": "Pure Bodybuilding-inspired full body structure with deterministic day templates.",
    "ppl_v1": "Push/Pull/Legs baseline template for balanced hypertrophy progression.",
    "upper_lower_v1": "Upper/Lower split with clear weekly distribution and recovery spacing.",
    "edited_ppl_5x": "Imported higher-frequency PPL variant derived from reference spreadsheet data.",
}


def list_program_templates() -> list[dict]:
    programs_path = Path(settings.programs_dir)
    candidates = sorted(programs_path.glob("*.json"))

    summaries: list[dict] = []
    for candidate in candidates:
        raw = json.loads(candidate.read_text(encoding="utf-8"))
        try:
            validated = CanonicalProgramTemplate.model_validate(raw)
        except ValidationError:
            continue

        data = validated.model_dump()
        summaries.append(
            {
                "id": data["id"],
                "version": data["version"],
                "split": data["split"],
                "days_supported": data["days_supported"],
                "session_count": len(data["sessions"]),
                "description": PROGRAM_DESCRIPTIONS.get(
                    data["id"],
                    f"Deterministic {data['split']} program template.",
                ),
            }
        )

    return summaries


def load_program_template(template_id: str) -> dict:
    candidate = Path(settings.programs_dir) / f"{template_id}.json"
    if not candidate.exists():
        raise FileNotFoundError(f"Program template not found: {template_id}")

    raw = json.loads(candidate.read_text(encoding="utf-8"))
    validated = CanonicalProgramTemplate.model_validate(raw)
    return validated.model_dump()
