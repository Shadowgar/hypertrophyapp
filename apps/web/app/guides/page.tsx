"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function GuidesIndex() {
  const [programs, setPrograms] = useState<Array<{id: string; name: string; description?: string}>>([]);

  useEffect(() => {
    let mounted = true;
    api.listPrograms()
      .then((list) => { if (mounted) setPrograms(list); })
      .catch(() => {});
    return () => { mounted = false };
  }, []);

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-xl font-semibold">Program Guides</h1>
      <div className="grid grid-cols-2 gap-3">
        <div className="main-card">
          <p className="text-xs uppercase tracking-wide text-zinc-400">Library</p>
          <p className="text-sm text-zinc-200">{programs.length} program modules</p>
        </div>
        <div className="main-card glass-layer--accent">
          <p className="text-xs uppercase tracking-wide text-zinc-400">Sync</p>
          <p className="inline-flex items-center gap-2 text-sm text-zinc-200">
            <span className="status-dot status-dot--green" /> Online
          </p>
        </div>
      </div>
      <div className="grid gap-3">
        {programs.map((p) => (
          <Link key={p.id} href={`/programs/${p.id}`} className="main-card p-3" aria-label={`Open guide for ${p.name}`}>
            <h2 className="font-medium">{p.name}</h2>
            {p.description && <p className="text-sm text-zinc-400">{p.description}</p>}
          </Link>
        ))}
        {programs.length === 0 && <p className="text-sm text-zinc-400">No programs available.</p>}
      </div>
    </div>
  );
}
