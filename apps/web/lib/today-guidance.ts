export function resolveGuidanceText(rationale?: string | null, guidance?: string | null): string {
  const preferred = rationale?.trim();
  if (preferred) {
    return preferred;
  }
  return guidance?.trim() ?? "";
}
