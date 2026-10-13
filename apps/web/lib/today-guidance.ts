import { useCallback, useRef } from "react";
import type { LoadContext, LoadDecision, LoadIntelligence } from "@/lib/api";

/** Scope selection only: the core owns evidence qualification and load calculation. */
export function currentLoadDecision(guidance: LoadIntelligence | null | undefined, completed: number, total: number): LoadDecision | null {
  if (!guidance || completed >= total) return null;
  const decision = completed === 0 ? guidance.next_exposure : guidance.remaining_sets;
  return decision?.scope === (completed === 0 ? "next_exposure" : "remaining_sets") ? decision : null;
}

export function prefillLoadKg(decision: LoadDecision | null): number | undefined {
  const value = decision?.recommended_weight;
  return decision?.prefill_available && typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : undefined;
}

export function resolveGuidanceText(rationale?: string | null, guidance?: string | null): string {
  const preferred = rationale?.trim();
  if (preferred) {
    return preferred;
  }
  return guidance?.trim() ?? "";
}


function declaredLoadContextSignature(context: LoadContext): string {
  return JSON.stringify([context.unit, context.display_unit, context.basis,
    context.increment ?? null, context.increment_unit ?? "kg", context.equipment_key ?? null]);
}

/** Event-time transport guard: projection provenance does not alter the user's declared fields. */
export type LoadProjectionGeneration = { epoch: number; exercises: Record<string, number> };

export function useDeclaredLoadContextGuard() {
  const selectedKeys = useRef<Record<string, string>>({});
  const versions = useRef<Record<string, number>>({});
  const epoch = useRef(0);
  const advance = useCallback((key: string) => { versions.current[key] = (versions.current[key] ?? 0) + 1; }, []);
  const reset = useCallback(() => { selectedKeys.current = {}; versions.current = {}; epoch.current += 1; }, []);
  const select = useCallback((key: string, context: LoadContext) => {
    selectedKeys.current[key] = declaredLoadContextSignature(context); advance(key);
  }, [advance]);
  const forget = useCallback((key: string) => { delete selectedKeys.current[key]; advance(key); }, [advance]);
  const capture = useCallback((): LoadProjectionGeneration => ({ epoch: epoch.current, exercises: { ...versions.current } }), []);
  const isCurrent = useCallback((key: string, snapshot?: LoadProjectionGeneration) => !snapshot ||
    (snapshot.epoch === epoch.current && (snapshot.exercises[key] ?? 0) === (versions.current[key] ?? 0)), []);
  const matches = useCallback((key: string, guidance: LoadIntelligence | null | undefined) => {
    const selected = selectedKeys.current[key];
    return !selected || !guidance || selected === declaredLoadContextSignature(guidance.load_context);
  }, []);
  return { reset, select, forget, matches, capture, isCurrent, advance };
}
