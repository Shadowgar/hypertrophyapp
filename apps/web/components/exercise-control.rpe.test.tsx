import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import ExerciseControlModule, { SetInputCard, useExerciseControl } from "./exercise-control";

test("actual RPE stays blank independently of targets and resets only after acknowledgement", async () => {
  let acknowledge!: () => void;
  const calls: unknown[] = [];
  render(<ExerciseControlModule exerciseId="effort" totalSets={2} recommendedWorkingWeight={55.7}
    repRange={[8, 12]} onSetComplete={async (_id, _index, performed) => {
      calls.push(performed); await new Promise<void>(resolve => { acknowledge = resolve; });
    }} />);
  const effort = screen.getByRole("spinbutton", { name: /Actual RPE/ });
  expect(effort).toHaveValue(null);
  fireEvent.change(effort, { target: { value: "9.5" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  expect(calls).toEqual([{ reps: 8, weight: 55.7, rpe: 9.5 }]);
  expect(effort).toHaveValue(9.5);
  acknowledge();
  await waitFor(() => expect(effort).toHaveValue(null));
});

test("failed RPE submission retries the exact performed values despite later edits", async () => {
  const calls: unknown[] = [];
  render(<ExerciseControlModule exerciseId="retry-effort" totalSets={2} recommendedWorkingWeight={50}
    onSetComplete={async (_id, _index, performed) => {
      calls.push(performed); if (calls.length === 1) throw new Error("Lost acknowledgement");
    }} />);
  const effort = screen.getByRole("spinbutton", { name: /Actual RPE/ });
  fireEvent.change(effort, { target: { value: "8" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Complete Set" })).toBeEnabled());
  expect(effort).toHaveValue(8);
  fireEvent.change(effort, { target: { value: "6" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(calls).toHaveLength(2));
  expect(calls).toEqual([{ reps: 8, weight: 50, rpe: 8 }, { reps: 8, weight: 50, rpe: 8 }]);
  await waitFor(() => expect(effort).toHaveValue(null));
});

test("RPE outside0–10 blocks submission while blank remains explicitly unknown", async () => {
  const calls: unknown[] = [];
  render(<ExerciseControlModule exerciseId="effort-bounds" totalSets={2} onSetComplete={(_id, _index, values) => { calls.push(values); }} />);
  const effort = screen.getByRole("spinbutton", { name: /Actual RPE/ });
  fireEvent.change(effort, { target: { value: "10.5" } });
  expect(screen.getByRole("button", { name: "Complete Set" })).toBeDisabled();
  fireEvent.change(effort, { target: { value: "" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(calls).toEqual([{ reps: 8, weight: 0, rpe: null }]));
});

test("authoritative advice refresh preserves an explicitly edited next-set rep draft", () => {
  function Input({ range }: { range: [number, number] }) {
    const ctrl = useExerciseControl({ exerciseId: "stable-source-slot", totalSets: 3, repRange: range });
    return <SetInputCard exerciseId="stable-source-slot" ctrl={ctrl} guidanceLine="Fixed authored targets" />;
  }
  const view = render(<Input range={[8, 12]} />);
  fireEvent.change(screen.getByRole("spinbutton", { name: "Reps" }), { target: { value: "11" } });
  view.rerender(<Input range={[8, 12]} />);
  expect(screen.getByRole("spinbutton", { name: "Reps" })).toHaveValue(11);
});

test("explicit zero actual load is retained instead of replaced by a suggested load", async () => {
  const calls: unknown[] = [];
  render(<ExerciseControlModule exerciseId="zero-override" recommendedWorkingWeight={40} onSetComplete={(_id, _index, values) => { calls.push(values); }} />);
  fireEvent.change(screen.getByRole("spinbutton", { name: "Weight (lb)" }), { target: { value: "0" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(calls).toEqual([{ reps: 8, weight: 0, rpe: null }]));
});


test.each([false, true])("next-set drafts adopt refreshed targets only after acknowledgement (lost response: %s)", async lost => {
  let acknowledge!: () => void;
  const calls: unknown[] = [];
  const complete = async (_id: string, _index: number, performed: unknown) => {
    calls.push(performed);
    if (calls.length === 1) {
      if (lost) throw new Error("Lost acknowledgement");
      await new Promise<void>(resolve => { acknowledge = resolve; });
    }
  };
  function Input({ next }: { next: boolean }) {
    const ctrl = useExerciseControl({ exerciseId: "acknowledged-source-slot", totalSets: 3,
      recommendedWorkingWeight: next ? 44.1 : 55.7, recommendedWeightCanonicalKg: next ? 20 : 25.25,
      repRange: next ? [6, 8] : [8, 12], onSetComplete: complete, skipTimerOnComplete: true });
    return <SetInputCard exerciseId="acknowledged-source-slot" ctrl={ctrl} guidanceLine="Fixed authored targets" />;
  }
  const view = render(<Input next={false} />);
  fireEvent.change(screen.getByRole("spinbutton", { name: "Weight (lb)" }), { target: { value: "65" } });
  fireEvent.change(screen.getByRole("spinbutton", { name: "Reps" }), { target: { value: "7" } });
  fireEvent.change(screen.getByRole("spinbutton", { name: /Actual RPE/ }), { target: { value: "10" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  if (lost) await waitFor(() => expect(screen.getByRole("button", { name: "Complete Set" })).toBeEnabled());
  view.rerender(<Input next />);
  expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(65);
  expect(screen.getByRole("spinbutton", { name: "Reps" })).toHaveValue(7);
  if (lost) fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  else await act(async () => { acknowledge(); });
  await waitFor(() => expect(screen.getByRole("spinbutton", { name: "Weight (lb)" })).toHaveValue(44.1));
  expect(screen.getByRole("spinbutton", { name: "Reps" })).toHaveValue(6);
  expect(calls).toEqual(Array.from({ length: lost ? 2 : 1 }, () => ({ reps: 7, weight: 65, rpe: 10 })));
  fireEvent.change(screen.getByRole("spinbutton", { name: /Actual RPE/ }), { target: { value: "8" } });
  fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
  await waitFor(() => expect(calls).toHaveLength(lost ? 3 : 2));
  expect(calls.at(-1)).toEqual({ reps: 6, weight: 44.1, rpe: 8, canonicalWeight: 20 });
});

test('Customized records explicit RIR, technique and pain without rounding real pound loads',async()=>{
  const calls:unknown[]=[];
  function Customized(){const ctrl=useExerciseControl({exerciseId:'customized',customizedEvidence:true,weightUnit:'lb',totalSets:2,requireWeight:true,onSetComplete:(_id,_i,values)=>{calls.push(values);}});
    return <SetInputCard exerciseId="customized" ctrl={ctrl} guidanceLine="Actual setup"/>;}
  render(<Customized/>);
  expect(screen.getByLabelText('Actual RIR (optional)')).toHaveValue(null);
  fireEvent.change(screen.getByLabelText('Weight (lb)'),{target:{value:'11'}});
  fireEvent.change(screen.getByLabelText('Actual RIR (optional)'),{target:{value:'5'}});
  fireEvent.change(screen.getByLabelText('Technique quality'),{target:{value:'acceptable'}});
  fireEvent.change(screen.getByLabelText('Pain during this set'),{target:{value:'no'}});
  fireEvent.click(screen.getByRole('button',{name:'Complete Set'}));
  await waitFor(()=>expect(calls).toHaveLength(1));
  expect(calls[0]).toMatchObject({actual_rir:5,technique_quality:'acceptable',pain:false});
  expect((calls[0] as {canonicalWeight:number}).canonicalWeight).toBeCloseTo(4.98951607,10);
  expect(screen.getByLabelText('Actual RIR (optional)')).toHaveValue(null);
});

test('Customized correction can explicitly clear recorded RIR while preserving receipt identity',async()=>{
  const {LoadIntelligencePanel}=await import('./exercise-control');const correct=vi.fn(async(_receipt:unknown,_values:unknown)=>{});
  render(<LoadIntelligencePanel receiptOnly guidance={null} completed={1} total={2} loadContext={{unit:'kg',display_unit:'kg',basis:'per_hand'}} onContextChange={()=>{}} onPreview={async()=>{}} overrideReason="" onOverrideReason={()=>{}} onCorrect={correct} effectiveSets={[{id:'actual-receipt',set_index:1,reps:12,weight:10,rpe:null,actual_rir:5,set_kind:'work',parent_set_index:null,technique:null,created_at:'2026-10-19'}]}/>);
  fireEvent.click(screen.getByRole('button',{name:'Edit set 1'}));
  fireEvent.change(screen.getByLabelText('Corrected actual RIR'),{target:{value:''}});
  fireEvent.click(screen.getByRole('button',{name:'Save correction'}));
  await waitFor(()=>expect(correct).toHaveBeenCalled());
  expect(correct.mock.calls[0][0]).toMatchObject({id:'actual-receipt'});
  expect(correct.mock.calls[0][1]).toMatchObject({actual_rir:null,reps:12,weight:10});
});
