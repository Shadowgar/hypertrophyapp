import React from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import ExerciseControlModule from "./exercise-control";

describe("ExerciseControlModule", () => {
  it("increments completed sets and auto-starts rest timer on Complete Set", () => {
    vi.useFakeTimers();

    render(
      <ExerciseControlModule
        exerciseId="ex-1"
        totalSets={3}
        defaultRestSeconds={5}
      />,
    );

    expect(screen.getAllByText("Set 1").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/00:05/).length).toBeGreaterThan(0);

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
    });

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getAllByText(/00:04/).length).toBeGreaterThan(0);

    vi.useRealTimers();
  });

  it("disables Complete Set after reaching total sets", () => {
    render(
      <ExerciseControlModule
        exerciseId="ex-2"
        totalSets={1}
        defaultRestSeconds={5}
      />,
    );

    const completeButton = screen.getByRole("button", { name: "Complete Set" });
    expect(completeButton).toBeEnabled();

    fireEvent.click(completeButton);

    const doneButton = screen.getByRole("button", { name: "All Sets Complete" });
    expect(doneButton).toBeDisabled();
  });
});
