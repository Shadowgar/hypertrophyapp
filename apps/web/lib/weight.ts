/**
 * American weight units: UI uses lbs; API uses kg.
 * Convert at the boundary when displaying or sending.
 */

const KG_TO_LBS = 2.20462262185;
const LBS_TO_KG = 0.45359237;

export function kgToLbs(kg: number): number {
  return Number((kg * KG_TO_LBS).toFixed(1));
}

export function lbsToKg(lbs: number): number {
  return Number((lbs * LBS_TO_KG).toFixed(1));
}

export function formatWeightLbs(lbs: number): string {
  return `${Number(lbs.toFixed(1))} lbs`;
}

/** Round to nearest 0.5 lb for display/recommendations to avoid kg→lb noise (e.g. 54.9 → 55). */
export function snapToHalfLb(lbs: number): number {
  return Math.round(lbs * 2) / 2;
}
