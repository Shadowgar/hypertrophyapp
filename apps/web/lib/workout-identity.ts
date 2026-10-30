import type { WorkoutExercise, WorkoutSession } from "@/lib/api";
import {getToken} from "@/lib/api";
import {accountScope} from "@/lib/appearance";

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
  return `hypertrophy_occurrence_v3:${accountScope(getToken())??"guest"}:${kind}:${identity}`;
}

export function pendingCommandKey(workout: string, exercise: string, slot: string): string {
  return `hypertrophy_occurrence_v2:command:${workout}:${exercise}:${slot}`;
}

const memoryCommands = new Map<string, string>();
const memoryPayloads = new Map<string, unknown>();

/** Enumerate exact account-owned Flexible attempts without needing an active runner. */
export function pendingFlexibleSets<T extends object>(scope: string): Array<{key:string;workoutId:string;payload:T}> {
  const prefix = `hypertrophy_occurrence_v2:command:hypertrophy_occurrence_v3:${scope}:attempt:`;
  const keys = new Set(memoryPayloads.keys());
  try {
    for (let index=0; index<localStorage.length; index++) {
      const key=localStorage.key(index);
      if(key?.endsWith(':payload')) keys.add(key.slice(0,-8));
    }
  } catch { /* Memory-retained commands are still available. */ }
  const pending:Array<{key:string;workoutId:string;payload:T}>=[];
  for (const key of keys) {
    if(!key.startsWith(prefix))continue;
    const workoutId=key.slice(prefix.length).split(':')[0];
    const payload=pendingLogPayload<Record<string,unknown>>(key);
    if(/^[\w-]+$/.test(workoutId) && payload && typeof payload.command_id==='string'
        && typeof payload.execution_context_id==='string' && typeof payload.exercise_id==='string'
        && typeof payload.set_index==='number' && typeof payload.reps==='number' && typeof payload.weight==='number') {
      pending.push({key,workoutId,payload:payload as T});
    }
  }
  return pending;
}

/** Pending writes remain blocking even when browser persistence could not be written. */
export function hasPendingWorkoutCommands(scope: string): boolean {
  const matches = (key: string) => key.startsWith("hypertrophy_occurrence_v2:command:")
    && key.includes(`hypertrophy_occurrence_v3:${scope}:`);
  if ([...memoryPayloads.keys()].some(matches)) return true;
  for (let index = 0; index < localStorage.length; index++) {
    const key = localStorage.key(index) ?? "";
    if (key.endsWith(":payload") && matches(key)) return true;
  }
  return false;
}

/** Read an attempted receipt without creating a new command. */
export function pendingLogPayload<T extends object>(key: string): T | null {
  let payload = memoryPayloads.get(key);
  try { const stored = localStorage.getItem(`${key}:payload`); if (stored) payload = JSON.parse(stored); } catch { /* memory fallback */ }
  return (payload as T | undefined) ?? null;
}

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
