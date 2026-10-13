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
const memoryPayloads = new Map<string, unknown>();

/** Keep the complete attempted command immutable until acknowledged, including after remount. */
export function retainLogPayload<T extends object>(key: string, proposed: T): T {
  let payload = memoryPayloads.get(key);
  try { const stored = localStorage.getItem(`${key}:payload`); if (stored) payload = JSON.parse(stored); } catch { /* memory fallback */ }
  if (!payload) payload = { ...proposed };
  memoryPayloads.set(key, payload);
  try { localStorage.setItem(`${key}:payload`, JSON.stringify(payload)); } catch { /* memory fallback */ }
  return payload as T;
}

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
  memoryPayloads.delete(key);
  try { localStorage.removeItem(key); } catch { /* memory fallback */ }
  try { localStorage.removeItem(`${key}:payload`); } catch { /* memory fallback */ }
}
