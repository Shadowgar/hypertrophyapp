"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api, type Profile } from "@/lib/api";

export default function SettingsPage() {
  const [theme] = useState("dark");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [programs, setPrograms] = useState<Array<{id: string; name: string; description?: string}>>([]);
  const [selectedProgramId, setSelectedProgramId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.getProfile()
      .then((data) => {
        if (!mounted) return;
        setProfile(data);
        setSelectedProgramId(data.selected_program_id ?? null);
      })
      .catch(() => setProfile(null));

    api.listPrograms()
      .then((list) => {
        if (!mounted) return;
        setPrograms(list);
      })
      .catch(() => {});

    return () => { mounted = false };
  }, []);

  async function saveProgram() {
    if (!profile) return;
    setStatus("Saving...");
    try {
      const updated = await api.updateProfile({ selected_program_id: selectedProgramId });
      setProfile(updated);
      setStatus("Saved");
    } catch {
      setStatus("Save failed");
    }
    setTimeout(() => setStatus(null), 2000);
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Settings</h1>
      <div className="main-card space-y-3">
        <p className="text-sm text-zinc-300">Theme is locked to dark for MVP.</p>
        <Button variant="secondary" className="w-full" disabled>
          Theme: {theme}
        </Button>

        <div className="rounded-md border border-zinc-800 p-3 text-xs text-zinc-300">
          <p>Training Location: {profile?.training_location ?? "not set"}</p>
          <p>Equipment: {(profile?.equipment_profile ?? []).join(", ") || "not set"}</p>
        </div>

        <div className="space-y-2">
          <label htmlFor="settings-program" className="text-xs text-zinc-400">Program</label>
          <select
            id="settings-program"
            className="w-full rounded-md bg-zinc-900 p-2 text-white"
            value={selectedProgramId ?? ""}
            onChange={(e) => setSelectedProgramId(e.target.value || null)}
            aria-label="Settings program selector"
            aria-describedby="settings-program-desc"
          >
            <option value="">Default — trainer&apos;s recommended program</option>
            {programs.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <p id="settings-program-desc" className="text-xs text-zinc-500">{selectedProgramId ? (programs.find((p) => p.id === selectedProgramId)?.description ?? "No description available.") : "Default uses trainer recommendation."}</p>
          <div className="flex gap-2">
            <Button aria-label="Save selected program" className="mt-2" onClick={saveProgram}>Save Program</Button>
            <p className="text-sm text-zinc-400 mt-3">{status ?? ""}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
