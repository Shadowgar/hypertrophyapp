import type { WorkoutExercise, WorkoutSession } from "@/lib/api";

export function exerciseKey(exercise: WorkoutExercise): string {
  return exercise.exercise_occurrence_id ?? exercise.id;
}

export function workoutReference(workout: WorkoutSession): string {
  return workout.workout_occurrence_id ?? workout.session_id;
}

const unidentifiedViews = new WeakMap<WorkoutSession, string>();

export function occurrenceStorageKey(kind: string, workout: WorkoutSession): string {
  // v2 deliberately does not read legacy template-keyed caches.
  let identity = workout.workout_occurrence_id;
  if (!identity) {
    // An older API's ambiguous template ID never restores a persisted view.
    identity = unidentifiedViews.get(workout) ?? `unidentified-view-${crypto.randomUUID()}`;
    unidentifiedViews.set(workout, identity);
  }
  return `hypertrophy_occurrence_v2:${kind}:${identity}`;
}

export function pendingCommandKey(workout: string, exercise: string, slot: string): string {
  return `hypertrophy_occurrence_v2:command:${workout}:${exercise}:${slot}`;
}

const memoryCommands = new Map<string, string>();

export function getLogCommand(key: string): string {
  let command = memoryCommands.get(key);
  try { command = localStorage.getItem(key) ?? command; } catch { /* memory fallback */ }
  if (!command) command = crypto.randomUUID();
  memoryCommands.set(key, command);
  try { localStorage.setItem(key, command); } catch { /* memory fallback */ }
  return command;
}

export function acknowledgeLogCommand(key: string): void {
  memoryCommands.delete(key);
  try { localStorage.removeItem(key); } catch { /* memory fallback */ }
}
