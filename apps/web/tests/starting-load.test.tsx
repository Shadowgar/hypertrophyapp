import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { AtlasRunner } from "@/components/atlas-runner";
import { currentLoadDecision } from "@/lib/today-guidance";
import type { LoadDecision, LoadIntelligence } from "@/lib/api";
const decision = (
  weight: number | null,
  scope = "next_exposure",
): LoadDecision =>
  ({
    id: scope,
    evidence_revision: "r1",
    scope,
    action: weight === null ? "monitor" : "hold",
    recommended_weight: weight,
    known_baseline_weight: null,
    prefill_available: weight !== null,
    explanation: "Server history explanation",
    reason_codes: [],
    evidence: {
      completed_exposure_count: 0,
      comparable_completed_exposure_count: 0,
      consecutive_underperformance_count: 0,
      actual_rpe_count: 0,
      required_working_set_count: 3,
      actual_rpe_sufficient: false,
      effective_set_ids: [],
    },
    equipment_feasibility: { status: "unknown", limitations: [] },
    decision_trace: {},
  }) as LoadDecision;
const guidance = (): LoadIntelligence =>
  ({
    next_exposure: decision(null),
    remaining_sets: null,
    load_context: {
      unit: "kg",
      display_unit: "lb",
      basis: "machine_stack",
      equipment_key: "cable-A",
    },
    effective_sets: [],
    initial_estimate: {
      ...decision(29.48350405, "initial_calibration"),
      action: "estimate",
      status: "provisional",
      explanation: "A provisional estimate for your confirmed cable setup.",
    },
  }) as LoadIntelligence;
function runner(g = guidance(), extra: Record<string, unknown> = {}) {
  return (
    <AtlasRunner
      exercise={{
        id: "cross-body",
        exercise_occurrence_id: "slot-a",
        name: "Cross Body",
        sets: 3,
        rep_range: [10, 12],
        recommended_working_weight: null,
      }}
      name="Cross Body"
      completed={0}
      scope="synthetic-user/occurrence"
      guidance={g}
      context={g.load_context}
      receipts={[]}
      navigation={[]}
      onSelect={() => {}}
      onClose={() => {}}
      submit={async () => {}}
      onCorrect={async () => {}}
      details={null}
      warmups={null}
      technique={null}
      rest={null}
      endRest={() => {}}
      {...extra}
    />
  );
}
afterEach(cleanup);
test("server provisional decision prefills first set and transitions to remaining-set guidance", () => {
  const g = guidance();
  expect(currentLoadDecision(g, 0, 3)?.recommended_weight).toBe(29.48350405);
  g.remaining_sets = decision(25, "remaining_sets");
  expect(currentLoadDecision(g, 1, 3)?.recommended_weight).toBe(25);
  expect(currentLoadDecision(g, 3, 3)).toBeNull();
});
test("unavailable estimate and qualified history use existing server decision", () => {
  const g = guidance();
  g.initial_estimate!.status = "unavailable";
  expect(currentLoadDecision(g, 0, 3)).toBe(g.next_exposure);
  g.initial_estimate!.status = "provisional";
  g.initial_estimate!.prefill_available = false;
  expect(currentLoadDecision(g, 0, 3)).toBe(g.next_exposure);
  g.next_exposure = decision(40);
  expect(currentLoadDecision(g, 0, 3)).toBe(g.next_exposure);
});
test("estimate label and actual draft survive refreshed advice and reload", () => {
  const g = guidance();
  const view = render(runner(g));
  expect(
    screen.getByText("Suggested starting weight — estimate"),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("spinbutton", { name: "Working weight (lb)" }),
  ).toHaveValue(65);
  fireEvent.change(
    screen.getByRole("spinbutton", { name: "Working weight (lb)" }),
    { target: { value: "60" } },
  );
  const changed = guidance();
  changed.initial_estimate!.recommended_weight = 20;
  view.rerender(runner(changed));
  expect(
    screen.getByRole("spinbutton", { name: "Working weight (lb)" }),
  ).toHaveValue(60);
  view.unmount();
  render(runner(changed));
  expect(
    screen.getByRole("spinbutton", { name: "Working weight (lb)" }),
  ).toHaveValue(60);
});
function fillBenchmark() {
  fireEvent.click(screen.getByRole("radio", { name: "I know my 1-rep max." }));
  fireEvent.click(screen.getByText("Equipment and available loads"));
  fireEvent.change(screen.getByLabelText("Benchmark load (lb)"), {
    target: { value: "100" },
  });
  fireEvent.change(screen.getByLabelText("Observed date"), {
    target: { value: "2026-10-20" },
  });
  fireEvent.change(screen.getByLabelText("Setup details"), {
    target: { value: "Single cable, same attachment and ROM" },
  });
  fireEvent.change(screen.getByLabelText("Available loads (comma separated)"), {
    target: { value: "5, 35, 65, 100" },
  });
  fireEvent.click(screen.getByLabelText(/I confirm this benchmark/));
}
test("optional benchmark submits context without recording work; uncertain retry restores exact request", async () => {
  const requests: unknown[] = [];
  const save = vi.fn(async (payload) => {
    requests.push(structuredClone(payload));
    if (requests.length === 1) throw Error("lost response");
  });
  const submit = vi.fn();
  const view = render(runner(guidance(), { onSaveCalibration: save, submit }));
  fillBenchmark();
  fireEvent.click(
    screen.getByRole("button", { name: "Save benchmark and estimate" }),
  );
  await screen.findByText(/Benchmark save not confirmed/);
  expect(submit).not.toHaveBeenCalled();
  expect(requests[0]).toMatchObject({
    exercise_occurrence_id: "slot-a",
    load_context: { basis: "machine_stack", equipment_key: "cable-A" },
    calibration: {
      method: "known_1rm",
      load: 100,
      unit: "lb",
      observed_date: "2026-10-20",
      variant_id: "cross-body",
      confirmed: true,
      attainable: { unit: "lb", values: [5, 35, 65, 100] },
    },
  });
  view.unmount();
  render(runner(guidance(), { onSaveCalibration: save, submit }));
  fireEvent.click(
    screen.getByRole("button", { name: "Retry exact benchmark" }),
  );
  await waitFor(() => expect(requests).toHaveLength(2));
  expect(requests[1]).toEqual(requests[0]);
});

