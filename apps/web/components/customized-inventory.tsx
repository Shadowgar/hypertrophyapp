'use client';

import {useCallback, useEffect, useRef, useState} from 'react';
import {Button} from '@/components/ui/button';
import {customizedApi, getToken} from '@/lib/api';
import type {InventoryDocument, InventoryKind, InventorySetup, InventoryUnit, InventoryVariant, LocationProfile, StrengthReport} from '@/lib/customized-inventory';

export type CustomizedInventoryEditorProps = {
  document: InventoryDocument | null;
  equipment: string[];
  variants: InventoryVariant[];
  onSaved: (document: InventoryDocument) => void;
  accountToken?: string | null;
};
type WeightDraft = {weight: string; count: string};
type SetupDraft = {
  key: string; label: string; kind: InventoryKind | ''; unit: InventoryUnit | '';
  weights: WeightDraft[]; plates: WeightDraft[]; bar_weight: string;
  stack: {minimum: string; maximum: string; increment: string} | null;
  min_load: string; max_load: string; setup_note: string;
};
type ReportDraft = Omit<StrengthReport, 'load' | 'unit' | 'kind'> & {load: string; unit: InventoryUnit | ''; kind: StrengthReport['kind'] | ''; saved?: boolean; needs_reentry?: boolean};
type Draft = {location_id: string; location_name: string; setups: SetupDraft[]; assignments: Record<string, string>; unavailable_variants: string[]; reports: ReportDraft[]};
const text = (value: number | null) => value === null ? '' : String(value);
function loadDraft(profile: LocationProfile | null): Draft {
  return {
    location_id: profile?.location_id ?? crypto.randomUUID(), location_name: profile?.location_name ?? '',
    setups: (profile?.setups ?? []).map(s => ({...s, weights: s.weights.map(w => ({weight: text(w.weight), count: text(w.count)})), plates: s.plates.map(w => ({weight: text(w.weight), count: text(w.count)})),
      bar_weight: text(s.bar_weight), min_load: text(s.min_load), max_load: text(s.max_load), stack: s.stack ? {minimum: text(s.stack.minimum), maximum: text(s.stack.maximum), increment: text(s.stack.increment)} : null})),
    assignments: {...profile?.assignments}, unavailable_variants: [...(profile?.unavailable_variants ?? [])],
    reports: (profile?.strength_reports ?? []).map(r => ({...r, load: text(r.load), saved: true})),
  };
}
function number(value: string, label: string, zeroAllowed = false): number {
  const n = value.trim() === '' ? NaN : Number(value);
  if (!Number.isFinite(n) || n > 2000 || (zeroAllowed ? n < 0 : n <= 0)) throw new Error(`${label}: enter an actual ${zeroAllowed ? 'nonnegative' : 'positive'} value no greater than 2000.`);
  return n;
}
function compatible(variant: InventoryVariant, setup: SetupDraft) {
  return setup.kind === ({dumbbell: 'dumbbell', machine: 'machine_stack', bodyweight: 'bodyweight'} as Record<string, string>)[variant.implement];
}
function serialize(draft: Draft, equipment: string[], variants: InventoryVariant[]): LocationProfile {
  if (!draft.location_name.trim()) throw new Error('Enter a location name.');
  const rows = (entries: WeightDraft[], label: string) => entries.map(w => {
    const count = number(w.count, `${label} count`);
    if (!Number.isInteger(count) || count > 128) throw new Error(`${label}: counts must be whole numbers from 1 to 128.`);
    return {weight: number(w.weight, `${label} weight`), count};
  });
  if (draft.setups.length > 64 || draft.reports.length > 32) throw new Error('Keep at most 64 setups and 32 historical reports.');
  const setups: InventorySetup[] = draft.setups.map((s, i) => {
    const label = `Setup ${i + 1}`;
    if (!s.label.trim() || !s.setup_note.trim() || !s.kind || !s.unit) throw new Error(`${label}: enter a name, kind, unit and identity/range notes.`);
    if ((s.kind === 'dumbbell' || (s.kind === 'machine_stack' && !s.stack)) && s.weights.length === 0) throw new Error(`${label}: declare the actual weights available.`);
    const stack = s.kind === 'machine_stack' && s.stack ? {minimum: number(s.stack.minimum, `${label} stack minimum`), maximum: number(s.stack.maximum, `${label} stack maximum`), increment: number(s.stack.increment, `${label} stack increment`)} : null;
    if (stack && stack.minimum > stack.maximum) throw new Error(`${label}: stack minimum exceeds maximum.`);
    const min_load = s.min_load === '' ? null : number(s.min_load, `${label} minimum usable load`, true);
    const max_load = s.max_load === '' ? null : number(s.max_load, `${label} maximum usable load`);
    if (min_load !== null && max_load !== null && min_load > max_load) throw new Error(`${label}: minimum usable load exceeds maximum.`);
    return {key: s.key, label: s.label.trim(), kind: s.kind, unit: s.unit, setup_note: s.setup_note.trim(), min_load, max_load,
      weights: s.kind === 'dumbbell' || (s.kind === 'machine_stack' && !stack) ? rows(s.weights, label) : [],
      plates: s.kind === 'barbell' ? rows(s.plates, label) : [], bar_weight: s.kind === 'barbell' ? number(s.bar_weight, `${label} bar weight`) : null, stack};
  });
  const assignments = {...draft.assignments};
  for (const [id, key] of Object.entries(assignments)) {
    const variant = variants.find(v => v.id === id), setup = draft.setups.find(s => s.key === key);
    if (!variant || !setup || !compatible(variant, setup) || draft.unavailable_variants.includes(id)) throw new Error('Review exercise equipment assignments before saving.');
  }
  const strength_reports: StrengthReport[] = draft.reports.map((r, i) => {
    const setup = setups.find(s => s.key === assignments[r.variant_id]);
    if (!setup || !r.kind || !r.unit || !r.confirmed || !/^\d{4}-\d{2}-\d{2}$/.test(r.observed_on)) throw new Error(`Report ${i + 1}: choose an assigned exercise, kind, date and confirm the historical observation.`);
    if (r.needs_reentry || r.setup_key !== setup.key) throw new Error(`Report ${i + 1}: setup identity changed. Remove this profile report and re-enter it for the actual setup; workout history is retained.`);
    if (r.kind === 'e1rm' && !r.method_reference?.trim()) throw new Error(`Report ${i + 1}: an estimated 1RM requires its method or reference.`);
    return {report_id: r.report_id, variant_id: r.variant_id, setup_key: setup.key, kind: r.kind, load: number(r.load, `Report ${i + 1} load`), unit: r.unit,
      observed_on: r.observed_on, confirmed: r.confirmed, method_reference: r.method_reference?.trim() || null, ...(r.setup_fingerprint !== undefined ? {setup_fingerprint: r.setup_fingerprint} : {})};
  });
  return {location_id: draft.location_id, location_name: draft.location_name.trim(), equipment: [...equipment], setups, assignments, unavailable_variants: [...draft.unavailable_variants], strength_reports};
}
function Field({label, value, onChange, numeric = false}: {label: string; value: string; onChange: (value: string) => void; numeric?: boolean}) {
  return <label className="block text-sm">{label}<input className="ui-input block w-full min-w-0" aria-label={label} type={numeric ? 'number' : 'text'} step={numeric ? 'any' : undefined} value={value} onChange={e => onChange(e.target.value)}/></label>;
}

