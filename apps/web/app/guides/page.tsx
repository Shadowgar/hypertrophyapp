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
      <div className="grid gap-3">
        {programs.map((p) => (
          <Link key={p.id} href={`/programs/${p.id}`} className="main-card p-3">
            <h2 className="font-medium">{p.name}</h2>
            {p.description && <p className="text-sm text-zinc-400">{p.description}</p>}
          </Link>
        ))}
        {programs.length === 0 && <p className="text-sm text-zinc-400">No programs available.</p>}
      </div>
    </div>
  );
}
