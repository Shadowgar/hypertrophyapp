"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

export default function ProgramGuidePage() {
  const params = useParams();
  const id = params?.id as string | undefined;
  const [program, setProgram] = useState<any | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let mounted = true;
    (async () => {
      setStatus("Loading...");
      try {
        const list = await api.listPrograms();
        const found = list.find((p: any) => p.id === id || p.slug === id);
        if (mounted) {
          setProgram(found ?? null);
          setStatus(found ? null : "Program not found");
        }
      } catch {
        if (mounted) setStatus("Failed to load programs");
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

          {program.days && Array.isArray(program.days) ? (
            <div className="space-y-2">
              {program.days.map((day: any, idx: number) => (
                <div key={idx} className="border-t border-zinc-800 pt-2">
                  <h3 className="font-medium">Day {idx + 1}: {day.title ?? day.name ?? "Session"}</h3>
                  {day.notes && <p className="text-xs text-zinc-400">{day.notes}</p>}
                  {day.blocks && Array.isArray(day.blocks) ? (
                    <ul className="list-disc list-inside text-sm">
                      {day.blocks.map((blk: any, i: number) => (
                        <li key={i}>{blk.name ?? blk.title ?? JSON.stringify(blk)}</li>
                      ))}
                    </ul>
                  ) : (
                    <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(day, null, 2)}</pre>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <pre className="text-sm whitespace-pre-wrap">{JSON.stringify(program, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );
}
