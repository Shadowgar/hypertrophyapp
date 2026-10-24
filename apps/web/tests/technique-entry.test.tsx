import React from "react";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { InlineTechniquePanel } from "@/components/technique-entry";
import {
  getLogCommand,
  pendingCommandKey,
  retainLogPayload,
} from "@/lib/workout-identity";
beforeEach(() => localStorage.clear());
for (const outcome of ["success", "failure"])
  test(`authoritative technique receipt wins over later ${outcome} without skipping ordinal`, async () => {
    const state = {
      exerciseId: "cross",
      exerciseName: "Synthetic exercise",
      workoutId: "occurrence",
      parentSetIndex: 1,
      kind: "dropset" as const,
      baseWeight: 40,
      baseReps: 12,
      unit: "lb" as const,
    };
    const scope = "technique-" + outcome;
    const key = pendingCommandKey(scope, "cross", "dropset:1:1");
    const command = getLogCommand(key);
    let finish: () => void = () => {};
    const onLog = vi.fn(() => {
      retainLogPayload(key, { command_id: command });
      return new Promise<void>((resolve, reject) => {
        finish = () =>
          outcome === "success"
            ? resolve()
            : reject(new Error("late reply failure"));
      });
    });
    const props = {
      state,
      scope,
      receipts: [] as any[],
      onLog,
      onClose: vi.fn(),
    };
    const mounted = render(<InlineTechniquePanel {...props} />);
    fireEvent.change(screen.getByRole("spinbutton", { name: "Reps" }), {
      target: { value: "6" },
    });
    fireEvent.change(
      screen.getByRole("spinbutton", { name: "Technique weight (lb)" }),
      { target: { value: "30" } },
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Log technique set #1" }),
    );
    mounted.rerender(
      <InlineTechniquePanel
        {...props}
        receipts={[
          {
            command_id: command,
            set_index: 1,
            parent_set_index: 1,
            technique: { ordinal: 1 },
          } as any,
        ]}
      />,
    );
    await screen.findByText(/Technique set confirmed/);
    await act(async () => finish());
    expect(
      screen.getByRole("button", { name: "Log technique set #2" }),
    ).toBeEnabled();
    expect(
      screen.getByRole("spinbutton", { name: "Reps" }),
    ).not.toHaveAttribute("readonly");
  });
