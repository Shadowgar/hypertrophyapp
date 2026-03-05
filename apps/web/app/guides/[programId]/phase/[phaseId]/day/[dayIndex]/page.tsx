"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { api, type GuideDayDetail } from "@/lib/api";

function resolvePhaseName(phaseId: string): string {
  return phaseId === "main" ? "Main Phase" : phaseId;
}

export default function ProgramPhaseDayGuidePage() {
  const params = useParams();
  const programId = params?.programId as string | undefined;
  const phaseId = params?.phaseId as string | undefined;
  const dayIndexParam = params?.dayIndex as string | undefined;
  const dayIndex = Number(dayIndexParam);

  const [dayGuide, setDayGuide] = useState<GuideDayDetail | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!programId || !phaseId || !Number.isFinite(dayIndex) || dayIndex < 1) {
      return;
    }

    let mounted = true;
    (async () => {
      setStatus("Loading...");
      try {
        const guide = await api.getProgramDayGuide(programId, dayIndex);
        if (!mounted) {
          return;
        }
        setDayGuide(guide);
        setStatus(null);
      } catch {
        if (!mounted) {
          return;
        }
        setDayGuide(null);
        setStatus("Day guide not found");
      }
    })();

    return () => {
      mounted = false;
    };
  }, [programId, phaseId, dayIndex]);

  if (!programId || !phaseId || !Number.isFinite(dayIndex) || dayIndex < 1) {
    return <div className="p-4">Missing params</div>;
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="ui-title-page">Day Guide</h1>
      {status ? <p className="text-sm text-zinc-400">{status}</p> : null}

      {dayGuide ? (
        <div className="main-card space-y-3">
          <div className="telemetry-header">
            <p className="telemetry-kicker">Phase</p>
            <p className="telemetry-status">
              <span className="status-dot status-dot--green" /> {resolvePhaseName(phaseId)}
            </p>
          </div>

          <h2 className="text-lg text-zinc-100">Day {dayGuide.day_index}: {dayGuide.day_name}</h2>

          <div className="space-y-2">
            {dayGuide.exercises.map((exercise) => (
              <div key={exercise.id} className="rounded-md border border-zinc-800 bg-zinc-900/40 p-2">
                <p className="font-medium text-zinc-100">{exercise.name}</p>
                {exercise.notes ? <p className="text-xs text-zinc-400">{exercise.notes}</p> : null}
                <div className="mt-2 flex gap-2">
                  <Link
                    href={`/guides/${programId}/exercise/${exercise.primary_exercise_id ?? exercise.id}`}
                    className="rounded-md border border-zinc-700 px-2 py-1 text-xs text-zinc-200"
                  >
                    Open exercise guide
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
