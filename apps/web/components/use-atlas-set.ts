"use client";
import { useEffect, useRef, useState } from "react";
import { ApiError, type EffectiveLoadSet } from "@/lib/api";
import { canonicalLoad, displayLoad } from "@/lib/appearance";
import {
  acknowledgeLogCommand,
  getLogCommand,
  pendingCommandKey,
  pendingLogPayload,
} from "@/lib/workout-identity";
import type { PerformedSet } from "./exercise-control";

type Draft = {
  canonical?: number;
  source?: "suggestion" | "manual";
  weight: string;
  reps: string;
  rpe: string;
  rir: string;
  unit: "kg" | "lb";
  quality: "acceptable" | "poor" | "unknown";
  pain: "unknown" | "yes" | "no";
  attempt?: { set: number; command: string; performed: PerformedSet };
};
type Props = {
  draftIdentity?: string;
  scope: string;
  exerciseId: string;
  completed: number;
  total: number;
  unit: "kg" | "lb";
  prefillKg?: number;
  repRange: [number, number] | null;
  receipts: EffectiveLoadSet[];
  bodyweight?: boolean;
  submit: (set: number, performed: PerformedSet) => Promise<void> | void;
};
export function useAtlasSet(p: Props) {
  const key = `${p.scope}:draft:${p.exerciseId}:${p.draftIdentity ?? "source"}`;
  const [storageAvailable, setStorageAvailable] = useState(true);
  const [draft, setDraft] = useState<Draft>(() => {
    let previous: Draft | null = null;
    try {
      previous = JSON.parse(localStorage.getItem(key) ?? "null");
    } catch {
      /* a new in-memory draft */
    }
    if (
      previous &&
      (previous.unit === "kg" || previous.unit === "lb") &&
      typeof previous.weight === "string"
    ) {
      if (
        previous.attempt &&
        p.receipts.some((r) => r.command_id === previous!.attempt!.command)
      )
        return {
          ...previous,
          reps: "",
          rpe: "",
          rir: "",
          quality: "unknown",
          pain: "unknown",
          attempt: undefined,
        };
      return previous;
    }
    return {
      canonical: p.prefillKg,
      source: "suggestion",
      weight:
        p.prefillKg === undefined
          ? ""
          : String(displayLoad(p.prefillKg, p.unit)),
      reps: p.repRange ? String(p.repRange[0]) : "",
      rpe: "",
      rir: "",
      unit: p.unit,
      quality: "unknown",
      pain: "unknown",
    };
  });
  const [phase, setPhase] = useState<
    "ready" | "pending" | "uncertain" | "saved" | "error" | "conflict"
  >(draft.attempt ? "uncertain" : "ready");
  const [message, setMessage] = useState(
    draft.attempt
      ? "Previous save is unconfirmed. Retry these exact values."
      : "Ready for your next set",
  );
  const [confirmed, setConfirmed] = useState(p.completed);
  const busy = useRef(false);
  const acknowledgedCommands = useRef(new Set<string>());
  const edited = useRef(draft.source !== "suggestion");
  const write = (value: Draft) => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      setStorageAvailable(true);
    } catch {
      setStorageAvailable(false);
    }
  };
  useEffect(() => {
    write(draft);
  }, [draft, key]);
  useEffect(() => {
    const confirmedAttempt =
      draft.attempt &&
      p.receipts.find((r) => r.command_id === draft.attempt!.command);
    if (confirmedAttempt) {
      acknowledgedCommands.current.add(confirmedAttempt.command_id!);
      const next: Draft = {
        ...draft,
        reps: "",
        rpe: "",
        rir: "",
        quality: "unknown",
        pain: "unknown",
        attempt: undefined,
      };
      setDraft(next);
      write(next);
      setConfirmed((c) => Math.max(c, confirmedAttempt.set_index));
      setPhase("saved");
      setMessage(`✓ Set ${confirmedAttempt.set_index} saved`);
    }
    for (const receipt of p.receipts) {
      if (
        !receipt.command_id ||
        receipt.set_kind === "warmup" ||
        receipt.parent_set_index != null
      )
        continue;
      const commandKey = pendingCommandKey(
        p.scope,
        p.exerciseId,
        `work:${receipt.set_index}`,
      );
      const retained = pendingLogPayload<{ command_id: string }>(commandKey);
      if (retained?.command_id === receipt.command_id)
        acknowledgeLogCommand(commandKey);
    }
  }, [p.receipts, p.scope, p.exerciseId, draft.attempt]);
  useEffect(() => {
    if (draft.attempt || draft.unit === p.unit) return;
    setDraft((d) => {
      if (d.attempt || d.unit === p.unit) return d;
      const canonical =
        d.canonical ??
        (d.weight !== "" ? canonicalLoad(Number(d.weight), d.unit) : undefined);
      return {
        ...d,
        unit: p.unit,
        canonical,
        weight:
          canonical === undefined ? "" : String(displayLoad(canonical, p.unit)),
      };
    });
  }, [p.unit, draft.attempt, draft.unit]);
  const previousCompleted = useRef(p.completed);
  useEffect(() => {
    if (p.completed < previousCompleted.current && !draft.attempt) {
      setPhase("ready");
      setMessage(`Ready for set ${p.completed + 1}`);
    }
    previousCompleted.current = p.completed;
    setConfirmed(p.completed);
  }, [p.completed]);
  useEffect(() => {
    if (!edited.current && !draft.attempt)
      setDraft((d) => ({
        ...d,
        canonical: p.prefillKg,
        weight:
          p.prefillKg === undefined
            ? ""
            : String(displayLoad(p.prefillKg, d.unit)),
      }));
  }, [p.prefillKg]);
  const validEffort = (v: string) =>
    v === "" ||
    (Number.isFinite(Number(v)) && Number(v) >= 0 && Number(v) <= 10);
  const valid =
    draft.reps !== "" &&
    Number.isInteger(Number(draft.reps)) &&
    Number(draft.reps) > 0 &&
    draft.weight !== "" &&
    Number.isFinite(Number(draft.weight)) &&
    (p.bodyweight ? Number(draft.weight) >= 0 : Number(draft.weight) > 0) &&
    validEffort(draft.rpe) &&
    validEffort(draft.rir) &&
    !(draft.rpe !== "" && draft.rir !== "");
  function edit<K extends keyof Omit<Draft, "attempt" | "unit">>(
    field: K,
    value: Draft[K],
  ) {
    if (busy.current || draft.attempt || phase === "conflict") return;
    if (field === "weight") edited.current = true;
    setDraft((d) => ({
      ...d,
      [field]: value,
      source: field === "weight" ? "manual" : d.source,
      canonical: field === "weight" ? undefined : d.canonical,
    }));
    if (phase === "error") {
      setPhase("ready");
      setMessage("Ready to save");
    }
  }
  async function save() {
    if (
      busy.current ||
      phase === "conflict" ||
      (!draft.attempt && (!valid || confirmed >= p.total))
    )
      return;
    busy.current = true;
    const set = draft.attempt?.set ?? confirmed + 1;
    const attempt = draft.attempt ?? {
      set,
      command: getLogCommand(
        pendingCommandKey(p.scope, p.exerciseId, `work:${set}`),
      ),
      performed: {
        reps: Number(draft.reps),
        weight: Number(draft.weight),
        canonicalWeight:
          draft.canonical !== undefined &&
          Number(draft.weight) === displayLoad(draft.canonical, draft.unit)
            ? draft.canonical
            : p.prefillKg !== undefined &&
                Number(draft.weight) === displayLoad(p.prefillKg, draft.unit)
              ? p.prefillKg
              : canonicalLoad(Number(draft.weight), draft.unit),
        display_unit: draft.unit,
        rpe: draft.rpe === "" ? null : Number(draft.rpe),
        actual_rir: draft.rir === "" ? null : Number(draft.rir),
        technique_quality: draft.quality,
        pain: draft.pain === "unknown" ? null : draft.pain === "yes",
      },
    };
    const locked = { ...draft, attempt };
    setDraft(locked);
    write(locked);
    setPhase("pending");
    setMessage(`Saving set ${set}…`);
    try {
      await p.submit(set, attempt.performed);
      edited.current = true;
      const next = {
        ...locked,
        canonical: attempt.performed.canonicalWeight,
        source: "manual" as const,
        reps: "",
        rpe: "",
        rir: "",
        quality: "unknown" as const,
        pain: "unknown" as const,
        attempt: undefined,
      };
      setDraft(next);
      write(next);
      setConfirmed(Math.max(confirmed, set));
      setPhase("saved");
      setMessage(`✓ Set ${set} saved`);
    } catch (e) {
      if (acknowledgedCommands.current.has(attempt.command)) return;
      if (
        e instanceof ApiError &&
        e.status === 409 &&
        /^Logical (working )?set already logged;/.test(e.message)
      ) {
        acknowledgeLogCommand(
          pendingCommandKey(p.scope, p.exerciseId, `work:${set}`),
        );
        const next = { ...locked, attempt: undefined };
        setDraft(next);
        write(next);
        setPhase("conflict");
        setMessage(
          "A saved set already exists. Reload saved sets to review it.",
        );
      } else if (
        e instanceof ApiError &&
        (e.status === 422 ||
          (e.status === 409 && e.code === "stale_load_recommendation"))
      ) {
        const next = { ...locked, attempt: undefined };
        setDraft(next);
        write(next);
        setPhase("error");
        setMessage(e.message);
      } else {
        setPhase("uncertain");
        setMessage("Save not confirmed. Retry the same set.");
      }
    } finally {
      busy.current = false;
    }
  }
  return {
    draft,
    phase,
    message,
    valid,
    confirmed,
    storageAvailable,
    locked:
      phase === "pending" || phase === "conflict" || Boolean(draft.attempt),
    edit,
    save,
  };
}