test("Today sends the calibration command and restores the server setup on reload", async () => {
  const { default: Today } = await import("@/app/today/page");
  let g = guidance();
  let saved = false;
  const requests: Array<{ url: string; body: any }> = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input, init) => {
      const url = String(input);
      if (url.includes("/plan/scheduling-context?"))
        return Response.json({
          timezone: "UTC",
          local_today: new Date().toISOString().slice(0, 10),
          week_start: "2026-10-19",
          selected_dates: [],
          placement_revision: 0,
          plan: null,
        });
      if (url.endsWith("/workout/today"))
        return Response.json({
          session_id: "template",
          workout_occurrence_id: "occurrence-a",
          title: "Synthetic calibration",
          date: new Date().toISOString().slice(0, 10),
          exercises: [
            {
              id: "cross-body",
              exercise_occurrence_id: "slot-a",
              name: "Cross Body",
              sets: 3,
              rep_range: [10, 12],
              recommended_working_weight: null,
              load_intelligence: g,
            },
          ],
        });
      if (url.includes("/progress"))
        return Response.json({
          completed_total: 0,
          planned_total: 3,
          percent_complete: 0,
          exercises: [
            {
              exercise_id: "cross-body",
              exercise_occurrence_id: "slot-a",
              completed_sets: 0,
              load_intelligence: g,
            },
          ],
        });
      if (url.includes("/soreness"))
        return Response.json([
          { entry_date: new Date().toISOString().slice(0, 10) },
        ]);
      if (url.endsWith("/initial-calibration")) {
        const body = JSON.parse(String(init?.body));
        requests.push({ url, body });
        g = {
          ...g,
          calibration: {
            id: "benchmark",
            revision: 1,
            requires_confirmation: false,
            input: body.calibration,
            load_context: body.load_context,
          },
          load_context: body.load_context,
        };
        saved = true;
        return Response.json(g);
      }
      return Response.json({});
    }),
  );
  const first = render(<Today />);
  fireEvent.click(screen.getByRole("button", { name: /Load today's workout/ }));
  fireEvent.click(await screen.findByRole("button", { name: /Cross Body/ }));
  fillBenchmark();
  fireEvent.change(screen.getByLabelText("Equipment identity"), {
    target: { value: "specific-cable" },
  });
  fireEvent.click(screen.getByLabelText(/I confirm this benchmark/));
  fireEvent.click(
    screen.getByRole("button", { name: "Save benchmark and estimate" }),
  );
  await waitFor(() => expect(saved).toBe(true));
  expect(requests[0].body.load_context.equipment_key).toBe("specific-cable");
  first.unmount();
  localStorage.clear();
  render(<Today />);
  fireEvent.click(screen.getByRole("button", { name: /Load today's workout/ }));
  fireEvent.click(
    (await screen.findAllByRole("button", { name: /Cross Body/ }))[0],
  );
  fireEvent.click(screen.getByRole("button", { name: "Why?" }));
  expect(screen.getByLabelText("Equipment identity")).toHaveValue(
    "specific-cable",
  );
  expect(screen.getByLabelText("Benchmark load (lb)")).toHaveValue(100);
  expect(
    screen.getByRole("spinbutton", { name: "Working weight (lb)" }),
  ).toHaveValue(65);
  fireEvent.click(screen.getByRole("button", { name: "Close Starting load" }));
  fireEvent.click(screen.getByRole("button", { name: "Guide & setup" }));
  expect(
    screen.getByText("Initial estimate load guidance"),
  ).toBeInTheDocument();
});

test("pending actual set stays frozen when estimate refreshes; first set switches away from estimate", async () => {
  const submit = vi.fn(async () => {
    throw Error("reply lost");
  });
  const view = render(runner(guidance(), { submit }));
  fireEvent.change(screen.getByLabelText("Working weight (lb)"), {
    target: { value: "60" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save set 1" }));
  await screen.findByText("Save not confirmed. Retry the same set.");
  const next = guidance();
  next.initial_estimate!.recommended_weight = 40;
  view.rerender(runner(next, { submit }));
  expect(screen.getByLabelText("Working weight (lb)")).toHaveValue(60);
  fireEvent.click(screen.getByRole("button", { name: "Retry same set" }));
  await waitFor(() => expect(submit).toHaveBeenCalledTimes(2));
  expect(submit.mock.calls[1]).toEqual(submit.mock.calls[0]);
  next.remaining_sets = decision(20, "remaining_sets");
  view.rerender(runner(next, { submit, completed: 1 }));
  expect(
    screen.queryByText("Suggested starting weight — estimate"),
  ).not.toBeInTheDocument();
});

test("recent benchmark requires explicit RIR and confirmation and sends declared grid without calculation", async () => {
  const save = vi.fn<(command: unknown, isRetry?: boolean) => Promise<void>>(async () => {});
  render(runner(guidance(), { onSaveCalibration: save }));
  fillBenchmark();
  fireEvent.click(screen.getByRole("radio", { name: "I know a recent weight and repetitions." }));
  fireEvent.change(screen.getByLabelText("Benchmark load (lb)"), {
    target: { value: "40" },
  });
  fireEvent.change(screen.getByLabelText("Benchmark reps (1–10)"), {
    target: { value: "8" },
  });
  fireEvent.click(screen.getByLabelText(/I confirm this benchmark/));
  expect(
    screen.getByRole("button", { name: "Save benchmark and estimate" }),
  ).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Benchmark RIR (0–3)"), {
    target: { value: "2" },
  });
  fireEvent.change(screen.getByLabelText("Available load format"), {
    target: { value: "grid" },
  });
  for (const [label, value] of [
    ["Minimum available load", "5"],
    ["Available increment", "2.5"],
    ["Maximum available load", "100"],
  ])
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  fireEvent.click(screen.getByLabelText(/I confirm this benchmark/));
  fireEvent.click(
    screen.getByRole("button", { name: "Save benchmark and estimate" }),
  );
  await screen.findByText(/Benchmark saved/);
  expect(save.mock.calls[0][0]).toEqual(
    expect.objectContaining({
      calibration: expect.objectContaining({
        method: "recent_set",
        load: 40,
        reps: 8,
        rir: 2,
        attainable: { unit: "lb", min: 5, step: 2.5, max: 100 },
      }),
    }),
  );
});

test("server refusal explains manual fallback and never prefills a refused numeric value", () => {
  const g = guidance();
  g.initial_estimate!.status = "unavailable";
  g.initial_estimate!.explanation =
    "This source AMRAP target does not support an initial estimate.";
  render(runner(g));
  fireEvent.click(screen.getByRole("button", { name: "Set up" }));
  expect(screen.getByText(/This source AMRAP/)).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Close Starting load" }));
  expect(screen.getByLabelText("Working weight (lb)")).toHaveValue(null);
  fireEvent.change(screen.getByLabelText("Working weight (lb)"), {
    target: { value: "40" },
  });
  expect(screen.getByRole("button", { name: "Save set 1" })).toBeEnabled();
});

test("later occurrence restores benchmark details but requires fresh confirmation", () => {
  const g = guidance();
  g.calibration = {
    id: "saved",
    revision: 1,
    requires_confirmation: true,
    load_context: g.load_context,
    input: {
      method: "known_1rm",
      load: 100,
      unit: "lb",
      observed_date: "2026-10-20",
      confirmed: false,
      variant_id: "cross-body",
      setup_details: "same cable setup",
      attainable: { unit: "lb", values: [5, 65, 100] },
    },
  };
  render(
    runner(g, {
      scope: "synthetic-user/later-occurrence",
      onSaveCalibration: async () => {},
    }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Why?" }));
  expect(screen.getByLabelText("Benchmark load (lb)")).toHaveValue(100);
  expect(screen.getByLabelText(/I confirm this benchmark/)).not.toBeChecked();
  expect(
    screen.getByRole("button", { name: "Save benchmark and estimate" }),
  ).toBeDisabled();
  fireEvent.click(screen.getByLabelText(/I confirm this benchmark/));
  expect(
    screen.getByRole("button", { name: "Save benchmark and estimate" }),
  ).toBeEnabled();
});

test("external setup change requires confirmation again without retaining the old equipment identity", () => {
  const g = guidance();
  const save = async () => {};
  const view = render(runner(g, { onSaveCalibration: save }));
  fillBenchmark();
  expect(screen.getByLabelText(/I confirm this benchmark/)).toBeChecked();
  view.rerender(
    runner(g, {
      onSaveCalibration: save,
      context: { ...g.load_context, equipment_key: "different-cable" },
    }),
  );
  expect(screen.getByLabelText("Equipment identity")).toHaveValue(
    "different-cable",
  );
  expect(screen.getByLabelText(/I confirm this benchmark/)).not.toBeChecked();
});

test("ambiguous HTTP failure retains the same calibration command for retry", async () => {
  const { ApiError } = await import("@/lib/api");
  const requests: unknown[] = [];
  const save = async (payload: unknown) => {
    requests.push(structuredClone(payload));
    if (requests.length === 1)
      throw new ApiError("Upstream route unavailable", 404);
  };
  render(runner(guidance(), { onSaveCalibration: save }));
  fillBenchmark();
  fireEvent.click(
    screen.getByRole("button", { name: "Save benchmark and estimate" }),
  );
  await screen.findByRole("button", { name: "Retry exact benchmark" });
  fireEvent.click(
    screen.getByRole("button", { name: "Retry exact benchmark" }),
  );
  await waitFor(() => expect(requests).toHaveLength(2));
  expect(requests[1]).toEqual(requests[0]);
});

test("benchmark retry preserves a newer declared setup and rejects advice for the old context", async () => {
  const { default: Today } = await import("@/app/today/page");
  const g = guidance();
  const requests: unknown[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input, init) => {
      const url = String(input);
      if (url.includes("/plan/scheduling-context?"))
        return Response.json({
          timezone: "UTC",
          local_today: new Date().toISOString().slice(0, 10),
          week_start: "2026-10-19",
          selected_dates: [],
          placement_revision: 0,
          plan: null,
        });
      if (url.endsWith("/workout/today"))
        return Response.json({
          session_id: "template",
          workout_occurrence_id: "retry-context",
          title: "Synthetic calibration",
          date: new Date().toISOString().slice(0, 10),
          exercises: [
            {
              id: "cross-body",
              exercise_occurrence_id: "slot-a",
              name: "Cross Body",
              sets: 3,
              rep_range: [10, 12],
              recommended_working_weight: null,
              load_intelligence: g,
            },
          ],
        });
      if (url.includes("/progress"))
        return Response.json({
          completed_total: 0,
          planned_total: 3,
          percent_complete: 0,
          exercises: [
            {
              exercise_id: "cross-body",
              exercise_occurrence_id: "slot-a",
              completed_sets: 0,
              load_intelligence: g,
            },
          ],
        });
      if (url.includes("/soreness"))
        return Response.json([
          { entry_date: new Date().toISOString().slice(0, 10) },
        ]);
      if (url.endsWith("/initial-calibration")) {
        requests.push(JSON.parse(String(init?.body)));
        if (requests.length === 1) throw Error("reply lost");
        return Response.json(g);
      }
      return Response.json({});
    }),
  );
  render(<Today />);
  fireEvent.click(screen.getByRole("button", { name: /Load today's workout/ }));
  fireEvent.click(await screen.findByRole("button", { name: /Cross Body/ }));
  fireEvent.change(screen.getByLabelText("Working weight (lb)"), {
    target: { value: "60" },
  });
  fillBenchmark();
  fireEvent.click(
    screen.getByRole("button", { name: "Save benchmark and estimate" }),
  );
  await screen.findByText(/Benchmark save not confirmed/);
  fireEvent.click(screen.getByRole("button", { name: "Guide & setup" }));
  fireEvent.change(screen.getByLabelText("Equipment reference (optional)"), {
    target: { value: "new-cable" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Close Guide & setup" }));
  fireEvent.click(
    screen.getByRole("button", { name: "Retry exact benchmark" }),
  );
  await screen.findByText(/Benchmark saved/);
  expect(requests[1]).toEqual(requests[0]);
  expect(screen.getByLabelText("Working weight (lb)")).toHaveValue(60);
  fireEvent.click(screen.getByRole("button", { name: "Guide & setup" }));
  expect(screen.getByLabelText("Equipment reference (optional)")).toHaveValue(
    "new-cable",
  );
  expect(
    screen.queryByText("Suggested starting weight — estimate"),
  ).not.toBeInTheDocument();
});

test("long initial explanations stay in the Starting load sheet instead of the fixed suggestion slot", () => {
  const g = guidance();
  g.initial_estimate!.status = "unavailable";
  const explanation = "Declare total external, per-hand, or same-machine stack load basis. Identify the exact equipment setup for this benchmark. Enter a positive finite benchmark load. Declare the benchmark unit as lb or kg. Enter a valid observation date that is not in the future. Confirm the report still represents this exact variant, side, range of motion and setup. Describe the side, range of motion, grip, attachment and relevant settings.";
  g.initial_estimate!.explanation = explanation;
  const view = render(runner(g));
  const slot = view.container.querySelector(".atlas-suggestion")!;
  expect(slot).not.toHaveTextContent(explanation);
  expect(slot).toHaveTextContent("Add a benchmark or choose a load.");
  fireEvent.click(screen.getByRole("button", { name: "Set up" }));
  expect(screen.getByText(explanation)).toBeVisible();
});

test.each([["effective_history_takes_precedence", 0], ["current_working_sets_take_precedence", 1]] as const)("%s keeps the specific existing load explanation visible", (reason, completed) => {
  const g = guidance();
  g.initial_estimate!.status = "unavailable";
  g.initial_estimate!.reason_codes = [reason];
  g.initial_estimate!.explanation = "Existing work takes precedence over an estimate.";
  const explanation = "Recorded effort is missing from this exposure.";
  g.next_exposure.explanation = explanation;
  g.remaining_sets = { ...decision(null, "remaining_sets"), explanation };
  const view = render(runner(g, { completed }));
  expect(view.container.querySelector(".atlas-suggestion")).toHaveTextContent(explanation);
  fireEvent.click(screen.getByRole("button", { name: "Set up" }));
  expect(screen.getByRole("dialog", { name: "Starting load" })).toHaveTextContent(explanation);
  expect(screen.getByRole("dialog", { name: "Starting load" })).not.toHaveTextContent("Existing work takes precedence over an estimate.");
});

test("first-use choices are inline; manual logging needs no benchmark setup", async () => {
  const g = guidance();
  g.initial_estimate = null;
  const submit = vi.fn(async (..._args: any[]) => {});
  render(runner(g, { onSaveCalibration: vi.fn(), submit }));
  expect(screen.getByRole("radio", { name: "I know my 1-rep max." })).toBeVisible();
  expect(screen.getByRole("radio", { name: "I know a recent weight and repetitions." })).toBeVisible();
  expect(screen.getByRole("radio", { name: "I'll choose a comfortable starting weight myself." })).toBeChecked();
  expect(screen.queryByLabelText("Equipment identity")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Working weight (lb)"), { target: { value: "20" } });
  fireEvent.click(screen.getByRole("button", { name: "Save set 1" }));
  await waitFor(() => expect(submit).toHaveBeenCalledOnce());
  expect(submit.mock.calls[0][2]).toMatchObject({ weight: 20, display_unit: "lb" });
  expect(submit.mock.calls[0][2].canonicalWeight).toBeCloseTo(9.0718474, 10);
});

test("estimate setup is optional for actual logging and does not duplicate the composer", () => {
  render(runner(guidance(), { onSaveCalibration: vi.fn() }));
  fireEvent.click(screen.getByRole("radio", { name: "I know my 1-rep max." }));
  expect(screen.getByLabelText("Benchmark load (lb)")).toBeVisible();
  expect(screen.getByLabelText("Equipment identity")).not.toBeVisible();
  expect(screen.getByRole("button", { name: "Save benchmark and estimate" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Save set 1" })).toBeEnabled();
  fireEvent.click(screen.getByRole("button", { name: "Why?" }));
  expect(screen.getAllByLabelText("Benchmark load (lb)")).toHaveLength(1);
});

test("history-backed guidance does not offer first-use estimates", () => {
  const g = guidance();
  g.next_exposure = decision(40);
  g.initial_estimate!.status = "unavailable";
  g.initial_estimate!.reason_codes = ["effective_history_takes_precedence"];
  render(runner(g, { onSaveCalibration: vi.fn() }));
  expect(screen.queryByRole("radio", { name: "I know my 1-rep max." })).not.toBeInTheDocument();
  expect(screen.getByLabelText("Working weight (lb)")).toHaveValue(88.2);
});

test("saved benchmark retains original magnitude across preferred-unit presentation and reload", async () => {
  const { AuthoredCalibration } = await import("@/components/authored-calibration");
  const save = vi.fn(async (..._args: any[]) => {});
  const g = guidance();
  const props = { scope: "unit-user", exercise: { id: "cross-body", exercise_occurrence_id: "slot-a", name: "Cross Body", sets: 3, rep_range: [10, 12] } as any,
    context: g.load_context, disabled: false, onSave: save };
  const view = render(<AuthoredCalibration {...props} />);
  fireEvent.click(screen.getByRole("radio", { name: "I know my 1-rep max." }));
  fireEvent.change(screen.getByLabelText("Benchmark load (lb)"), { target: { value: "100" } });
  fireEvent.change(screen.getByLabelText("Observed date"), { target: { value: "2026-10-20" } });
  fireEvent.change(screen.getByLabelText("Setup details"), { target: { value: "same setup" } });
  fireEvent.change(screen.getByLabelText("Available loads (comma separated)"), { target: { value: "5,65,100" } });
  view.rerender(<AuthoredCalibration {...props} context={{ ...g.load_context, display_unit: "kg" }} />);
  expect(screen.getByLabelText("Benchmark load (kg)")).toHaveValue(45.359237);
  fireEvent.click(screen.getByLabelText(/I confirm this benchmark/));
  fireEvent.click(screen.getByRole("button", { name: "Save benchmark and estimate" }));
  await waitFor(() => expect(save).toHaveBeenCalledOnce());
  expect(save.mock.calls[0][0].calibration).toMatchObject({ load: 100, unit: "lb", attainable: { unit: "lb", values: [5,65,100] } });
  view.unmount();
  render(<AuthoredCalibration {...props} context={{ ...g.load_context, display_unit: "kg" }} />);
  expect(screen.getByLabelText("Benchmark load (kg)")).toHaveValue(45.359237);
});

test("pending benchmark survives a first actual set and history takes precedence on retry", async () => {
  const save = vi.fn(async (..._args: any[]) => { if (save.mock.calls.length === 1) throw Error("lost reply"); });
  const view = render(runner(guidance(), { onSaveCalibration: save }));
  fillBenchmark();
  fireEvent.click(screen.getByRole("button", { name: "Save benchmark and estimate" }));
  await screen.findByText(/Benchmark save not confirmed/);
  const g = guidance();
  g.initial_estimate!.status = "unavailable";
  g.initial_estimate!.reason_codes = ["current_working_sets_take_precedence"];
  view.rerender(runner(g, { onSaveCalibration: save, completed: 1 }));
  fireEvent.click(screen.getByRole("button", { name: "Retry exact benchmark" }));
  await waitFor(() => expect(save).toHaveBeenCalledTimes(2));
  expect(save.mock.calls[1][0]).toEqual(save.mock.calls[0][0]);
  await waitFor(() => expect(screen.getByRole("radio", { name: "I know my 1-rep max." })).toBeDisabled());
});

test("Customized choices disclose the unsupported calculation and preserve manual logging", async () => {
  const g = guidance(); g.initial_estimate = null;
  const exercise = { id: "custom", exercise_occurrence_id: "custom-slot", name: "Custom", sets: 3, rep_range: [8,12], load_semantics: "external_load",
    customized: { target_min: 1, target_max: 3, target_kind: "rir", rest_seconds: { low:90, high:120 } } };
  render(runner(g, { exercise }));
  fireEvent.click(screen.getByRole("radio", { name: "I know my 1-rep max." }));
  expect(screen.getByText(/Customized does not convert/)).toBeVisible();
  expect(screen.queryByLabelText(/Benchmark load/)).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Working weight (lb)"), { target: { value:"25" } });
  expect(screen.getByRole("button", { name:"Save set 1" })).toBeEnabled();
});

test("appending a converted attainable list preserves exact old loads through save, reload and retry", async () => {
  const { AuthoredCalibration } = await import("@/components/authored-calibration");
  const g = guidance();
  g.calibration = { id:"old",revision:1,requires_confirmation:true,load_context:g.load_context,
    input:{method:"known_1rm",load:100,unit:"kg",observed_date:"2026-10-20",confirmed:false,variant_id:"cross-body",setup_details:"unchanged cable",attainable:{unit:"kg",values:[5,10,15]}} };
  const save = vi.fn(async (..._args:any[]) => { if(save.mock.calls.length===1)throw Error("lost reply"); });
  const props = {scope:"exact-list-user",exercise:{id:"cross-body",exercise_occurrence_id:"slot-a",name:"Cross Body",sets:3,rep_range:[10,12]} as any,context:g.load_context,guidance:g,disabled:false,onSave:save};
  const view=render(<AuthoredCalibration {...props}/>);
  const loads=screen.getByLabelText("Available loads (comma separated)") as HTMLInputElement;
  fireEvent.change(loads,{target:{value:loads.value+", 44"}});
  fireEvent.change(loads,{target:{value:loads.value.split(",").reverse().join(",")}});
  fireEvent.change(loads,{target:{value:loads.value.split(",").reverse().join(",")}});
  fireEvent.click(screen.getByLabelText(/I confirm this benchmark/));
  fireEvent.click(screen.getByRole("button",{name:"Save benchmark and estimate"}));
  await screen.findByText(/Benchmark save not confirmed/);
  expect(save.mock.calls[0][0].calibration.attainable.values.slice(0,3)).toEqual([5,10,15]);
  expect(save.mock.calls[0][0].calibration.attainable.values[3]).toBeCloseTo(44*0.45359237,10);
  view.unmount();render(<AuthoredCalibration {...props} context={{...g.load_context,display_unit:"kg"}}/>);
  fireEvent.click(screen.getByRole("button",{name:"Retry exact benchmark"}));
  await waitFor(()=>expect(save).toHaveBeenCalledTimes(2));
  expect(save.mock.calls[1][0]).toEqual(save.mock.calls[0][0]);
});

test("first-use help stays mounted after a saved set so expanded content cannot clamp scroll", () => {
  const view=render(runner(guidance(),{onSaveCalibration:vi.fn()}));fillBenchmark();
  const g=guidance();g.initial_estimate!.status="unavailable";g.initial_estimate!.reason_codes=["current_working_sets_take_precedence"];
  view.rerender(runner(g,{onSaveCalibration:vi.fn(),completed:1}));
  expect(screen.getByLabelText("Benchmark load (lb)")).toBeDisabled();
  expect(screen.getByText("Equipment and available loads").closest("details")).toHaveAttribute("open");
  expect(screen.getByRole("button",{name:"Save benchmark and estimate"})).toBeDisabled();
});
