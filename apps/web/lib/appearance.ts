import type { InterfacePreferences } from "./api";
export const defaultPreferences: InterfacePreferences = {
  theme_family: "classic",
  appearance: "dark",
  weight_unit: "lb",
  revision: 0,
};
export const resolvedAppearance = (
  appearance: InterfacePreferences["appearance"],
  deviceDark: boolean,
) => (appearance === "system" ? (deviceDark ? "dark" : "light") : appearance);
export function safeReturnPath(path: string | null): string {
  return path &&
    path.startsWith("/") &&
    !path.startsWith("//") &&
    !/[\\\s\x00-\x1f]/.test(path)
    ? path
    : "/today";
}
/** Cache namespace only. Server authentication remains authoritative. */
export function accountScope(token: string | null): string | null {
  try {
    const sub = JSON.parse(
      atob(token!.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")),
    ).sub;
    return typeof sub === "string" && /^[\w@.+-]{1,200}$/.test(sub)
      ? sub
      : null;
  } catch {
    return null;
  }
}
export const displayLoad = (kg: number, unit: "kg" | "lb") =>
  unit === "lb" ? Number((kg / 0.45359237).toFixed(1)) : kg;
export const canonicalLoad = (value: number, unit: "kg" | "lb") =>
  unit === "lb" ? value * 0.45359237 : value;
