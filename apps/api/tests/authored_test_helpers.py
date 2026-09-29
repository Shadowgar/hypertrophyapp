"""Explicit feasible equipment for positive authored execution fixtures."""
from app.program_loader import load_program_template


def source_equipment(program_id="pure_bodybuilding_phase_1_full_body"):
    template = load_program_template(program_id)
    weeks = template.get('authored_weeks') or [{'sessions': template['sessions']}]
    return sorted({tag for week in weeks for session in week['sessions'] for exercise in session['exercises']
        for tag in exercise.get('equipment_tags') or []})
