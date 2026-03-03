import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import OnboardingPage from "@/app/onboarding/page";

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
  global.fetch.mockImplementation((input, init) => {
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
});
