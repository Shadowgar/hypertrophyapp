import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, test, expect, vi } from "vitest";
import {
  AppearanceProvider,
  useAppearance,
} from "@/components/appearance-provider";
import { setAuthToken, clearAuthToken } from "@/lib/api";
const token = (sub: string) => `a.${btoa(JSON.stringify({ sub }))}.c`;
function View() {
  const p = useAppearance();
  return (
    <p>
      {p.preferences.theme_family}/{p.preferences.appearance}/
      {p.preferences.weight_unit}
    </p>
  );
}
beforeEach(() => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  );
});
test("a late old-account response cannot change the next account or signed-out appearance", async () => {
  let oldResolve: (value: Response) => void = () => {};
  vi.stubGlobal(
    "fetch",
    vi.fn((_url, init) =>
      init.headers.get("Authorization").includes(token("first"))
        ? new Promise<Response>((resolve) => {
            oldResolve = resolve;
          })
        : Promise.resolve(
            Response.json({
              theme_family: "charcoal",
              appearance: "system",
              weight_unit: "kg",
              revision: 1,
            }),
          ),
    ),
  );
  setAuthToken(token("first"));
  render(
    <AppearanceProvider>
      <View />
    </AppearanceProvider>,
  );
  act(() => setAuthToken(token("second")));
  await screen.findByText("charcoal/system/kg");
  await act(async () =>
    oldResolve(
      Response.json({
        theme_family: "graphite",
        appearance: "light",
        weight_unit: "lb",
        revision: 4,
      }),
    ),
  );
  expect(screen.getByText("charcoal/system/kg")).toBeInTheDocument();
  expect(document.documentElement.dataset.appearance).toBe("light");
  act(() => clearAuthToken());
  await screen.findByText("classic/dark/lb");
  await waitFor(() =>
    expect(document.documentElement.dataset.appearance).toBe("dark"),
  );
});

test("Settings persists only writable preference fields through the strict API boundary", async () => {
  const { AppearanceSettings } =
    await import("@/components/appearance-settings");
  const { fireEvent } = await import("@testing-library/react");
  const initial = {
    theme_family: "classic",
    appearance: "dark",
    weight_unit: "lb",
    revision: 0,
  };
  let submitted: unknown;
  vi.stubGlobal(
    "fetch",
    vi.fn((_url, init) => {
      if (init.method === "PUT") {
        submitted = JSON.parse(init.body);
        const body = submitted as Record<string, unknown>;
        return Promise.resolve(
          "revision" in body
            ? Response.json(
                { detail: "Extra inputs are not permitted" },
                { status: 422 },
              )
            : Response.json({ ...initial, ...body, revision: 1 }),
        );
      }
      return Promise.resolve(Response.json(initial));
    }),
  );
  setAuthToken(token("theme-owner"));
  render(
    <AppearanceProvider>
      <AppearanceSettings />
    </AppearanceProvider>,
  );
  await waitFor(() =>
    expect(screen.getByLabelText("Theme family")).toBeEnabled(),
  );
  fireEvent.change(screen.getByLabelText("Theme family"), {
    target: { value: "graphite" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save appearance" }));
  await waitFor(() =>
    expect(submitted).toEqual({
      theme_family: "graphite",
      appearance: "dark",
      weight_unit: "lb",
      expected_revision: 0,
    }),
  );
  await screen.findByText("Appearance saved.");
});

test("unrelated cross-tab workout storage does not reload or discard appearance drafts", async () => {
  const { AppearanceSettings } =
    await import("@/components/appearance-settings");
  const { fireEvent } = await import("@testing-library/react");
  const fetcher = vi.fn(() =>
    Promise.resolve(
      Response.json({
        theme_family: "classic",
        appearance: "dark",
        weight_unit: "lb",
        revision: 0,
      }),
    ),
  );
  vi.stubGlobal("fetch", fetcher);
  setAuthToken(token("theme-storage"));
  render(
    <AppearanceProvider>
      <AppearanceSettings />
    </AppearanceProvider>,
  );
  await waitFor(() =>
    expect(screen.getByLabelText("Theme family")).toBeEnabled(),
  );
  fireEvent.change(screen.getByLabelText("Theme family"), {
    target: { value: "charcoal" },
  });
  await act(async () =>
    window.dispatchEvent(
      new StorageEvent("storage", {
        key: "hypertrophy_occurrence_v3:rest",
        newValue: "123",
      }),
    ),
  );
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText("Theme family")).toHaveValue("charcoal");
});
