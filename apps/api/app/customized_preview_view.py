"""Escaped consumer-readable staging preview, rendered from owned result facts."""
from html import escape

from .customized_preview_models import PreviewResponse

STYLE="""
:root{font-family:system-ui,sans-serif;color:#e5eaf2;background:#101722;line-height:1.5}
*{box-sizing:border-box}body{margin:0}main{max-width:1160px;margin:auto;padding:28px 20px 60px}
a{color:#a8d4ff}h1,h2,h3{line-height:1.2}h1{font-size:2rem}.banner{border:1px solid #e4b75f;background:#392d18;color:#ffe4ac;padding:16px;border-radius:10px}.intro{max-width:85ch}.nav{display:flex;gap:24px;flex-wrap:wrap;margin:24px 0}.candidate{margin-top:32px;padding:20px;border:1px solid #48566c;border-radius:12px;background:#172231}.facts{display:flex;gap:12px;flex-wrap:wrap}.fact{padding:8px 12px;background:#243449;border-radius:6px}.muted{color:#bdc9da}.sessions{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:16px;margin:20px 0}.session{padding:16px;border:1px solid #52647d;border-radius:8px;min-width:0}.exercise{border-top:1px solid #41516a;padding:12px 0}.exercise h4{margin:0 0 5px}.exercise p{margin:4px 0}.notice{border-left:4px solid #e4b75f;padding:8px 12px;background:#243449}summary{cursor:pointer;min-height:44px;padding:10px 0}details{margin:12px 0}.table-wrap{overflow:auto}table{border-collapse:collapse;width:100%;font-size:.95rem}th,td{padding:9px;text-align:left;border-bottom:1px solid #52647d}code{overflow-wrap:anywhere}li{margin:5px 0}p,li{overflow-wrap:anywhere}@media(max-width:500px){main{padding:18px 12px 40px}.candidate{padding:12px}h1{font-size:1.65rem}}
"""


def _e(value):
    return escape(str(value),quote=True)


def _labels(values):
    return ", ".join(_e(v.replace("_"," ")) for v in values) or "None declared"



def _load_note(exercise):
    if exercise.working_load is not None:
        return f'{exercise.working_load:g} {_e(exercise.load_unit)} ({_e(exercise.load_basis)}), synthetic comparable baseline'
    reasons=set(exercise.calibration_reasons)
    if "pain_reported" in reasons:
        return "unavailable: pain reported; pause load calibration for review"
    if "pain_status_unknown" in reasons:
        return "unavailable: confirm pain status before load calibration"
    if "technique_not_qualified" in reasons:
        return "unavailable: technique needs review before load calibration"
    if "exposure_stale_or_future" in reasons:
        return "unavailable: evidence date is outside the candidate admission window"
    return {
        "requires_calibration":"requires exercise-specific calibration",
        "unsupported_variant":"unavailable: exercise/load semantics need review",
        "insufficient_history":"unavailable: completed evidence is insufficient or incomparable",
        "invalid_input":"unavailable: input needs correction",
        "policy_not_approved":"unavailable: policy is not approved",
    }.get(exercise.calibration_status,"unavailable: review calibration evidence")


