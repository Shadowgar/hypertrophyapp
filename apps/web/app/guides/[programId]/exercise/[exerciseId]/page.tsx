"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

export default function ExerciseGuidePage() {
  const params = useParams();
  const programId = params?.programId as string | undefined;
  const exerciseId = params?.exerciseId as string | undefined;
  const [exercise, setExercise] = useState<any | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!programId || !exerciseId) return;
    let mounted = true;
    (async () => {
      setStatus("Loading...");
      try {
        const details = await api.getProgramExerciseGuide(programId, exerciseId);
        const found = details.exercise;
        if (mounted) {
          setExercise(found);
          setStatus(found ? null : "Exercise not found in program data");
        }
      } catch {
        if (mounted) setStatus("Exercise not found in program data");
      }
    })();
    return () => { mounted = false };
  }, [programId, exerciseId]);

  if (!programId || !exerciseId) return <div className="p-4">Missing params</div>;

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">Exercise Guide</h1>
      {status && <p className="text-sm text-zinc-400">{status}</p>}
      {exercise ? (
        <div className="main-card space-y-2">
          <h2 className="text-lg">{exercise.name ?? exercise.title}</h2>
          {exercise.description && <p className="text-sm text-zinc-400">{exercise.description}</p>}
          {exercise.instructions && <pre className="text-xs whitespace-pre-wrap">{exercise.instructions}</pre>}
          <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(exercise, null, 2)}</pre>
        </div>
      ) : (
        <div className="main-card text-sm text-zinc-400">No exercise details available.</div>
      )}
    </div>
  );
}
