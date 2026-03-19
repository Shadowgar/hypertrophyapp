/**
 * Parse exercise rest strings (e.g. "~2-3 min", "~1 min", "~30s") to seconds.
 * Mirrors importers/xlsx_to_program.py _parse_rest_seconds; used for default rest timer.
 */
export function parseRestToSeconds(rest: string | null | undefined): number | null {
  const raw = rest?.trim().toLowerCase();
  if (!raw) return null;
  if (/^\d{4,}(?:\.\d+)?$/.test(raw)) return null;

  const values = [...raw.matchAll(/\d+/g)].map((m) => parseInt(m[0], 10));
  if (values.length === 0) return null;

  if (raw.includes("min")) {
    if (values.length >= 2) {
      return Math.round(((values[0] + values[1]) / 2) * 60);
    }
    return values[0] * 60;
  }
  if (raw.includes("sec") || raw.endsWith("s")) {
    return values[0];
  }
  return null;
}
