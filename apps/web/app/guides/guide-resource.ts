"use client";

import { useEffect, useState } from "react";
import { ApiError, getToken } from "@/lib/api";

export type GuideResource<T> = { status: "loading" | "error" | "not-found" | "unauthorized"; value?: never } | { status: "ready"; value: T };
type Snapshot<T> = { key: string | null; token: string | null | undefined; resource: GuideResource<T> };

// Guides are public reads. Account changes still retire the previous request,
// including replies arriving before a storage/focus notification is delivered.
export function useGuideResource<T>(key: string | null, load: () => Promise<T>) {
  const [token, setToken] = useState<string | null | undefined>(undefined);
  const [attempt, setAttempt] = useState(0);
  const [snapshot, setSnapshot] = useState<Snapshot<T>>({ key: null, token: undefined, resource: { status: "loading" } });

  useEffect(() => {
    const sync = () => setToken(getToken());
    sync();
    window.addEventListener("hypertrophy:auth-token-changed", sync);
    window.addEventListener("storage", sync);
    window.addEventListener("focus", sync);
    return () => {
      window.removeEventListener("hypertrophy:auth-token-changed", sync);
      window.removeEventListener("storage", sync);
      window.removeEventListener("focus", sync);
    };
  }, []);

  useEffect(() => {
    if (key === null || token === undefined) return;
    let retired = false;
    const current = () => {
      if (retired) return false;
      const actualToken = getToken();
      if (actualToken !== token) { setToken(actualToken); return false; }
      return true;
    };
    if (!current()) return;
    setSnapshot({ key, token, resource: { status: "loading" } });
    void load().then((value) => {
      if (current()) setSnapshot({ key, token, resource: { status: "ready", value } });
    }).catch((error: unknown) => {
      if (!current()) return;
      const status = error instanceof ApiError && error.status === 404 ? "not-found"
        : error instanceof ApiError && (error.status === 401 || error.status === 403) ? "unauthorized" : "error";
      setSnapshot({ key, token, resource: { status } });
    });
    return () => { retired = true; };
  }, [key, token, attempt, load]);

  const resource: GuideResource<T> = key === null ? { status: "not-found" }
    : snapshot.key === key && snapshot.token === token ? snapshot.resource : { status: "loading" };
  const retry = () => {
    const actualToken = getToken();
    if (actualToken !== token) { setToken(actualToken); return; }
    if (resource.status !== "loading") setAttempt((value) => value + 1);
  };
  return { resource, retry };
}
