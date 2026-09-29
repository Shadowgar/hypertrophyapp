import type { WorkoutExercise, GeneratedWeekExercise } from "@/lib/api";

type Exercise = Pick<WorkoutExercise | GeneratedWeekExercise, "rep_range" | "authored_prescription" | "reps">;

export function authoredRepLabel(exercise: Exercise, setIndex?: number): string {
  const prescription = exercise.authored_prescription;
  if (prescription) {
    if (setIndex !== undefined) {
      return prescription.sets[setIndex - 1]?.rep_target.raw ?? "Target unspecified";
    }
    return prescription.raw.reps ?? "Target unspecified";
  }
  return exercise.rep_range ? `${exercise.rep_range[0]}-${exercise.rep_range[1]}` : "Target unspecified";
}

export function authoredSetRepRange(exercise: Exercise, setIndex: number): [number, number] | null {
  if (!exercise.authored_prescription) return exercise.rep_range;
  const target = exercise.authored_prescription.sets[setIndex - 1]?.rep_target;
  return target?.kind === "reps" && target.min != null && target.max != null ? [target.min, target.max] : null;
}

export function authoredSetDetails(exercise: Exercise, setIndex: number): string {
  const set = exercise.authored_prescription?.sets[setIndex - 1];
  if (!set) return "";
  return [set.effort_target.raw && `${set.effort_target.kind.toUpperCase()} ${set.effort_target.raw}`,
    set.rest && `Rest ${set.rest}`, set.intensity_technique].filter(Boolean).join(" · ");
}

export function authoredWarmupLabel(exercise: WorkoutExercise): string | null {
  return exercise.authored_prescription?.raw.warm_up_sets ?? exercise.warm_up_sets ?? null;
}

export function isBodyweightAuthored(exercise: Pick<WorkoutExercise, "authored_prescription" | "load_semantics" | "performed_variant">): boolean {
  return Boolean(exercise.authored_prescription) && (exercise.performed_variant?.load_semantics ?? exercise.load_semantics) === "bodyweight";
}

export function authoredSetTechnique(exercise: WorkoutExercise, setIndex: number): string | null {
  const raw = exercise.authored_prescription?.sets[setIndex - 1]?.intensity_technique ?? null;
  return raw && !["n/a", "na", "none", "-", "–", "—"].includes(raw.trim().toLowerCase()) ? raw : null;
}
