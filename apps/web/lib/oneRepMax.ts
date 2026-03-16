/**
 * 1RM estimation and derived warm-up / working weights for the exercise detail UI.
 * Epley formula: 1RM ≈ weight × (1 + reps/30). Used to drive baseline block and next-set suggestions.
 */

const INCREMENT_LB = 2.5;
const MIN_WEIGHT_LB = 5;

/** Estimate 1RM (lb) from a set: weight (lb) × reps. Epley formula. */
export function epleyEstimate1RMLbs(weightLb: number, reps: number): number {
  if (reps < 1 || weightLb <= 0) return 0;
  if (reps === 1) return weightLb;
  return weightLb * (1 + reps / 30);
}

/** Round to nearest increment (e.g. 2.5 lb). */
function roundToIncrement(lb: number, increment: number = INCREMENT_LB): number {
  if (increment <= 0) return lb;
  return Math.round(lb / increment) * increment;
}

/** Warm-up weights (lb) from working weight, same logic as backend: 45%, 65%, 82%, 90% of working weight. */
export function warmupsFromWorkingWeightLb(
  workingWeightLb: number,
  warmupCount: number,
): number[] {
  if (warmupCount <= 0 || workingWeightLb <= 0) return [];
  const pcts = [0.45, 0.65, 0.82, 0.9];
  const selected = pcts.slice(0, warmupCount);
  const out: number[] = [];
  for (const pct of selected) {
    const raw = Math.max(MIN_WEIGHT_LB, workingWeightLb * pct);
    out.push(Math.max(MIN_WEIGHT_LB, roundToIncrement(raw)));
  }
  return [...new Set(out)].sort((a, b) => a - b);
}

/** Suggested working weight (lb) from 1RM for hypertrophy rep range (e.g. 8–12): ~70% 1RM. */
export function workingWeightFrom1RMLb(oneRepMaxLb: number): number {
  if (oneRepMaxLb <= 0) return 0;
  return roundToIncrement(oneRepMaxLb * 0.7);
}
