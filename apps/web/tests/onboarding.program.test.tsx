import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import OnboardingPage from "@/app/onboarding/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

beforeEach(() => {
  // reset fetch mock
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("Onboarding loads program list and renders options", async () => {
  const programs = [
    { id: "full_body_v1", name: "Full Body V1", description: "A 5-day full body" },
    { id: "upper_lower", name: "Upper/Lower", description: "4 day" },
  ];

  // mock /plan/programs
  // @ts-ignore
  globalThis.fetch.mockImplementation((input, init) => {
    if (typeof input === "string" && input.endsWith("/plan/programs")) {
      return Promise.resolve(new Response(JSON.stringify(programs), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<OnboardingPage />);

  // wait for options to appear
  await waitFor(() => {
    expect(screen.getByLabelText(/Program/i)).toBeInTheDocument();
  });

  // options should include our program
  expect(screen.getByText("Full Body V1")).toBeInTheDocument();

  const password = screen.getByLabelText(/Password/i);
  expect(password).toHaveAttribute("type", "password");
  fireEvent.click(screen.getByRole("button", { name: /show password/i }));
  expect(password).toHaveAttribute("type", "text");

  const dumbbell = screen.getByRole("button", { name: /dumbbell/i });
  expect(dumbbell).toHaveAttribute("aria-pressed", "true");
  fireEvent.click(dumbbell);
  expect(dumbbell).toHaveAttribute("aria-pressed", "false");
});
