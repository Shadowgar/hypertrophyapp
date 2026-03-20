import { beforeEach, expect, test, vi } from "vitest";

import { api } from "@/lib/api";

beforeEach(() => {
  localStorage.clear();
  // @ts-ignore
  globalThis.fetch = vi.fn();
});

test("API request clears stale token on 401", async () => {
  localStorage.setItem("hypertrophy_token", "stale-token");

  // @ts-ignore
  globalThis.fetch.mockResolvedValue(
    new Response("Invalid token", { status: 401 }),
  );

  await expect(api.getProfile()).rejects.toThrow(/Invalid token/i);
  expect(localStorage.getItem("hypertrophy_token")).toBeNull();
});
