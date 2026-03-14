import { expect, test } from "vitest";

import { resolveGuidanceText } from "@/lib/today-guidance";

test("resolveGuidanceText does not invent fallback coaching guidance", () => {
  expect(resolveGuidanceText("Authoritative guidance.", "within_target_reps_hold_or_microload")).toBe(
    "Authoritative guidance.",
  );
  expect(resolveGuidanceText(undefined, "within_target_reps_hold_or_microload")).toBe(
    "within_target_reps_hold_or_microload",
  );
  expect(resolveGuidanceText(undefined, undefined)).toBe("");
});
