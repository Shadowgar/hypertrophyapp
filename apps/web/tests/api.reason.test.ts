import { expect, test } from "vitest";

import { resolveReasonText } from "@/lib/api";

test("resolveReasonText does not humanize fallback reason codes", () => {
  expect(resolveReasonText(undefined, "continue_accumulation")).toBe("continue_accumulation");
  expect(resolveReasonText("Authoritative rationale.", "continue_accumulation")).toBe("Authoritative rationale.");
});
