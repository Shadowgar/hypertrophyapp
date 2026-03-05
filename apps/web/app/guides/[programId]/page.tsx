"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { api, type GuideProgramDetail } from "@/lib/api";

type ProgramPhase = {
  id: string;
  name: string;
  dayIndexes: number[];
};

function buildProgramPhases(program: GuideProgramDetail): ProgramPhase[] {
  const dayIndexes = program.days.map((day) => day.day_index).sort((a, b) => a - b);
  return [{ id: "main", name: "Main Phase", dayIndexes }];
}

export default function ProgramGuidePhaseIndexPage() {
  const params = useParams();
  const programId = params?.programId as string | undefined;
  const [program, setProgram] = useState<GuideProgramDetail | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!programId) {
      return;
    }

    let mounted = true;
    (async () => {
      setStatus("Loading...");
      try {
        const found = await api.getProgramGuide(programId);
        if (!mounted) {
          return;
        }
        setProgram(found);
        setStatus(null);
      } catch {
        if (!mounted) {
          return;
        }
        setProgram(null);
        setStatus("Program guide not found");
      }
    })();

    return () => {
      mounted = false;
    };
  }, [programId]);

  const phases = useMemo(() => {
    if (!program) {
      return [] as ProgramPhase[];
    }
    return buildProgramPhases(program);
  }, [program]);

  if (!programId) {
    return <div className="p-4">No program id provided.</div>;
  }

  return (
    <div className="space-y-4 p-4">
      <h1 className="ui-title-page">Program Guide</h1>
      {status ? <p className="text-sm text-zinc-400">{status}</p> : null}
      {program ? (
        <div className="main-card space-y-3">
          <h2 className="text-lg text-zinc-100">{program.name}</h2>
          {program.description ? <p className="text-sm text-zinc-400">{program.description}</p> : null}
          <p className="text-xs text-zinc-500">Split: {program.split} · Program ID: {program.id}</p>

          <div className="space-y-2">
            {phases.map((phase) => (
              <div key={phase.id} className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3">
                <p className="telemetry-kicker">Phase</p>
                <h3 className="font-medium text-zinc-100">{phase.name}</h3>
                <p className="text-xs text-zinc-400">Days in phase: {phase.dayIndexes.join(", ") || "None"}</p>
                <div className="mt-2 flex gap-2">
                  <Link
                    href={`/guides/${program.id}/phase/${phase.id}`}
                    className="rounded-md border border-zinc-700 px-2 py-1 text-xs text-zinc-200"
                  >
                    Open phase guide
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