def _candidate(result, index):
    workload=sum(e.sets for s in result.sessions for e in s.exercises)
    title=_e(result.candidate_name)
    out=[f'<section class="candidate" id="candidate-{index}"><h2>{title}</h2>',f'<p>{_e(result.message)}</p>',
        f'<div class="facts"><span class="fact">{workload} proposed working sets/week</span><span class="fact">{_e(result.cap_kind or "No")} cap: {_e(result.cap_minutes or "unknown")} min</span><span class="fact">Coverage: {_e((result.coverage_status or "not assessed").replace("_"," "))}</span></div>',
        f'<p class="muted">Dates in {_e(result.timezone or "unknown timezone")}. {_e(result.coverage_meaning)}</p>']
    if result.dose_conflicts:
        out.append(f'<p class="notice">Below/outside original candidate direct-work bands: {_labels(result.dose_conflicts)}. These are workload tradeoffs, not equivalent gains.</p>')
    if result.missing_actions or result.missing_regions:
        out.append(f'<p class="notice">Missing actions: {_labels(result.missing_actions)}. Missing primary regions: {_labels(result.missing_regions)}.</p>')
    if result.accepted_omissions:
        out.append('<details><summary>Tradeoffs explicitly accepted for this synthetic comparison</summary><ul>')
        out.extend(f'<li>{_e(o.kind)}: {_e(o.name.replace("_"," "))} — {_e(o.reason)}</li>' for o in result.accepted_omissions)
        out.append('</ul></details>')
    out.append('<div class="sessions">')
    for s in result.sessions:
        cap="Fits modeled upper time bound" if s.cap_status=="within_estimated_cap" else "Time budget exceeded or uncertain; review required"
        out.extend((f'<article class="session"><h3>{_e(s.local_date.isoformat())}</h3><p>{_e(s.design_label)}</p>',
            f'<p><strong>{s.minimum_minutes:g}–{s.maximum_minutes:g} minutes</strong><br>{cap}</p>'))
        for e in s.exercises:
            observed=", ".join(f'{v:g}' for v in e.observed_effort) if e.observed_effort else "unknown"
            load=_load_note(e)
            out.extend((f'<div class="exercise"><h4>{_e(e.name)}</h4><p><strong>{e.sets} × {e.reps_min}–{e.reps_max}</strong></p>',
                f'<p>Target effort: {e.target_min:g}–{e.target_max:g} {_e(e.target_scale.upper())}<br>Observed effort: {observed}{" " + _e(e.target_scale.upper()) if e.observed_effort else ""}</p>',
                f'<p>Rest: {e.rest_min_seconds:g}–{e.rest_max_seconds:g} seconds<br>Working load: {load}</p>'))
            out.append(f'<details><summary>Calibration evidence</summary><p>Status: <code>{_e(e.calibration_status)}</code></p><ul>'+
                "".join(f'<li><code>{_e(reason)}</code></li>' for reason in e.calibration_reasons)+'</ul></details></div>')
        out.append('</article>')
    out.append('</div>')
    if result.tradeoffs:
        out.append('<details open><summary>Time and coverage tradeoffs</summary><ul>')
        out.extend(f'<li>{_e(t)}</li>' for t in result.tradeoffs)
        out.append('</ul></details>')
    if result.regions:
        out.append('<details><summary>Weekly primary, secondary and unknown work</summary><p>Secondary involvement is separate; no half-set multiplier. A set may have two primary regions. Unknown distribution is not extra work.</p><div class="table-wrap"><table><thead><tr><th>Region</th><th>Primary</th><th>Secondary</th><th>Unknown</th></tr></thead><tbody>')
        out.extend(f'<tr><td>{_e(r.region.replace("_"," "))}</td><td>{r.primary_sets}</td><td>{r.secondary_sets}</td><td>{r.unknown_sets}</td></tr>' for r in result.regions)
        out.append('</tbody></table></div></details>')
    if result.issues:
        out.append('<details><summary>Unavailable exercise choices</summary><ul>')
        out.extend(f'<li>{_e(v)}</li>' for v in result.issues)
        out.append('</ul></details>')
    out.append('<details><summary>Review limitations and decision trace</summary><p>Fixed original candidate, not a personalized topology/volume optimizer. Every exact effort, rest, calibration and dose rule needs scientific and owner review. RIR is a fallible self-report; no failure/max test is required. Source-anchored exercise descriptions and synthetic loads are not qualified real inventory. Across-week scheduling remains unintegrated.</p>')
    out.append('<ul>'+''.join(f'<li><code>{_e(reason)}</code></li>' for reason in result.reasons)+'</ul>')
    out.append('<dl>'+''.join(f'<dt>{_e(k)}</dt><dd><code>{_e(v)}</code></dd>' for k,v in result.trace.items())+'</dl></details></section>')
    return "".join(out)


def render_comparison(results: tuple[PreviewResponse, ...]) -> str:
    nav="".join(f'<a href="#candidate-{i}">Candidate {i+1}</a>' for i,_ in enumerate(results))
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Experimental Customized preview</title><style>'+STYLE+'</style></head><body><main>'
        '<h1>Experimental Customized preview</h1><p class="banner"><strong>CANDIDATE FOR EXPERT REVIEW / NONPRESCRIPTIVE</strong><br>Synthetic review only. No approved training policy. Workout activation and logging are unavailable.</p>'
        '<p class="intro">Compare the proposed workload against the time you have. Less work can fit a shorter session, but equal or optimal hypertrophy results have not been established. Estimates include warmup, working sets, rest, setup, transitions and a margin; coaching or crowded equipment can take longer.</p>'
        '<p class="intro">Keep reported effort separate from the target. Unknown effort stays unknown. Working loads need exact-variant, technique, pain and attainable-equipment checks; optional max information does not select a starting weight.</p>'
        f'<nav class="nav" aria-label="Candidate comparison">{nav}</nav>' + ''.join(_candidate(r,i) for i,r in enumerate(results)) + '</main></body></html>')


def render_preview(result: PreviewResponse) -> str:
    return render_comparison((result,))
