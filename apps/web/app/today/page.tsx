"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import ExerciseControlModule from "@/components/exercise-control";
import { api, type SorenessSeverity, type WorkoutExercise, type WorkoutSession } from "@/lib/api";

type SwapState = Record<string, number>;
type NotesState = Record<string, boolean>;
const SWAP_STORAGE_PREFIX = "hypertrophy_swap_selection";
const MUSCLE_GROUPS = [
  "chest",
  "back",
  "quads",
  "hamstrings",
  "glutes",
  "shoulders",
  "biceps",
  "triceps",
  "calves",
] as const;

function createInitialSorenessState(): Record<string, SorenessSeverity> {
  return Object.fromEntries(MUSCLE_GROUPS.map((muscle) => [muscle, "none"])) as Record<string, SorenessSeverity>;
}

export default function TodayPage() {
  const [health, setHealth] = useState("loading");
  const [workout, setWorkout] = useState<WorkoutSession | null>(null);
  const [message, setMessage] = useState("No workout loaded");
  const [swapIndexByExercise, setSwapIndexByExercise] = useState<SwapState>({});
  const [notesOpenByExercise, setNotesOpenByExercise] = useState<NotesState>({});
  const [swapTargetExerciseId, setSwapTargetExerciseId] = useState<string | null>(null);
  const [showSorenessModal, setShowSorenessModal] = useState(false);
  const [sorenessStatus, setSorenessStatus] = useState("Idle");
  const [sorenessNotes, setSorenessNotes] = useState("");
  const [sorenessByMuscle, setSorenessByMuscle] = useState<Record<string, SorenessSeverity>>(createInitialSorenessState());

  useEffect(() => {
    api.health()
      .then((data) => setHealth(data.status))
      .catch(() => setHealth("offline"));
  }, []);

  async function loadToday() {
    try {
      const data = await api.getTodayWorkout();
      setWorkout(data);
      setMessage("");
      setNotesOpenByExercise({});

      const storageKey = `${SWAP_STORAGE_PREFIX}:${data.session_id}`;
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        try {
          const parsed = JSON.parse(saved) as SwapState;
          setSwapIndexByExercise(parsed);
        } catch {
          setSwapIndexByExercise({});
        }
      } else {
        setSwapIndexByExercise({});
      }
    } catch {
      setWorkout(null);
      setMessage("No workout available. Generate week plan first.");
    }
  }

  function resetSorenessForm() {
    setSorenessByMuscle(createInitialSorenessState());
    setSorenessNotes("");
    setSorenessStatus("Idle");
  }

  async function beginWorkoutLoad() {
    const today = new Date().toISOString().slice(0, 10);
    try {
      const entries = await api.listSoreness(today, today);
      if (entries.length > 0) {
        await loadToday();
        return;
      }
      resetSorenessForm();
      setShowSorenessModal(true);
    } catch {
      setMessage("Unable to verify soreness status. Try again.");
    }
  }

  async function submitSorenessAndLoad() {
    const today = new Date().toISOString().slice(0, 10);
    setSorenessStatus("Saving soreness...");
    try {
      await api.createSoreness({
        entry_date: today,
        severity_by_muscle: sorenessByMuscle,
        notes: sorenessNotes || undefined,
      });
      setShowSorenessModal(false);
      await loadToday();
    } catch {
      setSorenessStatus("Failed to save soreness");
    }
  }

  useEffect(() => {
    if (!workout) {
      return;
    }
    const storageKey = `${SWAP_STORAGE_PREFIX}:${workout.session_id}`;
    localStorage.setItem(storageKey, JSON.stringify(swapIndexByExercise));
  }, [swapIndexByExercise, workout]);

  function toggleNotes(exerciseId: string) {
    setNotesOpenByExercise((prev) => ({ ...prev, [exerciseId]: !prev[exerciseId] }));
  }

  function selectSwap(exerciseId: string, selectedIndex: number) {
    setSwapIndexByExercise((prev) => {
      return { ...prev, [exerciseId]: selectedIndex };
    });
    setSwapTargetExerciseId(null);
  }

  function resolveExerciseName(exercise: WorkoutExercise): string {
    const substitutions = exercise.substitution_candidates ?? [];
    const selectedIndex = swapIndexByExercise[exercise.id] ?? 0;
    if (selectedIndex === 0) {
      return exercise.name;
    }
    return substitutions[selectedIndex - 1] ?? exercise.name;
  }

  const swapTarget = workout?.exercises.find((exercise) => exercise.id === swapTargetExerciseId) ?? null;
  const swapTargetCurrentIndex = swapTarget ? (swapIndexByExercise[swapTarget.id] ?? 0) : 0;

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Today</h1>
      <div className="main-card">
        <p className="text-sm text-zinc-300">API Health: {health}</p>
        <Button className="mt-3 w-full" onClick={beginWorkoutLoad}>
          Load Today Workout
        </Button>
      </div>

      {message ? <div className="main-card text-sm text-zinc-300">{message}</div> : null}

      {workout ? (
        <div className="space-y-3">
          <div className="main-card">
            <p className="text-sm text-zinc-300">{workout.title}</p>
            <p className="text-xs text-zinc-400">{workout.date}</p>
            {workout.resume ? <p className="text-xs text-accent">Resumed unfinished workout</p> : null}
          </div>

          {workout.exercises.map((exercise) => {
            const notesOpen = notesOpenByExercise[exercise.id] ?? false;
            const hasVideo = Boolean(exercise.video?.youtube_url);
            const substitutions = exercise.substitution_candidates ?? [];
            const selectedName = resolveExerciseName(exercise);

            return (
              <div key={exercise.id} className="main-card space-y-3">
                <div>
                  <p className="text-sm font-semibold text-zinc-100">{selectedName}</p>
                  <p className="text-xs text-zinc-400">
                    {exercise.sets} sets · {exercise.rep_range[0]}-{exercise.rep_range[1]} reps · {exercise.recommended_working_weight} kg
                  </p>
                </div>

                <div className="glass-layer rounded-lg p-2 flex flex-wrap gap-2">
                  <Button
                    className="h-8 px-3 text-xs"
                    disabled={!hasVideo}
                    onClick={() => {
                      const url = exercise.video?.youtube_url;
                      if (url) {
                        window.open(url, "_blank", "noopener,noreferrer");
                      }
                    }}
                    type="button"
                    variant="secondary"
                  >
                    Video
                  </Button>
                  <Button
                    className="h-8 px-3 text-xs"
                    disabled={substitutions.length === 0}
                    onClick={() => setSwapTargetExerciseId(exercise.id)}
                    type="button"
                    variant="secondary"
                  >
                    I don’t have this equipment
                  </Button>
                  <Button
                    className="h-8 px-3 text-xs"
                    onClick={() => toggleNotes(exercise.id)}
                    type="button"
                    variant="secondary"
                  >
                    Notes
                  </Button>
                </div>

                <ExerciseControlModule
                  exerciseId={exercise.id}
                  note={exercise.notes}
                  totalSets={exercise.sets}
                  defaultRestSeconds={90}
                />

                {notesOpen ? (
                  <div className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2 text-xs text-zinc-300">
                    {exercise.notes ?? "No notes for this slot."}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}

      {swapTarget ? (
        <div className="fixed inset-0 z-50 flex items-end bg-black/60 p-4 md:items-center md:justify-center">
          <div className="main-card w-full max-w-md space-y-3">
            <div>
              <p className="text-sm font-semibold text-zinc-100">Choose a substitute</p>
              <p className="text-xs text-zinc-400">Slot: {swapTarget.name}</p>
            </div>

            <div className="space-y-2">
              <Button
                className="w-full justify-start"
                onClick={() => selectSwap(swapTarget.id, 0)}
                type="button"
                variant={swapTargetCurrentIndex === 0 ? "default" : "secondary"}
              >
                {swapTarget.name} (Original)
              </Button>

              {(swapTarget.substitution_candidates ?? []).map((candidate, index) => {
                const value = index + 1;
                return (
                  <Button
                    key={`${swapTarget.id}-${candidate}`}
                    className="w-full justify-start"
                    onClick={() => selectSwap(swapTarget.id, value)}
                    type="button"
                    variant={swapTargetCurrentIndex === value ? "default" : "secondary"}
                  >
                    {candidate}
                  </Button>
                );
              })}
            </div>

            <Button
              className="w-full"
              onClick={() => setSwapTargetExerciseId(null)}
              type="button"
              variant="ghost"
            >
              Close
            </Button>
          </div>
        </div>
      ) : null}

      {showSorenessModal ? (
        <div className="fixed inset-0 z-50 flex items-end bg-black/60 p-4 md:items-center md:justify-center">
          <div className="main-card w-full max-w-md space-y-3">
            <div>
              <p className="text-sm font-semibold text-zinc-100">What&rsquo;s sore today?</p>
              <p className="text-xs text-zinc-400">Log soreness before starting this workout.</p>
            </div>

            <div className="space-y-2">
              {MUSCLE_GROUPS.map((muscle) => (
                <div key={muscle} className="flex items-center justify-between gap-2">
                  <span className="text-xs uppercase tracking-wide text-zinc-300">{muscle}</span>
                  <select
                    className="rounded-md bg-zinc-900 p-1 text-xs text-white"
                    onChange={(event) => {
                      const value = event.target.value as SorenessSeverity;
                      setSorenessByMuscle((prev) => ({ ...prev, [muscle]: value }));
                    }}
                    value={sorenessByMuscle[muscle]}
                  >
                    <option value="none">None</option>
                    <option value="mild">Mild</option>
                    <option value="moderate">Moderate</option>
                    <option value="severe">Severe</option>
                  </select>
                </div>
              ))}
            </div>

            <textarea
              className="w-full rounded-md bg-zinc-900 p-2 text-xs text-white"
              onChange={(event) => setSorenessNotes(event.target.value)}
              placeholder="Optional soreness notes"
              rows={3}
              value={sorenessNotes}
            />

            <p className="text-xs text-zinc-400">{sorenessStatus}</p>

            <div className="flex gap-2">
              <Button className="w-full" onClick={submitSorenessAndLoad} type="button">
                Save & Start Workout
              </Button>
              <Button
                className="w-full"
                onClick={async () => {
                  setShowSorenessModal(false);
                  await loadToday();
                }}
                type="button"
                variant="secondary"
              >
                Skip
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
