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

    expect(screen.getByText("Set 0/3")).toBeInTheDocument();
    expect(screen.getByText("00:05")).toBeInTheDocument();

    act(() => {
      fireEvent.click(screen.getByRole("button", { name: "Complete Set" }));
    });

    expect(screen.getByText("Set 1/3")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByText("00:04")).toBeInTheDocument();

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

    expect(screen.getByText("Set 1/1")).toBeInTheDocument();
    expect(completeButton).toBeDisabled();
  });
});
