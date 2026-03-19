import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

import OnboardingPage from "@/app/onboarding/page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

beforeEach(() => {
  // @ts-ignore
  globalThis.fetch = vi.fn();
  localStorage.clear();
});

async function completeQuestionnaireToAccountStep() {
  fireEvent.click(screen.getByRole("button", { name: /next slide/i }));
  fireEvent.click(screen.getByRole("button", { name: /next slide/i }));
  fireEvent.click(screen.getByRole("button", { name: /get started/i }));

  fireEvent.click(screen.getByRole("button", { name: /^male$/i }));
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  fireEvent.click(screen.getByRole("button", { name: /build muscle/i }));
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  fireEvent.change(screen.getByLabelText(/birthday/i), { target: { value: "1990-01-01" } });
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  fireEvent.click(screen.getByRole("button", { name: /getting started/i }));
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));

  // Skip all remaining skippable questionnaire questions until we reach the account step.
  // (The questionnaire sequence changes as we add/remove steps, so we avoid hardcoding a count.)
  let safety = 0;
  while (!screen.queryByLabelText(/first name/i) && safety < 25) {
    const skipButton = screen.queryByRole("button", { name: /skip/i });
    if (!skipButton) break;
    fireEvent.click(skipButton);
    safety += 1;
  }

  await waitFor(() => {
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
  });
  fireEvent.change(screen.getByLabelText(/first name/i), { target: { value: "Rocco" } });
  fireEvent.click(screen.getByRole("button", { name: /^next$/i }));
}

test("Onboarding surfaces register validation errors", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input, _init) => {
    const url = typeof input === "string" ? input : input.url;

    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(
        new Response(
          JSON.stringify([{ id: "pure_bodybuilding_phase_1_full_body", name: "Pure Bodybuilding - Phase 1 Full Body" }]),
          { status: 200 },
        ),
      );
    }

    if (url.endsWith("/auth/register")) {
      return Promise.resolve(new Response(JSON.stringify({ detail: "Password must be at least 8 characters" }), { status: 422 }));
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<OnboardingPage />);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /next slide/i })).toBeInTheDocument();
  });

  await completeQuestionnaireToAccountStep();

  fireEvent.click(screen.getByRole("button", { name: /continue/i }));

  await waitFor(() => {
    expect(screen.getAllByText(/registration failed: password must be at least 8 characters/i).length).toBeGreaterThan(0);
  });

  // @ts-ignore
  const calls = globalThis.fetch.mock.calls as Array<[RequestInfo | URL, RequestInit | undefined]>;
  const calledUrls = calls.map(([input]) => {
    if (typeof input === "string") {
      return input;
    }
    if (input instanceof URL) {
      return input.toString();
    }
    return input.url;
  });
  expect(calledUrls.some((url) => url.endsWith("/auth/login"))).toBe(false);
});


test("Onboarding developer wipe button calls dev wipe endpoint", async () => {
  const confirmSpy = vi.spyOn(globalThis, "confirm").mockReturnValue(true);

  // @ts-ignore
  globalThis.fetch.mockImplementation((input, _init) => {
    const url = typeof input === "string" ? input : input.url;

    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(
        new Response(
          JSON.stringify([{ id: "pure_bodybuilding_phase_1_full_body", name: "Pure Bodybuilding - Phase 1 Full Body" }]),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/auth/dev/wipe-user")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "wiped" }), { status: 200 }));
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<OnboardingPage />);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /wipe test user by email/i })).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /wipe test user by email/i }));

  await waitFor(() => {
    expect(screen.getAllByText(/test user wiped/i).length).toBeGreaterThan(0);
  });

  // @ts-ignore
  const calls = globalThis.fetch.mock.calls as Array<[RequestInfo | URL, RequestInit | undefined]>;
  const wipeCall = calls.find(([input]) => {
    let url: string;
    if (typeof input === "string") {
      url = input;
    } else if (input instanceof URL) {
      url = input.toString();
    } else {
      url = input.url;
    }
    return url.endsWith("/auth/dev/wipe-user");
  });
  expect(wipeCall).toBeDefined();

  confirmSpy.mockRestore();
});


test("Onboarding register request normalizes email casing and whitespace", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input, _init) => {
    const url = typeof input === "string" ? input : input.url;

    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(
        new Response(
          JSON.stringify([{ id: "pure_bodybuilding_phase_1_full_body", name: "Pure Bodybuilding - Phase 1 Full Body" }]),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/auth/register")) {
      return Promise.resolve(new Response(JSON.stringify({ access_token: "tok" }), { status: 200 }));
    }
    if (url.endsWith("/profile")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));
    }
    if (url.endsWith("/plan/generate-week")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "ok" }), { status: 200 }));
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<OnboardingPage />);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /next slide/i })).toBeInTheDocument();
  });

  await completeQuestionnaireToAccountStep();

  fireEvent.change(screen.getByLabelText(/email address/i), {
    target: { value: "  ATHLETE@Example.COM  " },
  });
  fireEvent.click(screen.getByRole("button", { name: /continue/i }));

  await waitFor(() => {
    // @ts-ignore
    const calls = globalThis.fetch.mock.calls as Array<[RequestInfo | URL, RequestInit | undefined]>;
    const registerCall = calls.find(([input]) => {
      let url: string;
      if (typeof input === "string") {
        url = input;
      } else if (input instanceof URL) {
        url = input.toString();
      } else {
        url = input.url;
      }
      return url.endsWith("/auth/register");
    });
    expect(registerCall).toBeDefined();
    const payloadBody = registerCall?.[1]?.body;
    const body = typeof payloadBody === "string" ? (JSON.parse(payloadBody) as { email?: string }) : {};
    expect(body.email).toBe("athlete@example.com");
  });
});


test("Onboarding password reset request button calls reset endpoint", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input, _init) => {
    const url = typeof input === "string" ? input : input.url;

    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(
        new Response(
          JSON.stringify([{ id: "pure_bodybuilding_phase_1_full_body", name: "Pure Bodybuilding - Phase 1 Full Body" }]),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/auth/password-reset/request")) {
      return Promise.resolve(new Response(JSON.stringify({ status: "accepted", reset_token: "abc123def456ghi7" }), { status: 200 }));
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<OnboardingPage />);

  await waitFor(() => {
    expect(screen.getByRole("button", { name: /request password reset token/i })).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /request password reset token/i }));

  await waitFor(() => {
    expect(screen.getAllByText(/password reset token issued:/i).length).toBeGreaterThan(0);
  });
});
