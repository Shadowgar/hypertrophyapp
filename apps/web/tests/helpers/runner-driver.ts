/** Journey driver for the retained Today orchestration tests.
 * Opens the approved disclosure before querying its controls. The existing
 * assertions still exercise actual Today callbacks, request identities and
 * server-response races; browser qualification separately verifies layout/focus.
 */
import { fireEvent, screen, within, waitFor } from "@testing-library/react";

function closeSheets() {
  for (const dialog of Array.from(document.querySelectorAll("dialog[open]"))) {
    const button = within(dialog as HTMLElement).queryByRole("button", {
      name: /^Close /,
    });
    if (button) fireEvent.click(button);
  }
}
function reveal(panel: "warmup" | "guide" | "effort" | "records") {
  const title = {
    warmup: "Warm-up",
    guide: "Guide & setup",
    effort: "Actual effort",
    records: "Recorded sets",
  }[panel];
  const open = screen
    .queryAllByRole("dialog")
    .find((d) => within(d).queryByRole("heading", { name: title }));
  if (open) return within(open);
  closeSheets();
  const name = {
    warmup: /^Warm-up ·/,
    guide: "Guide & setup",
    effort: /Effort:|Actual RPE \d|Actual RIR \d/,
    records: /^Recorded sets · \d/,
  }[panel];
  const button = screen.queryByRole("button", { name });
  if (button) fireEvent.click(button);
  const dialog = screen
    .queryAllByRole("dialog")
    .find((d) => within(d).queryByRole("heading", { name: title }));
  return dialog ? within(dialog) : screen;
}
function route(role: any, options: any = {}) {
  if (!screen.queryByRole("region", { name: "Workout execution" }))
    return { scope: screen, role, options };
  let name = options.name;
  const label = typeof name === "string" ? name : (name?.source ?? "");
  let scope: any = screen;
  if (role === "dialog")
    return {
      scope: screen,
      role: "region",
      options: { name: "Workout execution" },
    };
  if (label === "Undo last warm-up to resolve") scope = reveal("guide");
  else if (
    /Corrected|Correction reason|Save correction|Cancel correction|Edit (set|warm-up)|Undo (Last|last)/.test(
      label,
    )
  )
    scope = reveal("records");
  else if (/Warm-up \d|Log warm-up|Retry warm-up/.test(label))
    scope = reveal("warmup");
  else if (/Actual RPE|Actual RIR|Technique quality|Pain during/.test(label))
    scope = reveal("effort");
  else if (
    /Load basis|Equipment reference|Known increment|Increment unit|Preview load|override reason|Report |Source-approved|Confirm this alternative|Decline alternatives|Undo last warm-up to resolve/.test(
      label,
    )
  )
    scope = reveal("guide");
  else if (
    /Weight \(lb\)|^Reps$|Complete Set|All Sets Complete|Back to list|Reload|Resolve authored|positive increment/.test(
      label,
    )
  )
    closeSheets();
  if (name instanceof RegExp && label.includes("Complete") && role === "button")
    name = /^Save set \d|^Retry same set$/;
  if (name instanceof RegExp && label.includes("Undo Last Set"))
    name = "Undo last set";
  if (name instanceof RegExp && label.includes("Back to list"))
    name = "Review workout";
  const names: Record<string, any> = {
    "Weight (lb)": "Working weight (lb)",
    Reps: "Working repetitions",
    "Complete Set": /^Save set \d|^Retry same set$/,
    "All Sets Complete": "Working sets complete",
    "Back to list": "Review workout",
    "Undo Last Set": "Undo last set",
    "Undo Last Warm-up": "Undo last warm-up",
    "Resolve authored slot first": /^Save set \d/,
    "Enter a positive increment or leave it blank": /^Save set \d/,
  };
  if (typeof name === "string" && names[name]) name = names[name];
  if (typeof name === "string" && name.startsWith("Log warm-up "))
    name = new RegExp(`^(Log|Retry) warm-up ${name.split(" ").at(-1)}$`);
  if (
    scope === screen &&
    role === "button" &&
    screen.queryAllByRole(role, { ...options, name }).length > 1
  ) {
    const nav = screen.queryByRole("navigation", { name: "Workout exercises" });
    if (nav && within(nav).queryByRole(role, { ...options, name }))
      scope = within(nav);
  }
  return { scope, role, options: { ...options, name } };
}
export const runnerScreen = {
  ...screen,
  getByRole: (role: any, options?: any) => {
    const q = route(role, options);
    return q.scope.getByRole(q.role, q.options);
  },
  findByRole: (role: any, options?: any, wait?: any) =>
    waitFor(() => {
      const q = route(role, options);
      return q.scope.getByRole(q.role, q.options);
    }, wait),
  getByLabelText: (label: any, options?: any) => {
    if (label === "Weight (lb)" || label === "Reps")
      return runnerScreen.getByRole("spinbutton", { name: label });
    if (typeof label === "string" && /Source-approved/.test(label))
      reveal("guide");
    return screen.getByLabelText(label, options);
  },
  queryByRole: (role: any, options?: any) => {
    const q = route(role, options);
    return q.scope.queryByRole(q.role, q.options);
  },
};
