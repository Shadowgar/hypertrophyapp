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
});

test("Onboarding surfaces register validation errors", async () => {
  // @ts-ignore
  globalThis.fetch.mockImplementation((input, _init) => {
    const url = typeof input === "string" ? input : input.url;

    if (url.endsWith("/plan/programs")) {
      return Promise.resolve(new Response(JSON.stringify([{ id: "full_body_v1", name: "Full Body v1" }]), { status: 200 }));
    }

    if (url.endsWith("/auth/register")) {
      return Promise.resolve(new Response(JSON.stringify({ detail: "Password must be at least 8 characters" }), { status: 422 }));
    }

    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });

  render(<OnboardingPage />);

  await waitFor(() => {
    expect(screen.getByLabelText(/program/i)).toBeInTheDocument();
  });

  fireEvent.click(screen.getByRole("button", { name: /save onboarding/i }));

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
      return Promise.resolve(new Response(JSON.stringify([{ id: "full_body_v1", name: "Full Body v1" }]), { status: 200 }));
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
