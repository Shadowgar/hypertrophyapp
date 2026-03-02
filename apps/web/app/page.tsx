import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Rocco&apos;s HyperTrophy Plan</h1>
      <p className="text-sm text-zinc-300">
        Deterministic hypertrophy planner + workout runner. Start with onboarding, then generate your week.
      </p>
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
