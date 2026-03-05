"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
import { API_BASE_URL } from "@/lib/env";

type ResetRequestResponse = {
  status: string;
  reset_token?: string | null;
};

export default function ResetPasswordPage() {
  const router = useRouter();
  const [email, setEmail] = useState("athlete@example.com");
  const [token, setToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [requestStatus, setRequestStatus] = useState("Idle");
  const [confirmStatus, setConfirmStatus] = useState("Idle");

  async function handleRequest(event: FormEvent) {
    event.preventDefault();
    setRequestStatus("Requesting...");

    try {
      const response = await fetch(`${API_BASE_URL}/auth/password-reset/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!response.ok) {
        const detail = await response.text();
        const message = detail ? `Request failed: ${detail}` : "Request failed";
        setRequestStatus(message);
        return;
      }

      const payload = (await response.json()) as ResetRequestResponse;
      if (payload.reset_token) {
        setToken(payload.reset_token);
      }
      setRequestStatus(payload.reset_token ? "Reset token generated (dev mode: token shown below)." : "Reset requested. Check your email inbox.");
    } catch {
      setRequestStatus("Network error");
    }
  }

  async function handleConfirm(event: FormEvent) {
    event.preventDefault();
    setConfirmStatus("Updating password...");

    try {
      const response = await fetch(`${API_BASE_URL}/auth/password-reset/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: newPassword }),
      });
      if (!response.ok) {
        const detail = await response.text();
        const message = detail ? `Password update failed: ${detail}` : "Password update failed";
        setConfirmStatus(message);
        return;
      }
      setConfirmStatus("Password updated. Redirecting to login...");
      setTimeout(() => router.push("/login"), 600);
    } catch {
      setConfirmStatus("Network error");
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="ui-title-page">Reset Password</h1>

      <form className="main-card main-card--module spacing-grid" onSubmit={handleRequest}>
        <p className="telemetry-kicker">Step 1 - Request Reset Token</p>
        <input
          className="ui-input"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Email"
        />
        <Button className="w-full" type="submit">
          <span className="inline-flex items-center gap-2">
            <UiIcon name="reset" className="ui-icon--action" />
            Request Reset
          </span>
        </Button>
        <p className="ui-meta">Status: {requestStatus}</p>
        <p className="ui-meta">If your environment has no SMTP configured, this screen will auto-fill the reset token for dev testing.</p>
      </form>

      <form className="main-card main-card--module spacing-grid" onSubmit={handleConfirm}>
        <p className="telemetry-kicker">Step 2 - Confirm New Password</p>
        <input
          className="ui-input"
          value={token}
          onChange={(event) => setToken(event.target.value)}
          placeholder="Reset token"
        />
        <input
          className="ui-input"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          placeholder="New password"
          type={showNewPassword ? "text" : "password"}
        />
        <button
          className="h-8 w-full rounded-md border border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] px-3 text-xs text-zinc-100 transition-colors hover:border-[var(--ui-edge-active)]"
          onClick={() => setShowNewPassword((prev) => !prev)}
          type="button"
        >
          <span className="inline-flex items-center gap-2">
            <UiIcon name="settings" className="ui-icon--action" />
            {showNewPassword ? "Hide Password" : "Show Password"}
          </span>
        </button>
        <Button className="w-full" type="submit">
          <span className="inline-flex items-center gap-2">
            <UiIcon name="save" className="ui-icon--action" />
            Confirm Reset
          </span>
        </Button>
        <p className="ui-meta">Status: {confirmStatus}</p>
      </form>
    </div>
  );
}
