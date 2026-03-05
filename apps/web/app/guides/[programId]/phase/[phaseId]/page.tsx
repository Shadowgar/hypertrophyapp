"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { api, type GuideProgramDetail } from "@/lib/api";

function resolvePhaseName(phaseId: string): string {
  return phaseId === "main" ? "Main Phase" : phaseId;
}

export default function ProgramPhaseGuidePage() {
  const params = useParams();
  const programId = params?.programId as string | undefined;
  const phaseId = params?.phaseId as string | undefined;

  const [program, setProgram] = useState<GuideProgramDetail | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!programId || !phaseId) {
      return;
    }

    let mounted = true;
    (async () => {
      setStatus("Loading...");
      try {
        const guide = await api.getProgramGuide(programId);
        if (!mounted) {
          return;
        }
        setProgram(guide);
        setStatus(null);
      } catch {
        if (!mounted) {
          return;
        }
        setProgram(null);
        setStatus("Phase guide not found");
      }
    })();

    return () => {
      mounted = false;
    };
  }, [programId, phaseId]);

  if (!programId || !phaseId) {
    return <div className="p-4">Missing params</div>;
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="ui-title-page">Phase Guide</h1>
      {status ? <p className="text-sm text-zinc-400">{status}</p> : null}

      {program ? (
        <div className="main-card space-y-3">
          <div className="telemetry-header">
            <p className="telemetry-kicker">Program</p>
            <p className="telemetry-status">
              <span className="status-dot status-dot--green" /> {program.name}
            </p>
          </div>
          <p className="text-sm text-zinc-300">Phase: {resolvePhaseName(phaseId)}</p>

          <div className="space-y-2">
            {program.days.map((day) => (
              <div key={day.day_index} className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3">
                <p className="font-medium text-zinc-100">Day {day.day_index}: {day.day_name}</p>
                <p className="text-xs text-zinc-400">{day.exercise_count} exercises</p>
                <div className="mt-2 flex gap-2">
                  <Link
                    href={`/guides/${program.id}/phase/${phaseId}/day/${day.day_index}`}
                    className="rounded-md border border-zinc-700 px-2 py-1 text-xs text-zinc-200"
                  >
                    Open day guide
                  </Link>
                  {day.first_exercise_id ? (
                    <Link
                      href={`/guides/${program.id}/exercise/${day.first_exercise_id}`}
                      className="rounded-md border border-zinc-700 px-2 py-1 text-xs text-zinc-200"
                    >
                      Open first exercise
                    </Link>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