export function CustomizedInventoryEditor({document, equipment, variants, onSaved, accountToken}: CustomizedInventoryEditorProps) {
  const [initialToken] = useState(getToken);
  const documentToken = accountToken === undefined ? initialToken : accountToken;
  const [draft, setDraft] = useState(() => loadDraft(document?.profile ?? null));
  const [revision, setRevision] = useState(document?.revision ?? 0);
  const [blocked, setBlocked] = useState(document === null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const epoch = useRef(0);
  const mounted = useRef(false);
  const loadedToken = useRef<string | null | undefined>(undefined);
  const reset = useCallback(() => {
    epoch.current++; loadedToken.current = undefined;
    setDraft(loadDraft(null)); setBlocked(true); setBusy(false); setError(''); setStatus('Account changed. Reload your inventory before saving.');
  }, []);
  useEffect(() => {
    if (documentToken !== getToken()) { reset(); return; }
    epoch.current++;
    loadedToken.current = documentToken;
    setDraft(loadDraft(document?.profile ?? null)); setRevision(document?.revision ?? 0);
    setBlocked(document === null); setBusy(false); setError(''); setStatus('');
  }, [documentToken, document, reset]);
  useEffect(() => {
    mounted.current = true;
    const invalidate = () => {epoch.current++;};
    const changed = () => { if (loadedToken.current !== getToken()) reset(); };
    window.addEventListener('hypertrophy:auth-token-changed', reset);
    window.addEventListener('storage', changed); window.addEventListener('focus', changed);
    return () => {mounted.current = false; invalidate(); window.removeEventListener('hypertrophy:auth-token-changed', reset); window.removeEventListener('storage', changed); window.removeEventListener('focus', changed);};
  }, [reset]);
  function updateSetup(key: string, change: Partial<SetupDraft>) {
    setDraft(d => {
      const previous = d.setups.find(s => s.key === key);
      const changedIdentity = previous && (['kind', 'unit', 'setup_note'] as const).some(field => field in change && change[field] !== previous[field]);
      return {...d, setups: d.setups.map(s => s.key === key ? {...s, ...change} : s),
        reports: changedIdentity ? d.reports.map(r => r.setup_key === key ? {...r, needs_reentry: true} : r) : d.reports};
    });
  }
  function updateReport(id: string, change: Partial<ReportDraft>) {
    setDraft(d => ({...d, reports: d.reports.map(r => r.report_id === id ? {...r, ...change,
      needs_reentry: r.needs_reentry || (r.saved && change.variant_id !== undefined && change.variant_id !== r.variant_id)} : r)}));
  }
  function removeSetup(key: string) {
    setDraft(d => ({...d, setups: d.setups.filter(s => s.key !== key), assignments: Object.fromEntries(Object.entries(d.assignments).filter(([, value]) => value !== key)), reports: d.reports.filter(r => r.setup_key !== key)}));
  }
  async function save() {
    if (!mounted.current || blocked || busy) return;
    const token = loadedToken.current;
    if (token === undefined || token !== getToken()) { reset(); return; }
    const attempt = epoch.current;
    const current = () => {
      if (!mounted.current) return false;
      if (loadedToken.current !== undefined && loadedToken.current !== getToken()) { reset(); return false; }
      return attempt === epoch.current && token === loadedToken.current && token === getToken();
    };
    setError(''); setStatus('');
    try {
      const profile = serialize(draft, equipment, variants);
      setBusy(true);
      const saved = await customizedApi.saveProfile(revision, profile);
      if (!current()) return;
      setRevision(saved.revision); setDraft(loadDraft(saved.profile)); setStatus('Inventory saved. Review a new program preview to use availability changes.'); onSaved(saved);
    } catch (e) {if (current()) setError(e instanceof Error ? e.message : 'Inventory could not be saved.');}
    finally {if (current()) setBusy(false);}
  }
  return <details className="space-y-3 rounded border border-zinc-700 p-3">
    <summary className="min-h-11 cursor-pointer py-2 font-semibold">Equipment inventory and calibration</summary>
    <p className="text-sm">Record equipment you can actually use at this location. Editing or removing inventory keeps accepted programs and workout history. An altered setup needs its own calibration; loads are not invented.</p>
    <fieldset disabled={busy || blocked} className="min-w-0 space-y-4">
      <Field label="Location name" value={draft.location_name} onChange={location_name => setDraft(d => ({...d, location_name}))}/>
      <p className="text-sm">Confirmed equipment: {equipment.length ? equipment.join(', ').replaceAll('_', ' ') : 'Confirm equipment availability before saving.'}</p>
      {draft.setups.map((s, i) => <section key={s.key} aria-label={`Equipment setup ${i + 1}`} className="space-y-3 rounded border border-zinc-700 p-3">
        <h3 className="font-semibold">Setup {i + 1}</h3>
        <Field label={`Setup ${i + 1} name`} value={s.label} onChange={label => updateSetup(s.key, {label})}/>
        <label className="block text-sm">Setup {i + 1} kind<select className="ui-input block w-full" aria-label={`Setup ${i + 1} kind`} value={s.kind} onChange={e => updateSetup(s.key, {kind: e.target.value as SetupDraft['kind'], weights: [], plates: [], bar_weight: '', stack: null})}>
          <option value="">Choose actual equipment</option><option value="dumbbell">Dumbbells</option><option value="barbell">Barbell and plates</option><option value="machine_stack">Machine stack</option><option value="bodyweight">Bodyweight setup</option></select></label>
        <label className="block text-sm">Setup {i + 1} unit<select className="ui-input block w-full" aria-label={`Setup ${i + 1} unit`} value={s.unit} onChange={e => updateSetup(s.key, {unit: e.target.value as SetupDraft['unit']})}><option value="">Choose labeled unit</option><option value="kg">kg</option><option value="lb">lb</option></select></label>
        <Field label={`Setup ${i + 1} identity and range notes`} value={s.setup_note} onChange={setup_note => updateSetup(s.key, {setup_note})}/>
        <p className="text-xs">Identify the exact machine, handles, bench position and range of motion as relevant. Changed equipment or setup may make old loads incomparable.</p>
        {s.kind === 'dumbbell' && <p className="text-sm">Enter each individual dumbbell weight and how many you have. Per-hand exercises use one hand&apos;s weight; matching-pair exercises require two available. Total external load is separately defined by the exercise.</p>}
        {s.kind === 'barbell' && <><p className="text-sm">Record the actual bar and all plates across both sleeves. Only equal plate pairs can be loaded. Current Customized exercises do not use barbell setups.</p><Field numeric label={`Setup ${i + 1} bar weight`} value={s.bar_weight} onChange={bar_weight => updateSetup(s.key, {bar_weight})}/></>}
        {s.kind === 'bodyweight' && <p className="text-sm">Bodyweight has no invented external load or attainable weight ladder.</p>}
        {s.kind === 'machine_stack' && <><p className="text-sm">Use actual labeled stack loads; machine labels are not interchangeable between machines.</p>
          <label className="flex min-h-11 items-center gap-2"><input type="checkbox" checked={s.stack !== null} onChange={e => updateSetup(s.key, {weights: [], stack: e.target.checked ? {minimum: '', maximum: '', increment: ''} : null})}/>Setup {i + 1} has a confirmed uniform stack range instead of individual labels</label>
          {s.stack && <div className="grid gap-3 sm:grid-cols-3">{(['minimum', 'maximum', 'increment'] as const).map(field => <Field key={field} numeric label={`Setup ${i + 1} stack ${field}`} value={s.stack![field]} onChange={value => updateSetup(s.key, {stack: {...s.stack!, [field]: value}})}/>)}</div>}
        </>}
        {(s.kind === 'barbell' || s.kind === 'dumbbell' || (s.kind === 'machine_stack' && !s.stack)) && (() => {
          const field = s.kind === 'barbell' ? 'plates' : 'weights', rows = s[field];
          return <div className="space-y-2">{rows.map((row, j) => <div key={j} className="grid gap-2 sm:grid-cols-3">
            <Field numeric label={`Setup ${i + 1} ${field === 'plates' ? 'plate' : 'weight'} ${j + 1}`} value={row.weight} onChange={weight => updateSetup(s.key, {[field]: rows.map((w, k) => k === j ? {...w, weight} : w)})}/>
            <Field numeric label={`Setup ${i + 1} count ${j + 1}`} value={row.count} onChange={count => updateSetup(s.key, {[field]: rows.map((w, k) => k === j ? {...w, count} : w)})}/>
            <Button type="button" variant="ghost" onClick={() => updateSetup(s.key, {[field]: rows.filter((_, k) => j !== k)})}>Remove {field === 'plates' ? 'plate' : 'weight'} {j + 1} from setup {i + 1}</Button>
          </div>)}<Button type="button" variant="secondary" disabled={rows.length >= (field === 'plates' ? 32 : 128)} onClick={() => updateSetup(s.key, {[field]: [...rows, {weight: '', count: ''}]})}>Add {field === 'plates' ? 'plate' : 'weight'} to setup {i + 1}</Button></div>;
        })()}
        {s.kind && s.kind !== 'bodyweight' && <div className="grid gap-3 sm:grid-cols-2"><Field numeric label={`Setup ${i + 1} minimum usable load`} value={s.min_load} onChange={min_load => updateSetup(s.key, {min_load})}/><Field numeric label={`Setup ${i + 1} maximum usable load`} value={s.max_load} onChange={max_load => updateSetup(s.key, {max_load})}/><p className="text-xs sm:col-span-2">Optional limits in this setup&apos;s unit. Leave blank when not declared.</p></div>}
        <Button type="button" variant="ghost" onClick={() => removeSetup(s.key)}>Remove setup {i + 1} and its profile reports</Button>
      </section>)}
      <Button type="button" variant="secondary" disabled={draft.setups.length >= 64} onClick={() => setDraft(d => ({...d, setups: [...d.setups, {key: crypto.randomUUID(), label: '', kind: '', unit: '', weights: [], plates: [], bar_weight: '', stack: null, min_load: '', max_load: '', setup_note: ''}]}))}>Add equipment setup</Button>
      <details><summary className="min-h-11 cursor-pointer py-2">Exercise availability and equipment assignments</summary>
        <p className="text-sm">Assign each exercise to its actual setup. Leaving an exercise unassigned does not create equipment loads. Exclusions affect future previews; accepted programs stay unchanged.</p>
        {variants.map(v => <div key={v.id} className="space-y-2 border-t border-zinc-700 py-3"><p>{v.name} · load basis: {v.basis.replaceAll('_', ' ')}</p>
          <label className="flex min-h-11 items-center gap-2"><input aria-label={`Unavailable: ${v.name}`} type="checkbox" checked={draft.unavailable_variants.includes(v.id)} onChange={e => setDraft(d => {
            const assignments = {...d.assignments}; if (e.target.checked) delete assignments[v.id];
            return {...d, assignments, unavailable_variants: e.target.checked ? [...d.unavailable_variants, v.id] : d.unavailable_variants.filter(id => id !== v.id)};
          })}/>Unavailable: {v.name}</label>
          <label className="block text-sm">Equipment setup for {v.name}<select aria-label={`Equipment setup for ${v.name}`} className="ui-input block w-full" value={draft.assignments[v.id] ?? ''} disabled={draft.unavailable_variants.includes(v.id)} onChange={e => setDraft(d => {const assignments = {...d.assignments}; if (e.target.value) assignments[v.id] = e.target.value; else delete assignments[v.id]; return {...d, assignments};})}>
            <option value="">Not assigned / needs calibration</option>{draft.setups.filter(s => compatible(v, s)).map(s => <option key={s.key} value={s.key}>{s.label || 'Unnamed setup'}</option>)}</select></label>
        </div>)}
      </details>
      <details><summary className="min-h-11 cursor-pointer py-2">Optional historical strength reports</summary>
        <p className="text-sm">Historical information only. Record a known prior 1RM or estimated 1RM for this exact exercise and setup. No maximum testing is requested. A report does not automatically calculate a working load; actual comparable training remains separate evidence.</p>
        {draft.reports.map((r, i) => {
          const setup = draft.setups.find(s => s.key === draft.assignments[r.variant_id]);
          return <section key={r.report_id} className="space-y-2 border-t border-zinc-700 py-3"><h3>Report {i + 1}</h3>
            {(r.needs_reentry || (setup && (setup.key !== r.setup_key || setup.unit !== r.unit))) && <p>Setup identity changed. Remove this profile report and re-enter it for the actual setup. Workout history is retained.</p>}
            <label className="block text-sm">Report {i + 1} exercise<select className="ui-input block w-full" aria-label={`Report ${i + 1} exercise`} value={r.variant_id} onChange={e => updateReport(r.report_id, {variant_id: e.target.value, setup_key: draft.assignments[e.target.value] ?? '', unit: draft.setups.find(s => s.key === draft.assignments[e.target.value])?.unit ?? ''})}><option value="">Choose an assigned exercise</option>{variants.filter(v => draft.assignments[v.id] && !draft.unavailable_variants.includes(v.id)).map(v => <option key={v.id} value={v.id}>{v.name}</option>)}</select></label>
            <p className="text-sm">Actual setup: {setup?.label || 'Choose an assigned exercise'} · Unit: {setup?.unit || 'Choose setup unit'}</p>
            <label className="block text-sm">Report {i + 1} kind<select className="ui-input block w-full" aria-label={`Report ${i + 1} kind`} value={r.kind} onChange={e => updateReport(r.report_id, {kind: e.target.value as ReportDraft['kind']})}><option value="">Choose known report type</option><option value="1rm">Historical 1RM</option><option value="e1rm">Historical estimated 1RM</option></select></label>
            <label className="block text-sm">Report {i + 1} unit<select className="ui-input block w-full" aria-label={`Report ${i + 1} unit`} value={r.unit} onChange={e=>updateReport(r.report_id,{unit:e.target.value as 'kg'|'lb'})}><option value="kg">kg</option><option value="lb">lb</option></select></label>
            <Field numeric label={`Report ${i + 1} load`} value={r.load} onChange={load => updateReport(r.report_id, {load})}/>
            <label className="block text-sm">Report {i + 1} observed date<input type="date" className="ui-input block w-full" aria-label={`Report ${i + 1} observed date`} value={r.observed_on} onChange={e => updateReport(r.report_id, {observed_on: e.target.value})}/></label>
            <Field label={`Report ${i + 1} estimation method or reference`} value={r.method_reference ?? ''} onChange={method_reference => updateReport(r.report_id, {method_reference})}/>
            <label className="flex min-h-11 items-center gap-2"><input type="checkbox" aria-label={`Report ${i + 1} confirmed historical observation`} checked={r.confirmed} onChange={e => updateReport(r.report_id, {confirmed: e.target.checked})}/>I confirm this historical observation and its exercise/setup basis.</label>
            <Button type="button" variant="ghost" onClick={() => setDraft(d => ({...d, reports: d.reports.filter(item => item.report_id !== r.report_id)}))}>Remove report {i + 1}</Button>
          </section>;
        })}
        <Button type="button" variant="secondary" disabled={draft.reports.length >= 32} onClick={() => setDraft(d => ({...d, reports: [...d.reports, {report_id: crypto.randomUUID(), variant_id: '', setup_key: '', unit: '', kind: '', load: '', observed_on: '', confirmed: false, method_reference: null}]}))}>Add historical strength report</Button>
      </details>
      <Button type="button" disabled={blocked || busy || equipment.length === 0} onClick={() => void save()}>{busy ? 'Saving inventory…' : 'Save inventory'}</Button>
    </fieldset>
    {error && <p role="alert">{error}</p>}{status && <p role="status">{status}</p>}
  </details>;
}
