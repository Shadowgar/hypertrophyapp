"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api, type WorkoutExercise, type WorkoutSession } from "@/lib/api";

type SwapState = Record<string, number>;
type NotesState = Record<string, boolean>;

export default function TodayPage() {
  const [health, setHealth] = useState("loading");
  const [workout, setWorkout] = useState<WorkoutSession | null>(null);
  const [message, setMessage] = useState("No workout loaded");
  const [swapIndexByExercise, setSwapIndexByExercise] = useState<SwapState>({});
  const [notesOpenByExercise, setNotesOpenByExercise] = useState<NotesState>({});

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
      setSwapIndexByExercise({});
      setNotesOpenByExercise({});
    } catch {
      setWorkout(null);
      setMessage("No workout available. Generate week plan first.");
    }
  }

  function toggleNotes(exerciseId: string) {
    setNotesOpenByExercise((prev) => ({ ...prev, [exerciseId]: !prev[exerciseId] }));
  }

  function swapExercise(exerciseId: string, optionCount: number) {
    if (optionCount < 1) {
      return;
    }
    setSwapIndexByExercise((prev) => {
      const current = prev[exerciseId] ?? 0;
      return { ...prev, [exerciseId]: (current + 1) % (optionCount + 1) };
    });
  }

  function resolveExerciseName(exercise: WorkoutExercise): string {
    const substitutions = exercise.substitution_candidates ?? [];
    const selectedIndex = swapIndexByExercise[exercise.id] ?? 0;
    if (selectedIndex === 0) {
      return exercise.name;
    }
    return substitutions[selectedIndex - 1] ?? exercise.name;
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Today</h1>
      <div className="main-card">
        <p className="text-sm text-zinc-300">API Health: {health}</p>
        <Button className="mt-3 w-full" onClick={loadToday}>
          Load Today Workout
        </Button>
      </div>

      {message ? <div className="main-card text-sm text-zinc-300">{message}</div> : null}

      {workout ? (
        <div className="space-y-3">
          <div className="main-card">
            <p className="text-sm text-zinc-300">{workout.title}</p>
            <p className="text-xs text-zinc-400">{workout.date}</p>
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

                <div className="flex gap-2">
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
                    onClick={() => swapExercise(exercise.id, substitutions.length)}
                    type="button"
                    variant="secondary"
                  >
                    Swap
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
    </div>
  );
}
