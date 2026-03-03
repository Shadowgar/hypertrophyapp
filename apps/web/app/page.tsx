import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="space-y-4">
      <h1 className="ui-title-hero">Rocco&apos;s HyperTrophy Plan</h1>
      <p className="ui-body-sm">
        Deterministic hypertrophy planner + workout runner. Start with onboarding, then generate your week.
      </p>

      <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">System Status</p>
        <div className="telemetry-header">
          <p className="telemetry-value">Recovery</p>
          <span className="telemetry-status">
            <span className="status-dot status-dot--green" /> Operational
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">This Week</p>
          <p className="telemetry-value">Sessions 3 / 4</p>
          <p className="telemetry-meta">Volume: 19 sets</p>
        </div>
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Trend Snapshot</p>
          <p className="telemetry-value">Bench ↑ 15 lbs</p>
          <p className="telemetry-meta">Last 8 weeks</p>
        </div>
      </div>

      <div className="main-card main-card--module spacing-grid">
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
