"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api, type Profile } from "@/lib/api";

export default function SettingsPage() {
  const [theme] = useState("dark");
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    api.getProfile()
      .then((data) => setProfile(data))
      .catch(() => setProfile(null));
  }, []);

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
      </div>
    </div>
  );
}
