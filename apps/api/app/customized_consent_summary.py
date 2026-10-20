"""Deterministic presentation/audit of existing planning facts; no prescription policy."""
from core_engine.customized.audit import content_hash

COMPACT_PROTOCOL='compact-candidate-consent-v2'
LEGACY_PROTOCOL='granular-candidate-consent-v1'
ACKNOWLEDGEMENT=("I choose Customized and acknowledge this exact inactive candidate version, its dates, estimated time, "
    "working-set changes and unapproved scientific assumptions. I understand that accepting it neither approves the science "
    "nor starts a workout; equal or optimal hypertrophy and a measured session-time guarantee have not been established.")


def _workload(preview):
    if not preview:return None
    sessions=preview['sessions']
    return dict(name=preview['candidate_name'],weekly_sets=sum(e['sets'] for s in sessions for e in s['exercises']),
        dates=[s['local_date'] for s in sessions],timezone=preview['timezone'],
        daily_sets=[sum(e['sets'] for e in s['exercises']) for s in sessions],
        minimum_minutes=[s['minimum_minutes'] for s in sessions],upper_minutes=[s['maximum_minutes'] for s in sessions],
        cap_minutes=preview['cap_minutes'],cap_kind=preview['cap_kind'],cap_status=[s['cap_status'] for s in sessions])


def consent_summary(snapshot):
    preview=snapshot['preview'];reference=snapshot.get('comparison_reference')
    names={(s['local_date'],e['variant_id']):e['name'] for s in preview['sessions'] for e in s['exercises']}
    changes=[{**c,'exercise_name':names[c['local_date'],c['variant_id']]} for c in snapshot['workload_changes']]
    if not changes and reference and len(reference['sessions'])==len(preview['sessions']):
        for old,new in zip(reference['sessions'],preview['sessions']):
            for a,b in zip(old['exercises'],new['exercises']):
                if a['variant_id']==b['variant_id'] and a['sets']!=b['sets']:
                    changes.append(dict(local_date=new['local_date'],variant_id=b['variant_id'],exercise_name=b['name'],
                        reference_sets=a['sets'],candidate_sets=b['sets'],removed_sets=a['sets']-b['sets']))
    evidence=snapshot.get('evidence') or {}
    bands={b['region']:b for b in evidence.get('bundle',{}).get('standard',{}).get('direct_region_bands',[])}
    counts={r['region']:r['primary_sets'] for r in preview['regions']}
    conflicts=[dict(region=r,primary_sets=counts[r],proposed_minimum=bands[r]['minimum'],proposed_maximum=bands[r]['maximum'],
        interpretation='Conflict with an unapproved candidate range; not an established biological minimum or medical finding.') for r in preview['dose_conflicts']]
    alternative_conflicts=[]
    if reference:
        alternative_counts={r['region']:r['primary_sets'] for r in reference['regions']}
        alternative_conflicts=[dict(region=r,primary_sets=alternative_counts[r],proposed_minimum=bands[r]['minimum'],
            proposed_maximum=bands[r]['maximum'],interpretation='Unapproved proposed range, not a biological minimum.') for r in reference['dose_conflicts'] if r in bands]
    plan=evidence.get('result',{}).get('plan',{})
    timing=[dict(local_date=s['local_date'],phases=s['duration']) for s in plan.get('sessions',[])]
    return dict(schema_version='inactive-candidate-informed-summary-v2',scientific_status='review_required',
        candidate=_workload(preview),reference=_workload(reference),workload_changes=changes,
        proposed_range_conflicts=conflicts,alternative_range_conflicts=alternative_conflicts,timing_assumptions=timing,
        limitations=list(preview['limitations']),
        explanation='Less scheduled work may mean less hypertrophy opportunity. Both candidates use provisional science and synthetic equipment/time assumptions. One acknowledgement covers the complete versioned comparison; it is not scientific or medical approval.',
        alternatives=('Review the longer candidate with a larger time allowance.','Revise dates/equipment/preferences and review a new candidate.','Decline the candidate; existing Authored work is preserved.'))


def compact_terms(document,audit_acknowledgements):
    summary=consent_summary(document['snapshot'])
    summary_hash=content_hash(summary)
    terms=dict(protocol=COMPACT_PROTOCOL,text=ACKNOWLEDGEMENT,subject=document['subject'],mode='customized',
        proposal_id=document['proposal_id'],plan_version=document['plan_version'],snapshot_hash=document['snapshot_hash'],
        summary=summary,summary_hash=summary_hash,audit_acknowledgements=audit_acknowledgements)
    return terms,content_hash(terms)
