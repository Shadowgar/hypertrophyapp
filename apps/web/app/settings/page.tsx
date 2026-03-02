"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";

export default function SettingsPage() {
  const [theme] = useState("dark");

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Settings</h1>
      <div className="main-card space-y-3">
        <p className="text-sm text-zinc-300">Theme is locked to dark for MVP.</p>
        <Button variant="secondary" className="w-full" disabled>
          Theme: {theme}
        </Button>
      </div>
    </div>
  );
}
