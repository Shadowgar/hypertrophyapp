import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { LoadIntelligencePanel } from "./exercise-control";
import { ApiError, type EffectiveLoadSet } from "@/lib/api";
import { acknowledgeLogCommand, getLogCommand, pendingCommandKey, retainLogPayload } from "@/lib/workout-identity";

const receipt: EffectiveLoadSet = { id: "original-receipt", set_index: 1, reps: 8, weight: 10,
  rpe: 8, actual_rir: null, set_kind: "work", parent_set_index: null, technique: null, created_at: "2026-10-22" };
const secondReceipt = { ...receipt, id: "second-receipt", set_index: 2 };
type Values = Parameters<React.ComponentProps<typeof LoadIntelligencePanel>["onCorrect"]>[1];

function correctionScenario(scope: string, lost: "before" | "after") {
  const requests: { receiptId: string; payload: Values & { command_id: string } }[] = [];
  const committed = new Map<string, EffectiveLoadSet>();
  let writes = 0;
  const correct = async (original: EffectiveLoadSet, values: Values) => {
    const key = pendingCommandKey(scope, "exercise-occurrence", `correct:${original.id}`);
    const payload = retainLogPayload(key, { ...values, command_id: getLogCommand(key) });
    requests.push({ receiptId: original.id, payload });
    if (requests.length === 1 && lost === "before") throw new Error("Connection lost before commit");
    if (!committed.has(payload.command_id)) {
      writes += 1;
      committed.set(payload.command_id, { ...original, ...payload, id: "replacement-receipt" });
    }
    if (requests.length === 1) throw new Error("Acknowledgement lost after commit");
    acknowledgeLogCommand(key);
  };
  const props: React.ComponentProps<typeof LoadIntelligencePanel> = { receiptOnly: true,
    allowRir: true, commandScope: scope, exerciseIdentity: "exercise-occurrence", guidance: null,
    completed: 2, total: 3, loadContext: { unit: "kg", display_unit: "lb", basis: "per_hand" },
    onContextChange: () => {}, onPreview: async () => {}, overrideReason: "", onOverrideReason: () => {},
    onCorrect: correct, effectiveSets: [receipt, secondReceipt] };
  return { props, requests, committed, writes: () => writes };
}

async function submitUncertainCorrection() {
  fireEvent.click(screen.getByRole("button", { name: "Edit set 1" }));
  fireEvent.change(screen.getByLabelText("Corrected reps"), { target: { value: "11" } });
  fireEvent.change(screen.getByLabelText("Corrected actual RPE"), { target: { value: "" } });
  fireEvent.change(screen.getByLabelText("Corrected actual RIR"), { target: { value: "3" } });
  fireEvent.change(screen.getByLabelText("Corrected technique quality"), { target: { value: "poor" } });
  fireEvent.change(screen.getByLabelText("Corrected pain report"), { target: { value: "no" } });
  fireEvent.change(screen.getByLabelText("Correction reason"), { target: { value: "Actual performance correction" } });
  fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/not confirmed/i));
}

