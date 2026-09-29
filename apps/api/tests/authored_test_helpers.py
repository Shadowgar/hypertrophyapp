"""Explicit feasible equipment for positive authored execution fixtures."""
from app.program_loader import load_program_template


def source_equipment(program_id="pure_bodybuilding_phase_1_full_body"):
    template = load_program_template(program_id)
    return sorted({tag for session in template['sessions'] for exercise in session['exercises']
        for tag in exercise.get('equipment_tags') or []})
