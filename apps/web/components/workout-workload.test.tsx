import React from "react";
import { cleanup, render, screen } from "@testing-library/react";
import { WorkoutWorkload } from "./workout-workload";

afterEach(cleanup);

test("discloses full grouped workload against a time goal without claiming minutes of execution", () => {
  render(<WorkoutWorkload exercises={Array.from({ length: 14 }, () => ({ sets: 3 }))} timeBudgetMinutes={60} mode="authored" />);
  expect(screen.getByText("14 exercises · 42 planned working sets")).toBeInTheDocument();
  expect(screen.getByText(/Your session-time goal: 60 minutes/)).toBeInTheDocument();
  expect(screen.getByText(/Duration is unknown/)).toBeInTheDocument();
  expect(screen.getByText(/may exceed your available time/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Review 2–5 selected visits in Week/ })).toHaveAttribute("href", "/week");
  expect(screen.getByText(/all source exercises and working sets/)).toBeInTheDocument();
  expect(screen.getByText(/cannot split a started workout/)).toBeInTheDocument();
});

test("keeps an absent time goal unknown and counts each repeated slot", () => {
  render(<WorkoutWorkload exercises={[{ sets: 2 }, { sets: 4 }]} timeBudgetMinutes={null} />);
  expect(screen.getByText("2 exercises · 6 planned working sets")).toBeInTheDocument();
  expect(screen.getByText(/No session-time goal saved/)).toBeInTheDocument();
  expect(screen.queryByText(/Your session-time goal:/)).not.toBeInTheDocument();
});

test("does not imply authored source authority or source-preserving redistribution for Customized", () => {
  render(<WorkoutWorkload exercises={[{ sets: 3 }]} mode="customized" timeBudgetMinutes={30} />);
  expect(screen.getByText("1 exercise · 3 planned working sets")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /Review Customized planning/ })).toHaveAttribute("href", "/customize");
  expect(screen.queryByText(/all source exercises/)).not.toBeInTheDocument();
});


test("does not claim an unread profile has no saved time goal", () => {
  render(<WorkoutWorkload exercises={[{ sets: 3 }]} />);
  expect(screen.getByText(/Session-time goal unavailable/)).toBeInTheDocument();
  expect(screen.queryByText(/No session-time goal saved/)).not.toBeInTheDocument();
});


test("unknown program guidance does not invent Authored or Customized mode", () => {
  render(<WorkoutWorkload exercises={[{sets:3}]} />);
  expect(screen.getByRole("link", {name:"Review your saved plan in Week"})).toHaveAttribute("href", "/week");
  expect(screen.queryByRole("link", {name:/Review Customized/})).not.toBeInTheDocument();
  expect(screen.queryByText(/all source exercises/)).not.toBeInTheDocument();
});
