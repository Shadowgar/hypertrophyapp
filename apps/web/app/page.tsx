import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Rocco&apos;s HyperTrophy Plan</h1>
      <p className="text-sm text-zinc-300">
        Deterministic hypertrophy planner + workout runner. Start with onboarding, then generate your week.
      </p>

      <div className="main-card glass-layer--accent space-y-2">
        <p className="text-xs uppercase tracking-wide text-zinc-400">System Status</p>
        <div className="flex items-center justify-between">
          <p className="text-sm text-zinc-100">Recovery</p>
          <span className="inline-flex items-center gap-2 text-xs text-zinc-200">
            <span className="status-dot status-dot--green" /> Operational
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="main-card">
          <p className="text-xs uppercase tracking-wide text-zinc-400">This Week</p>
          <p className="text-sm text-zinc-200">Sessions 3 / 4</p>
          <p className="text-xs text-zinc-500">Volume: 19 sets</p>
        </div>
        <div className="main-card">
          <p className="text-xs uppercase tracking-wide text-zinc-400">Trend Snapshot</p>
          <p className="text-sm text-zinc-200">Bench ↑ 15 lbs</p>
          <p className="text-xs text-zinc-500">Last 8 weeks</p>
        </div>
      </div>

      <div className="main-card space-y-3">
        <Link href="/login" className="block">
          <Button className="w-full" variant="secondary">
            Login
          </Button>
        </Link>
        <Link href="/reset-password" className="block">
          <Button className="w-full" variant="secondary">
            Reset Password
          </Button>
        </Link>
        <Link href="/onboarding" className="block">
          <Button className="w-full">Start Onboarding</Button>
        </Link>
        <Link href="/today" className="block">
          <Button className="w-full" variant="secondary">
            Go To Today
          </Button>
        </Link>
      </div>
    </div>
  );
}
