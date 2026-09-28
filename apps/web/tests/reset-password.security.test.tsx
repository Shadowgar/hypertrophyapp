import React from "react";
import { fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import ResetPasswordPage from "@/app/reset-password/page";

const navigation = vi.hoisted(() => ({ push: vi.fn(), query: new URLSearchParams() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: navigation.push }), useSearchParams: () => navigation.query }));

beforeEach(() => {
  navigation.query = new URLSearchParams();
  vi.stubGlobal("fetch", vi.fn());
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test("request acknowledges generically and cannot autofill an HTTP credential", async () => {
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ status: "accepted", reset_token: "unsafe-response-credential" }), { status: 200 }));
  render(<ResetPasswordPage />);
  fireEvent.click(screen.getByRole("button", { name: "Request Reset" }));
  await waitFor(() => expect(screen.getByText(/If recovery is available for this account/)).toBeInTheDocument());
  expect(screen.getByPlaceholderText("Reset token")).toHaveValue("");
  expect(screen.queryByText(/dev testing|dev mode|auto-fill/i)).not.toBeInTheDocument();
});

test("mailbox link still supplies the token for password confirmation", async () => {
  navigation.query = new URLSearchParams({ email: "mailbox@example.com", token: "mailbox-issued-synthetic-token" });
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ status: "password_updated" }), { status: 200 }));
  render(<ResetPasswordPage />);
  expect(screen.getByPlaceholderText("Reset token")).toHaveValue("mailbox-issued-synthetic-token");
  fireEvent.change(screen.getByPlaceholderText("New password"), { target: { value: "Synthetic-password-2" } });
  fireEvent.click(screen.getByRole("button", { name: "Confirm Reset" }));
  await waitFor(() => expect(screen.getByText(/Password updated/)).toBeInTheDocument());
  const body = JSON.parse(vi.mocked(fetch).mock.calls[0][1]?.body as string);
  expect(body).toEqual({ token: "mailbox-issued-synthetic-token", new_password: "Synthetic-password-2" });
});
