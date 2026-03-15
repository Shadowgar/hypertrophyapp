"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
import { API_BASE_URL } from "@/lib/env";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("athlete@example.com");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState("Idle");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setStatus("Logging in...");

    try {
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        const detail = await response.text();
        setStatus(detail ? `Login failed: ${detail}` : "Login failed");
        return;
      }

      const payload = (await response.json()) as { access_token: string };
      localStorage.setItem("hypertrophy_token", payload.access_token);
      const nextPath = searchParams.get("next") || "/today";
      setStatus("Logged in");
      router.push(nextPath);
    } catch {
      setStatus("Network error");
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="ui-title-page">Login</h1>
      <form className="main-card main-card--module spacing-grid" onSubmit={handleSubmit}>
        <input
          className="ui-input"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Email"
        />
        <input
          className="ui-input"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Password"
          type={showPassword ? "text" : "password"}
        />
        <button
          className="h-8 w-full rounded-md border border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] px-3 text-xs text-zinc-100 transition-colors hover:border-[var(--ui-edge-active)]"
          onClick={() => setShowPassword((prev) => !prev)}
          type="button"
        >
          <span className="inline-flex items-center gap-2">
            <UiIcon name="settings" className="ui-icon--action" />
            {showPassword ? "Hide Password" : "Show Password"}
          </span>
        </button>
        <Button className="w-full" type="submit">
          <span className="inline-flex items-center gap-2">
            <UiIcon name="login" className="ui-icon--action" />
            Login
          </span>
        </Button>
        <p className="ui-body-sm text-center">
          <Link
            href={email ? `/reset-password?email=${encodeURIComponent(email)}` : "/reset-password"}
            className="underline decoration-[var(--ui-edge-idle)] underline-offset-2 hover:decoration-[var(--ui-edge-active)]"
          >
            Forgot password?
          </Link>
        </p>
      </form>
      <p className="ui-body-sm">Status: {status}</p>
      {status.startsWith("Login failed") && (
        <p className="ui-body-sm">
          Wrong password?{" "}
          <Link
            href={email ? `/reset-password?email=${encodeURIComponent(email)}` : "/reset-password"}
            className="underline decoration-[var(--ui-edge-idle)] underline-offset-2 hover:decoration-[var(--ui-edge-active)]"
          >
            Request a password reset
          </Link>
        </p>
      )}
    </div>
  );
}
