"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, getProgramDisplayName, getToken, type Profile, type ProgramTemplateOption, type SchedulingContext } from "@/lib/api";

const AUTH_TOKEN_EVENT = "hypertrophy:auth-token-changed";
const AUTHORED_IDS = ["pure_bodybuilding_phase_1_full_body", "pure_bodybuilding_phase_2_full_body"];
type Resource<T> = { status: "loading" } | { status: "error" } | { status: "ready"; value: T };
type CatalogView = {
  token: string | null;
  catalog: Resource<ProgramTemplateOption[]>;
  profile: Resource<Profile>;
  schedule: Resource<SchedulingContext>;
};
const loadingView = (token: string | null): CatalogView => ({
  token, catalog: { status: "loading" }, profile: { status: "loading" }, schedule: { status: "loading" },
});

export default function ProgramsPage() {
  const [token, setToken] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [view, setView] = useState<CatalogView>(() => loadingView(null));

  useEffect(() => {
    const sync = () => setToken(getToken());
    sync();
    window.addEventListener(AUTH_TOKEN_EVENT, sync);
    window.addEventListener("storage", sync);
    window.addEventListener("focus", sync);
    return () => {
      window.removeEventListener(AUTH_TOKEN_EVENT, sync);
      window.removeEventListener("storage", sync);
      window.removeEventListener("focus", sync);
    };
  }, []);

  useEffect(() => {
    if (!token) return;
    let retired = false;
    const current = () => !retired && getToken() === token;
    setView(loadingView(token));
    // Catalog discovery is independent of account/schedule latency.
    void api.listPrograms().then((catalog) => {
      if (current()) setView((previous) => ({ ...previous, catalog: { status: "ready", value: catalog } }));
    }).catch(() => {
      if (current()) setView((previous) => ({ ...previous, catalog: { status: "error" } }));
    });
    void api.getProfile().then(async (profile) => {
      if (!current()) return;
      setView((previous) => ({ ...previous, profile: { status: "ready", value: profile } }));
      try {
        const timezone = profile.scheduling_timezone || Intl.DateTimeFormat().resolvedOptions().timeZone;
        const schedule = await api.getSchedulingContext(timezone);
        if (current()) setView((previous) => ({ ...previous, schedule: { status: "ready", value: schedule } }));
      } catch {
        if (current()) setView((previous) => ({ ...previous, schedule: { status: "error" } }));
      }
    }).catch(() => {
      if (current()) setView((previous) => ({ ...previous, profile: { status: "error" }, schedule: { status: "error" } }));
    });
    return () => { retired = true; };
  }, [token, attempt]);

  if (!token) {
    return <section className="ux-card space-y-4"><h1>Programs</h1><p>Sign in to explore programs and see your saved training choices.</p><Link className="ux-button ux-button-primary px-4" href="/login?next=%2Fprograms">Sign in</Link></section>;
  }

  // Never render a previous token's successful state while the next effect starts.
  const visible = view.token === token ? view : loadingView(token);
  const { catalog, profile, schedule } = visible;
  const authored = catalog.status === "ready" ? AUTHORED_IDS.flatMap((id) => catalog.value.filter((program) => program.id === id)) : [];
  const savedPreference = profile.status === "ready"
    ? profile.value.program_selection_mode === "auto"
      ? "Choose For Me"
      : profile.value.selected_program_id ? getProgramDisplayName({ id: profile.value.selected_program_id }) : "No program chosen yet"
    : null;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="ux-muted text-sm">Programs</p>
        <h1>Your programs</h1>
        <p className="ux-muted">Choose with confidence. Review a program before planning your dates.</p>
      </header>
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <section className="space-y-3" aria-labelledby="program-options-heading">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="program-options-heading">Explore programs</h2>
            <button className="ux-button ux-button-ghost px-3" aria-disabled={catalog.status === "loading"} onClick={() => { if (catalog.status !== "loading") setAttempt((value) => value + 1); }}>
              {catalog.status === "error" ? "Retry programs" : "Refresh programs"}
            </button>
          </div>
          <div role="status" aria-live="polite">
            {catalog.status === "loading" ? <p>Loading available programs…</p> : catalog.status === "error" ? <p>Could not load the program catalog. Your saved choices have not changed.</p> : authored.length === 0 ? <p>No Authored programs are currently listed. Try refreshing the catalog.</p> : null}
          </div>
          {authored.map((program) => {
            const name = getProgramDisplayName(program);
            const scheduled = schedule.status === "ready" && schedule.value.plan?.program_template_id === program.id;
            return <Link className="ux-card block space-y-2" href={`/programs/${encodeURIComponent(program.id)}`} aria-label={`View ${name} guide`} key={program.id}>
              <div className="flex justify-between gap-3"><h3 className="text-lg">{name}</h3><span aria-hidden="true">›</span></div>
              <p className="ux-muted text-sm">Authored · {scheduled ? "scheduled this week" : "separate source program"}</p>
              {program.days_supported?.length ? <p className="ux-muted text-sm">{program.days_supported.join(", ")} training days per week · View guide</p> : <p className="ux-muted text-sm">View the original program guide</p>}
            </Link>;
          })}
          <Link className="ux-card block space-y-2" href="/customize" aria-label="Review Customized options">
            <div className="flex justify-between gap-3"><h3 className="text-lg">Customized Full Body</h3><span aria-hidden="true">›</span></div>
            <p className="ux-muted text-sm">Create an original plan with explicit permission, or review your existing Customized plan.</p>
          </Link>
          <p className="ux-muted text-sm">Browsing does not choose or replace a program. Choose For Me is a recommendation preference, not consent to customize.</p>
        </section>

        <aside className="space-y-4">
          <div className="ux-card space-y-5" aria-live="polite">
            <section className="space-y-1" aria-labelledby="scheduled-program-heading">
              <h2 id="scheduled-program-heading">This week’s schedule</h2>
              {schedule.status === "loading" ? <p className="ux-muted">Loading your schedule…</p> : schedule.status === "error" ? <p className="ux-muted">Could not load this week’s schedule. Refresh to try again.</p> : schedule.value.plan ? <>
                <p>{getProgramDisplayName({ id: schedule.value.plan.program_template_id })}</p>
                <p className="ux-muted text-sm">Week of {schedule.value.week_start} · {schedule.value.timezone}</p>
              </> : <p className="ux-muted">No dated schedule for this week. Choose your actual training dates in Week.</p>}
            </section>
            <section className="space-y-1" aria-labelledby="saved-program-heading">
              <h2 id="saved-program-heading">Saved preference</h2>
              <p>{profile.status === "loading" ? "Loading your preference…" : profile.status === "error" ? "Could not load your saved preference." : savedPreference}</p>
              <p className="ux-muted text-sm">A preference is separate from the program in your dated schedule.</p>
            </section>
          </div>
          <Link className="ux-card block space-y-2" href="/week" aria-label="Choose dates in Week">
            <h2>Review before activation</h2><p className="ux-muted text-sm">Choose a program and dates in Week, then review the workload and any future schedule changes.</p>
          </Link>
          <Link className="ux-card block space-y-2" href="/guides"><h2>Program library</h2><p className="ux-muted text-sm">Read the original program and exercise guides.</p></Link>
          <Link className="ux-card block space-y-2" href="/history" aria-label="View training history"><h2>Your recorded training</h2><p className="ux-muted text-sm">Previous workouts remain available in History.</p></Link>
        </aside>
      </div>
    </div>
  );
}
