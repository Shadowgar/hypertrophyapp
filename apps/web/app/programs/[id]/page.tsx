"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, type GuideProgramDetail } from "@/lib/api";

export default function ProgramGuidePage() {
  const params = useParams();
  const id = params?.id as string | undefined;
  const [program, setProgram] = useState<GuideProgramDetail | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let mounted = true;
    (async () => {
      setStatus("Loading...");
      try {
        const found = await api.getProgramGuide(id);
        if (mounted) {
          setProgram(found);
          setStatus(null);
        }
      } catch {
        if (mounted) {
          setProgram(null);
          setStatus("Program not found");
        }
      }
    })();
    return () => { mounted = false };
  }, [id]);

  if (!id) return <div className="p-4">No program id provided.</div>;

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">Program Guide</h1>
      {status && <p className="text-sm text-zinc-400">{status}</p>}
      {program && (
        <div className="main-card space-y-3">
          <h2 className="text-lg">{program.name}</h2>
          {program.description && <p className="text-sm text-zinc-400">{program.description}</p>}
          <div className="space-y-2">
            {program.days.map((day) => (
              <div key={day.day_index} className="border-t border-zinc-800 pt-2">
                <h3 className="font-medium">Day {day.day_index}: {day.day_name}</h3>
                <p className="text-xs text-zinc-400">{day.exercise_count} exercises</p>
                <div className="mt-2 flex gap-2">
                  <Link
                    href={`/guides/${program.id}/day/${day.day_index}`}
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
      )}
    </div>
  );
}
