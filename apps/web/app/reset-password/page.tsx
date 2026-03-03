"use client";

import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { API_BASE_URL } from "@/lib/env";

type ResetRequestResponse = {
  status: string;
  reset_token?: string | null;
};

export default function ResetPasswordPage() {
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
        setRequestStatus("Request failed");
        return;
      }

      const payload = (await response.json()) as ResetRequestResponse;
      if (payload.reset_token) {
        setToken(payload.reset_token);
      }
      setRequestStatus("Reset requested");
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
        setConfirmStatus("Password update failed");
        return;
      }
      setConfirmStatus("Password updated");
    } catch {
      setConfirmStatus("Network error");
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="ui-title-page">Reset Password</h1>

      <form className="main-card main-card--module spacing-grid" onSubmit={handleRequest}>
        <p className="ui-meta">Request reset token</p>
        <input
          className="ui-input"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="Email"
        />
        <Button className="w-full" type="submit">
          Request Reset
        </Button>
        <p className="ui-meta">Status: {requestStatus}</p>
      </form>

      <form className="main-card main-card--module spacing-grid" onSubmit={handleConfirm}>
        <p className="ui-meta">Confirm new password</p>
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
        <Button
          className="h-8 w-full text-xs"
          onClick={() => setShowNewPassword((prev) => !prev)}
          type="button"
          variant="secondary"
        >
          {showNewPassword ? "Hide Password" : "Show Password"}
        </Button>
        <Button className="w-full" type="submit">
          Confirm Reset
        </Button>
        <p className="ui-meta">Status: {confirmStatus}</p>
      </form>
    </div>
  );
}
