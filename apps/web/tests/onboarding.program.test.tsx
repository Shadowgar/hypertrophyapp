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

async function completeQuestionnaireToAccountStep() {
  fireEvent.click(screen.getByRole("button", { name: /next slide/i }));
  fireEvent.click(screen.getByRole("button", { name: /next slide/i }));
  fireEvent.click(screen.getByRole("button", { name: /get started/i }));

  fireEvent.click(screen.getByRole("button", { name: /^male$/i }));
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  fireEvent.click(screen.getByRole("button", { name: /build muscle/i }));
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  fireEvent.click(screen.getByRole("button", { name: /^next$/i })); // height
  fireEvent.click(screen.getByRole("button", { name: /^next$/i })); // weight

  fireEvent.change(screen.getByLabelText(/birthday/i), { target: { value: "1990-01-01" } });
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  fireEvent.click(screen.getByRole("button", { name: /getting started/i }));
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  for (let index = 0; index < 8; index += 1) {
    fireEvent.click(screen.getByRole("button", { name: /skip/i }));
  }

  await waitFor(() => {
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
  });
  fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: "Rocco" } });
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));
}

test("Onboarding wizard reaches account step with program catalog and password toggle", async () => {
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

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /next slide/i })).toBeInTheDocument();
  });

  await completeQuestionnaireToAccountStep();

  await waitFor(() => {
    expect(screen.getByLabelText(/program/i)).toBeInTheDocument();
  });

  expect(screen.getByText("Full Body V1")).toBeInTheDocument();

  const password = screen.getByLabelText(/Password/i);
  expect(password).toHaveAttribute("type", "password");
  fireEvent.click(screen.getByRole("button", { name: /show password/i }));
  expect(password).toHaveAttribute("type", "text");
});
