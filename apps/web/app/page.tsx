import Link from "next/link";

import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";

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
            <span className="inline-flex items-center gap-2">
              <UiIcon name="login" className="ui-icon--action" />
              Login
            </span>
          </Button>
        </Link>
        <Link href="/reset-password" className="block">
          <Button className="w-full" variant="secondary">
            <span className="inline-flex items-center gap-2">
              <UiIcon name="reset" className="ui-icon--action" />
              Reset Password
            </span>
          </Button>
        </Link>
        <Link href="/onboarding" className="block">
          <Button className="w-full">
            <span className="inline-flex items-center gap-2">
              <UiIcon name="onboarding" className="ui-icon--action" />
              Start Onboarding
            </span>
          </Button>
        </Link>
        <Link href="/today" className="block">
          <Button className="w-full" variant="secondary">
            <span className="inline-flex items-center gap-2">
              <UiIcon name="workout" className="ui-icon--action" />
              Go To Today
            </span>
          </Button>
        </Link>
      </div>
    </div>
  );
}
