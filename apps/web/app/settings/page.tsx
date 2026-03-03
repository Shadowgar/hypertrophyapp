"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api, type Profile, type ProgramRecommendation } from "@/lib/api";

export default function SettingsPage() {
  const [theme] = useState("dark");
  const [profile, setProfile] = useState<Profile | null>(null);
  const [programs, setPrograms] = useState<Array<{id: string; name: string; description?: string}>>([]);
  const [selectedProgramId, setSelectedProgramId] = useState<string | null>(null);
  const [recommendation, setRecommendation] = useState<ProgramRecommendation | null>(null);
  const [pendingSwitch, setPendingSwitch] = useState<{ targetProgramId: string; reason: string } | null>(null);
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

    api.getProgramRecommendation()
      .then((data) => {
        if (!mounted) return;
        setRecommendation(data);
      })
      .catch(() => {});

    return () => { mounted = false };
  }, []);

  async function saveProgram() {
    if (!profile) return;
    if (!selectedProgramId) {
      setStatus("Choose a program first");
      setTimeout(() => setStatus(null), 2000);
      return;
    }

    if (selectedProgramId === (profile.selected_program_id ?? null)) {
      setStatus("Already selected");
      setPendingSwitch(null);
      setTimeout(() => setStatus(null), 1500);
      return;
    }

    setStatus("Saving...");
    try {
      const response = await api.switchProgram({ target_program_id: selectedProgramId, confirm: false });
      if (response.requires_confirmation) {
        setPendingSwitch({ targetProgramId: selectedProgramId, reason: response.reason });
        setStatus("Confirm program switch");
      } else if (response.applied) {
        const updated = await api.getProfile();
        setProfile(updated);
        setPendingSwitch(null);
        setStatus("Saved");
      } else {
        setPendingSwitch(null);
        setStatus("No change");
      }
    } catch {
      setStatus("Save failed");
    }
    setTimeout(() => setStatus(null), 2000);
  }

  async function confirmProgramSwitch() {
    if (!pendingSwitch) return;
    setStatus("Applying switch...");
    try {
      const response = await api.switchProgram({
        target_program_id: pendingSwitch.targetProgramId,
        confirm: true,
      });
      if (response.applied) {
        const updated = await api.getProfile();
        setProfile(updated);
        const recommendationUpdated = await api.getProgramRecommendation();
        setRecommendation(recommendationUpdated);
        setStatus("Program switched");
      } else {
        setStatus("No change");
      }
      setPendingSwitch(null);
    } catch {
      setStatus("Switch failed");
    }
    setTimeout(() => setStatus(null), 2000);
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Settings</h1>
      <div className="grid grid-cols-2 gap-3">
        <div className="main-card main-card--shell">
          <p className="text-xs uppercase tracking-wide text-zinc-400">Profile Link</p>
          <p className="inline-flex items-center gap-2 text-sm text-zinc-200">
            <span className="status-dot status-dot--green" /> Connected
          </p>
        </div>
        <div className="main-card main-card--module main-card--accent">
          <p className="text-xs uppercase tracking-wide text-zinc-400">Config Scope</p>
          <p className="text-sm text-zinc-200">Program + recovery</p>
        </div>
      </div>
      <div className="main-card main-card--module spacing-grid">
        <div className="rounded-md border border-zinc-800 p-3 text-xs text-zinc-300">
          <p>Recommended Program: {recommendation?.recommended_program_id ?? "not available"}</p>
          <p>Reason: {recommendation?.reason ?? "not available"}</p>
        </div>

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
            className="ui-select"
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
            {pendingSwitch ? (
              <Button aria-label="Confirm program switch" className="mt-2" onClick={confirmProgramSwitch} variant="secondary">
                Confirm Switch
              </Button>
            ) : null}
            <p className="text-sm text-zinc-400 mt-3">{status ?? ""}</p>
          </div>
          {pendingSwitch ? (
            <p className="text-xs text-zinc-500">
              Switching to <span className="text-zinc-300">{pendingSwitch.targetProgramId}</span> requires confirmation ({pendingSwitch.reason}).
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}
