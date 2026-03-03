"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type GuideProgram } from "@/lib/api";

export default function GuidesIndex() {
  const [programs, setPrograms] = useState<GuideProgram[]>([]);

  useEffect(() => {
    let mounted = true;
    api.listGuidePrograms()
      .then((list) => { if (mounted) setPrograms(list); })
      .catch(() => {});
    return () => { mounted = false };
  }, []);

  return (
    <div className="p-4 space-y-4">
      <h1 className="ui-title-page">Program Guides</h1>
      <div className="grid grid-cols-2 gap-3">
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Library</p>
          <p className="telemetry-value">{programs.length} program modules</p>
        </div>
        <div className="main-card main-card--module main-card--accent">
          <p className="telemetry-kicker">Sync</p>
          <p className="telemetry-status">
            <span className="status-dot status-dot--green" /> Online
          </p>
        </div>
      </div>
      <div className="grid gap-3">
        {programs.map((p) => (
          <Link key={p.id} href={`/programs/${p.id}`} className="main-card main-card--module p-3" aria-label={`Open guide for ${p.name}`}>
            <h2 className="font-medium">{p.name}</h2>
            {p.description && <p className="text-sm text-zinc-400">{p.description}</p>}
          </Link>
        ))}
        {programs.length === 0 && <p className="text-sm text-zinc-400">No programs available.</p>}
      </div>
    </div>
  );
}
