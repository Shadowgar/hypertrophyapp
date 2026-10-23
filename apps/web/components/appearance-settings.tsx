"use client";
import { useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";
import { useAppearance } from "./appearance-provider";
import { Button } from "./ui/button";
export function AppearanceSettings() {
  const { preferences, ready, error, reload, save, preview } = useAppearance();
  const [draft, setDraft] = useState(preferences);
  const [status, setStatus] = useState("");
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [conflict, setConflict] = useState(false);
  const active = useRef(false);
  useEffect(() => {
    setDraft(preferences);
    setUncertain(false);
    setConflict(false);
  }, [preferences]);
  useEffect(() => () => preview(null), [preview]);
  const change = (value: Partial<typeof draft>) => {
    const next = { ...draft, ...value };
    setDraft(next);
    preview(next);
    setStatus("Preview only. Save to use this appearance on your account.");
  };
  return (
    <section className="ux-card space-y-4" aria-labelledby="appearance-title">
      <h2 id="appearance-title">Appearance</h2>
      <p>
        Your familiar Classic WorkoutApp Dark stays selected until you change
        it.
      </p>
      <fieldset
        disabled={!ready || pending || uncertain || conflict}
        className="space-y-4"
      >
        <label className="ux-field">
          Theme family
          <select
            aria-label="Theme family"
            value={draft.theme_family}
            onChange={(e) =>
              change({
                theme_family: e.target.value as typeof draft.theme_family,
              })
            }
          >
            <option value="graphite">Graphite</option>
            <option value="charcoal">Charcoal</option>
            <option value="classic">Classic WorkoutApp</option>
          </select>
        </label>
        <label className="ux-field">
          Appearance
          <select
            aria-label="Appearance"
            value={draft.appearance}
            onChange={(e) =>
              change({ appearance: e.target.value as typeof draft.appearance })
            }
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">Follow Device Settings</option>
          </select>
        </label>
        <label className="ux-field">
          Weight unit
          <select
            aria-label="Weight unit"
            value={draft.weight_unit}
            onChange={(e) =>
              setDraft({ ...draft, weight_unit: e.target.value as "kg" | "lb" })
            }
          >
            <option value="lb">Pounds (lb)</option>
            <option value="kg">Kilograms (kg)</option>
          </select>
        </label>
      </fieldset>
      <p className="ux-muted">
        Themes sync across mobile and desktop. Follow Device Settings uses each
        device’s own appearance. A set in progress keeps its original unit.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button
          disabled={!ready || pending || conflict}
          onClick={async () => {
            if (active.current) return;
            active.current = true;
            setPending(true);
            setStatus("Saving appearance…");
            try {
              await save(draft, draft.revision);
              setUncertain(false);
              setStatus("Appearance saved.");
            } catch (e) {
              if (e instanceof ApiError && e.status === 409) {
                setConflict(true);
                setStatus(e.message);
              } else {
                setUncertain(true);
                setStatus(
                  "Save not confirmed. Retry these same preferences or reload the saved appearance.",
                );
              }
            } finally {
              active.current = false;
              setPending(false);
            }
          }}
        >
          {pending
            ? "Saving…"
            : uncertain
              ? "Retry same preferences"
              : "Save appearance"}
        </Button>
        <Button
          variant="secondary"
          disabled={pending}
          onClick={async () => {
            preview(null);
            setDraft(preferences);
            setStatus("");
            await reload();
          }}
        >
          Restore saved appearance
        </Button>
      </div>
      <p role="status" className="min-h-12">
        {error ||
          status ||
          (!ready
            ? "Loading saved appearance…"
            : "Six appearances. One familiar WorkoutApp.")}
      </p>
    </section>
  );
}