test("uncertain correction cannot be bypassed by choosing another receipt", async () => {
  const scenario = correctionScenario("switch-recovery", "before");
  render(<LoadIntelligencePanel {...scenario.props} />);
  await submitUncertainCorrection();
  expect(screen.getByRole("button", { name: "Edit set 2" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Edit set 2" }));
  expect(screen.getByLabelText("Corrected reps")).toHaveValue(11);
  expect(screen.getByLabelText("Corrected reps")).toHaveAttribute("readonly");
  expect(screen.getByRole("button", { name: "Cancel correction" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Retry exact correction" }));
  await waitFor(() => expect(scenario.requests).toHaveLength(2));
  expect(scenario.requests[1]).toEqual(scenario.requests[0]);
  expect(scenario.writes()).toBe(1);
});

test.each(["before", "after"] as const)("closed correction reopens visibly and retries original receipt after %s-commit response loss", async lost => {
  const scenario = correctionScenario(`reopen-${lost}`, lost);
  const view = render(<LoadIntelligencePanel {...scenario.props} />);
  await submitUncertainCorrection();
  view.unmount();
  const updated = lost === "after" ? [...scenario.committed.values(), secondReceipt] : [receipt, secondReceipt];
  render(<LoadIntelligencePanel {...scenario.props} effectiveSets={updated} loadContext={{ ...scenario.props.loadContext, display_unit: "kg" }} />);
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(/not confirmed/i));
  expect(screen.getByLabelText("Corrected reps")).toHaveValue(11);
  expect(screen.getByLabelText("Corrected load (lb)")).toHaveAttribute("readonly");
  expect(screen.getByLabelText("Corrected actual RIR")).toHaveValue(3);
  expect(screen.getByLabelText("Corrected technique quality")).toHaveValue("poor");
  expect(screen.getByLabelText("Corrected pain report")).toHaveValue("no");
  fireEvent.click(screen.getByRole("button", { name: "Retry exact correction" }));
  await waitFor(() => expect(screen.queryByLabelText("Corrected reps")).not.toBeInTheDocument());
  expect(scenario.requests[1]).toEqual(scenario.requests[0]);
  expect(scenario.requests[1].receiptId).toBe(receipt.id);
  expect(scenario.writes()).toBe(1);
  expect(screen.getByRole("button", { name: "Edit set 2" })).toBeEnabled();
});

test("full reload recovers a lost committed correction without the original effective receipt", async () => {
  const scenario = correctionScenario("full-reload-recovery", "after");
  const view = render(<LoadIntelligencePanel {...scenario.props} />);
  await submitUncertainCorrection();
  view.unmount();
  vi.resetModules();
  const { LoadIntelligencePanel: ReloadedPanel } = await import("./exercise-control");
  const commands = await import("@/lib/workout-identity");
  const replay = async (original: EffectiveLoadSet, values: Values) => {
    const key = commands.pendingCommandKey("full-reload-recovery", "exercise-occurrence", `correct:${original.id}`);
    const payload = commands.retainLogPayload(key, { ...values, command_id: commands.getLogCommand(key) });
    expect({ receiptId: original.id, payload }).toEqual(scenario.requests[0]);
    expect(scenario.committed.has(payload.command_id)).toBe(true);
    commands.acknowledgeLogCommand(key);
  };
  render(<ReloadedPanel {...scenario.props} effectiveSets={[...scenario.committed.values(), secondReceipt]} onCorrect={replay} />);
  await waitFor(() => expect(screen.getByRole("button", { name: "Retry exact correction" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Retry exact correction" }));
  await waitFor(() => expect(screen.queryByLabelText("Corrected reps")).not.toBeInTheDocument());
  expect(scenario.writes()).toBe(1);
});

test("reopened recovery keeps its original command when an older mounted request acknowledges late", async () => {
  const scenario = correctionScenario("late-ack-recovery", "before");
  let finish!: () => void;
  const commands: string[] = [];
  const correct = async (original: EffectiveLoadSet, values: Values) => {
    const key = pendingCommandKey("late-ack-recovery", "exercise-occurrence", `correct:${original.id}`);
    const payload = retainLogPayload(key, { ...values, command_id: getLogCommand(key) });
    commands.push(payload.command_id);
    if (commands.length === 1) await new Promise<void>(resolve => { finish = resolve; });
    acknowledgeLogCommand(key);
  };
  const view = render(<LoadIntelligencePanel {...scenario.props} onCorrect={correct} />);
  fireEvent.click(screen.getByRole("button", { name: "Edit set 1" }));
  fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  view.unmount();
  render(<LoadIntelligencePanel {...scenario.props} onCorrect={correct} />);
  await waitFor(() => expect(screen.getByRole("button", { name: "Retry exact correction" })).toBeEnabled());
  await act(async () => { finish(); });
  fireEvent.click(screen.getByRole("button", { name: "Retry exact correction" }));
  await waitFor(() => expect(commands).toHaveLength(2));
  expect(commands[1]).toBe(commands[0]);
});

test("definitive validation rejection releases the attempted command for a revised correction", async () => {
  const scenario = correctionScenario("rejected-recovery", "before");
  const attempted: Values[] = [];
  const correct = async (_original: EffectiveLoadSet, values: Values) => {
    attempted.push(values);
    if (attempted.length === 1) throw new ApiError("Recorded load is invalid", 422);
  };
  render(<LoadIntelligencePanel {...scenario.props} onCorrect={correct} />);
  fireEvent.click(screen.getByRole("button", { name: "Edit set 1" }));
  fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Recorded load is invalid"));
  expect(screen.getByRole("button", { name: "Cancel correction" })).toBeEnabled();
  expect(screen.getByLabelText("Corrected reps")).not.toHaveAttribute("readonly");
  fireEvent.change(screen.getByLabelText("Corrected reps"), { target: { value: "12" } });
  fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  await waitFor(() => expect(attempted).toHaveLength(2));
  expect(attempted[1].reps).toBe(12);
  expect((attempted[1] as Values & { command_id: string }).command_id).not.toBe((attempted[0] as Values & { command_id: string }).command_id);
});

test("an uncertain correction restores only within its account and occurrence scope", async () => {
  const scenario = correctionScenario("account-one-occurrence-one", "before");
  const view = render(<LoadIntelligencePanel {...scenario.props} />);
  await submitUncertainCorrection();
  view.rerender(<LoadIntelligencePanel {...scenario.props} commandScope="account-two-occurrence-one" />);
  expect(screen.queryByLabelText("Corrected reps")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Edit set 2" })).toBeEnabled();
  view.rerender(<LoadIntelligencePanel {...scenario.props} />);
  await waitFor(() => expect(screen.getByRole("button", { name: "Retry exact correction" })).toBeEnabled());
  expect(scenario.requests).toHaveLength(1);
});

test.each([
  [409, "Set already voided or superseded; correct its effective replacement", true],
  [404, "Set not found", true],
  [409, "Command payload conflicts with the recorded request", false],
  [404, "Upstream route unavailable", false],
] as const)("correction target rejection %s %s releases recovery only when definitive", async (status, message, obsolete) => {
  const scope = `target-rejected-${status}-${obsolete}`;
  const scenario = correctionScenario(scope, "before");
  const correct = vi.fn(async () => { throw new ApiError(message, status); });
  render(<LoadIntelligencePanel {...scenario.props} onCorrect={correct} />);
  fireEvent.click(screen.getByRole("button", { name: "Edit set 1" }));
  fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  await waitFor(() => expect(correct).toHaveBeenCalledTimes(1));
  const { pendingLogPayload } = await import("@/lib/workout-identity");
  if (obsolete) {
    await waitFor(() => expect(screen.queryByLabelText("Corrected reps")).not.toBeInTheDocument());
    expect(screen.getByRole("status")).toHaveTextContent(message);
    expect(screen.getByRole("button", { name: "Edit set 2" })).toBeEnabled();
    expect(pendingLogPayload(pendingCommandKey(scope, "exercise-occurrence", "correct:original-receipt"))).toBeNull();
    expect(pendingLogPayload(pendingCommandKey(scope, "exercise-occurrence", "correction-recovery"))).toBeNull();
  } else {
    await waitFor(() => expect(screen.getByRole("button", { name: "Retry exact correction" })).toBeEnabled());
    expect(screen.getByLabelText("Corrected reps")).toHaveAttribute("readonly");
    expect(screen.getByRole("button", { name: "Edit set 2" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Retry exact correction" }));
    await waitFor(() => expect(correct).toHaveBeenCalledTimes(2));
    expect(correct.mock.calls[1]).toEqual(correct.mock.calls[0]);
  }
});

test.each(["RPE to RIR", "RIR to RPE"] as const)("Customized correction switches %s and retries the explicit counterpart clear after reload", async direction => {
  const scenario = correctionScenario(`switch-effort-${direction}`, "after");
  const original = { ...receipt, rpe: direction === "RPE to RIR" ? 8 : null, actual_rir: direction === "RIR to RPE" ? 3 : null };
  const props = { ...scenario.props, effectiveSets: [original, secondReceipt] };
  const view = render(<LoadIntelligencePanel {...props} />);
  fireEvent.click(screen.getByRole("button", { name: "Edit set 1" }));
  fireEvent.change(screen.getByLabelText(direction === "RPE to RIR" ? "Corrected actual RIR" : "Corrected actual RPE"), { target: { value: direction === "RPE to RIR" ? "2" : "8.5" } });
  expect(screen.getByLabelText(direction === "RPE to RIR" ? "Corrected actual RPE" : "Corrected actual RIR")).toHaveValue(null);
  fireEvent.click(screen.getByRole("button", { name: "Save correction" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Retry exact correction" })).toBeEnabled());
  expect(scenario.requests[0].payload).toMatchObject(direction === "RPE to RIR" ? { rpe: null, actual_rir: 2 } : { rpe: 8.5, actual_rir: null });
  expect(scenario.requests[0].payload).not.toHaveProperty("technique_quality");
  expect(scenario.requests[0].payload).not.toHaveProperty("pain");
  view.unmount();
  render(<LoadIntelligencePanel {...props} effectiveSets={[...scenario.committed.values(), secondReceipt]} />);
  fireEvent.click(await screen.findByRole("button", { name: "Retry exact correction" }));
  await waitFor(() => expect(screen.queryByLabelText("Corrected reps")).not.toBeInTheDocument());
  expect(scenario.requests[1]).toEqual(scenario.requests[0]);
  expect(scenario.writes()).toBe(1);
});
