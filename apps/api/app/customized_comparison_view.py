"""Escaped, accessible comparisons of actual immutable candidate facts."""
from html import escape
from .customized_consent_summary import consent_summary


def render_comparison(snapshot):
    summary=consent_summary(snapshot);candidate=summary['candidate'];reference=summary['reference']
    if candidate is None:return ''
    e=lambda value:escape(str(value),quote=True)
    result=['<section id="workload-comparison" aria-label="Time and workload comparison"><h2>Compare the original candidates</h2>',
        '<p>Review candidates only. Science, exercise qualification and equipment/time assumptions remain unapproved. '
        'Accepting a shorter plan does not approve its science or establish equal or optimal hypertrophy.</p>']
    if reference:
        result.append('<div class="comparison-table"><table><caption>Same selected local dates; estimated minutes include warm-up, work, rest, setup, transitions and margin.</caption>'
            '<thead><tr><th scope="col">Local date</th><th scope="col">Selected candidate</th><th scope="col">Comparison candidate</th></tr></thead><tbody>')
        for i,day in enumerate(candidate['dates']):
            result.append(f'<tr><th scope="row">{e(day)}</th><td>{e(candidate["daily_sets"][i])} sets · {e(candidate["minimum_minutes"][i])}–{e(candidate["upper_minutes"][i])} min</td>'
                f'<td>{e(reference["daily_sets"][i])} sets · {e(reference["minimum_minutes"][i])}–{e(reference["upper_minutes"][i])} min</td></tr>')
        result.append('</tbody></table></div>')
        result.append(f'<p><strong>{e(candidate["name"])}: {e(candidate["weekly_sets"])} weekly working sets.</strong> '
            f'{e(reference["name"])}: {e(reference["weekly_sets"])} weekly working sets. '
            f'Selected local timezone: {e(candidate["timezone"])}; {e(candidate["cap_kind"])} cap {e(candidate["cap_minutes"])} minutes.</p>')
    else:
        result.append(f'<p>{e(candidate["name"])}: {e(candidate["weekly_sets"])} weekly working sets. '
            'A complete matched comparison is unavailable; reduced-dose acceptance requires one.</p>')
    changes=summary['workload_changes'];removed=sum(c['removed_sets'] for c in changes)
    if changes:
        result.append(f'<p>{abs(removed)} {"fewer" if removed>=0 else "additional"} working sets in the selected candidate. '
            'Less scheduled work may reduce hypertrophy opportunity; this is not evidence of equivalence or an optimal compromise.</p>'
            '<details id="full-workload-diff"><summary>Exercise-by-exercise working-set differences</summary><div class="comparison-table">'
            '<table><thead><tr><th scope="col">Date / exercise</th><th scope="col">Comparison sets</th><th scope="col">Selected sets</th></tr></thead><tbody>')
        for c in changes:
            result.append(f'<tr class="work-difference"><th scope="row">{e(c["local_date"])} · {e(c["exercise_name"])}</th><td>{e(c["reference_sets"])}</td><td>{e(c["candidate_sets"])}</td></tr>')
        result.append('</tbody></table></div></details>')
    for label,conflicts in (('Selected candidate',summary['proposed_range_conflicts']),('Comparison candidate',summary['alternative_range_conflicts'])):
        if conflicts:
            result.append(f'<p><strong>{e(label)}: {len(conflicts)} conflicts with unapproved proposed primary-region ranges.</strong> '
                'These ranges are review assumptions, not established biological minimums or medical findings. Secondary work is shown separately and does not cancel the differences.</p>'
                '<details><summary>View proposed range assumptions and actual primary-set counts</summary><ul>')
            result.extend(f'<li class="range-conflict">{e(c["region"].replace("_"," "))}: {e(c["primary_sets"])} primary sets; unapproved proposed range {e(c["proposed_minimum"])}–{e(c["proposed_maximum"])}.</li>' for c in conflicts)
            result.append('</ul></details>')
    result.append('<p>Predicted duration is not a measured guarantee; equipment queues and individual pace may exceed it. A hard45-minute cap remains infeasible for these candidates. '
        'The 45-set candidate exceeds a hard60-minute cap. No sets or rest periods are silently removed to claim a fit.</p>')
    result.append('<details><summary>Timing assumptions for the selected candidate</summary><ul>')
    for session in summary['timing_assumptions']:
        phases=session['phases']
        facts=[]
        for phase in ('warmup_seconds','work_seconds','rest_seconds','setup_seconds','transition_seconds','margin_seconds'):
            bounds=phases[phase];facts.append(f'{phase.removesuffix("_seconds").replace("_"," ")}: {bounds["low"]/60:g}–{bounds["high"]/60:g} min')
        result.append(f'<li>{e(session["local_date"])}: {e("; ".join(facts))}</li>')
    result.append('</ul></details><p>Alternatives: allow more time for the longer candidate; revise the candidate and review a new version; or decline. Existing Authored workouts remain preserved.</p></section>')
    return ''.join(result)
