"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { WorkoutWorkload, workloadMode } from "@/components/workout-workload";
import { FlexibleTraining } from "@/components/flexible-training";
import { NextWorkout } from "@/components/next-workout";
import { useAppearance } from "@/components/appearance-provider";
import { api, ApiError, getProgramDisplayName, getToken, type HistoryAnalyticsResponse, type Profile, type SchedulingContext, type WeeklyReviewStatus, type WorkoutSession } from "@/lib/api";
import { displayLoad } from "@/lib/appearance";
import { authoredRepLabel, isBodyweightAuthored } from "@/lib/authored-prescription";
import { datesInWeek, formatCalendarDate } from "@/lib/calendar-date";

type HomeWorkout = WorkoutSession & { program_template_id?: string | null; selected_program_id?: string | null };

type Data = {
  profile: Profile | null;
  workout: HomeWorkout | null;
  analytics: HistoryAnalyticsResponse | null;
  review: WeeklyReviewStatus | null;
  week: SchedulingContext | null;
};
type ReadStatus = "pending" | "ready" | "error";
type HomeState = {
  token: string | null | undefined;
  data: Data;
  status: Record<keyof Data, ReadStatus>;
  retryAvailable: boolean;
};
const emptyData: Data = { profile: null, workout: null, analytics: null, review: null, week: null };
function initialState(token: HomeState["token"], retryAvailable = false): HomeState {
  return { token, data: { ...emptyData }, status: { profile: "pending", workout: "pending", analytics: "pending", review: "pending", week: "pending" }, retryAvailable };
}
// Only these domain responses acknowledge absence. Unknown 404s and conflicts are failures.
function isNoWorkout(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404 &&
    ["No plan generated", "No workout scheduled today", "No workouts available"].includes(error.message);
}

function programName(profile: Profile | null, context: SchedulingContext | null, pending = false): string {
  const id = context?.plan?.program_template_id ?? profile?.effective_program_id ?? profile?.selected_program_id;
  return id ? getProgramDisplayName({ id }) : pending ? "Checking your program…" : profile ? "No program selected" : "Program details unavailable";
}


function workoutProgramName(workout: HomeWorkout, context: SchedulingContext | null, pending: boolean): string {
  const id = workout.program_template_id ?? workout.selected_program_id;
  if (id) return getProgramDisplayName({ id });
  if (workout.customized) return "Customized workout";
  // Calendar and Today are independent snapshots. Only an exact occurrence can bind them.
  if (workout.workout_occurrence_id && context?.plan?.sessions.some(session => session.workout_occurrence_id === workout.workout_occurrence_id)) {
    return programName(null, context);
  }
  return pending ? "Checking your program…" : "Program details unavailable";
}

export default function HomePage() {
  const { preferences } = useAppearance();
  const [home, setHome] = useState<HomeState>(() => initialState(undefined));
  const [flexibleMode, setFlexibleMode] = useState(false);
  const [trainingChecked, setTrainingChecked] = useState(false);
  const trainingResolved = useCallback((next: {mode: string} | null) => { setFlexibleMode(next?.mode === "flexible"); setTrainingChecked(true); }, []);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let mounted = true;
    let generation = 0;
    let activeToken: string | null | undefined;
    function load(keepRetry = false) {
      const token = getToken();
      const version = ++generation;
      activeToken = token;
      setFlexibleMode(false);
      setTrainingChecked(false);
      setHome(previous => initialState(token, keepRetry && previous.retryAvailable));
      if (!token) return;
      const isCurrent = () => mounted && version === generation && getToken() === token;
      function read<K extends keyof Data>(key: K, request: Promise<Data[K]>) {
        void request.then(value => {
          if (!isCurrent()) return;
          setHome(previous => ({ ...previous, data: { ...previous.data, [key]: value }, status: { ...previous.status, [key]: "ready" } }));
        }, error => {
          if (!isCurrent()) return;
          if (key === "workout" && isNoWorkout(error)) {
            setHome(previous => ({ ...previous, status: { ...previous.status, workout: "ready" } }));
          } else {
            setHome(previous => ({ ...previous, status: { ...previous.status, [key]: "error" }, retryAvailable: true }));
          }
        });
      }
      // Today is independently actionable. Optional profile/history/review/calendar reads never gate it.
      const training = api.getNextTraining();
      read("workout", training.then(next => next.mode === "flexible" && !["active", "finish"].includes(next.action) ? null : api.getTodayWorkout()));
      read("profile", api.getProfile());
      read("analytics", api.getHistoryAnalytics(8, 24));
      read("review", training.then(next => next.mode === "flexible" ? null : api.getWeeklyReviewStatus()));
      // The API prefers the account's saved timezone; this is only a first-use fallback.
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
      read("week", api.getSchedulingContext(timezone));
    }
    load(true);
    const sync = () => { if (activeToken !== getToken()) load(); };
    const storage = (event: StorageEvent) => { if (event.key === "hypertrophy_token" || event.key === null) sync(); };
    window.addEventListener("hypertrophy:auth-token-changed", sync);
    window.addEventListener("storage", storage);
    window.addEventListener("focus", sync);
    return () => {
      mounted = false;
      ++generation;
      window.removeEventListener("hypertrophy:auth-token-changed", sync);
      window.removeEventListener("storage", storage);
      window.removeEventListener("focus", sync);
    };
  }, [reload]);

  if (home.token === undefined) return <div className="ux-card" role="status">Loading FERRAVIS Home…</div>;
  if (!home.token) return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1>FERRAVIS</h1>
      <p className="ux-eyebrow">Strength, Engineered.</p>
      <p className="ux-muted">Your next session starts here. Sign in to continue your plan, or set up your first program.</p>
      <div className="ux-card space-y-4">
        <h2>Ready for your next session?</h2>
        <p className="ux-muted">Your saved training stays with your account.</p>
        <Link className="ux-button ux-button-primary w-full" href="/login?next=%2F">Sign in</Link>
        <Link className="ux-button ux-button-secondary w-full" href="/onboarding">Start onboarding</Link>
        <Link className="ux-button ux-button-ghost w-full" href="/reset-password">Need to reset your password?</Link>
      </div>
    </div>
  );

  const { data, status } = home;
  const workout = data.workout;
  const checked = status.workout === "ready" && trainingChecked;
  const loading = status.workout === "pending" || !trainingChecked;
  const failed = status.workout === "error";
  const flexible = flexibleMode || data.profile?.schedule_mode === "flexible";
  const noSchedule = checked && !workout && status.week === "ready" && data.week?.plan === null;
  const title = flexible ? "Your training" : noSchedule ? "Your week is open" : workout ? "Your next session" : "Your training";
  const primaryTitle = loading ? "Checking your training" : failed ? "Home unavailable" : workout?.title ?? (noSchedule ? "Choose your training dates" : "Review your schedule");
  const message = loading ? "Checking your workout and saved schedule…"
    : failed ? "Could not check today's workout. Retry before assuming it is a rest day. Your saved history is unchanged."
    : workout ? (workout.resume ? "Your unfinished session is available to resume." : "Session available.")
    : noSchedule ? "No workouts scheduled for this week. Preview your dates in Week before you commit."
    : "No session returned today. Review Week for your actual schedule.";
  const knownProgram = workout
    ? workoutProgramName(workout, data.week, status.week === "pending")
    : programName(data.profile, data.week, status.profile === "pending" || status.week === "pending");
  const currentDates = data.week?.plan?.schedule?.mode === "selected_dates_v1" ? data.week.selected_dates : [];
  const analytics = data.analytics;
  const bodyweight = analytics?.bodyweight_trend?.at(-1)?.body_weight ?? data.profile?.weight;
  const leadTrend = analytics?.strength_trends?.[0];
  const prCount = analytics?.pr_highlights?.length ?? 0;

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header className="space-y-2">
        <p className="text-sm font-semibold uppercase tracking-wide text-[var(--accent-text)]">Home</p>
        <h1>{title}</h1>
        {data.week?.local_today ? <p className="ux-muted">{formatCalendarDate(data.week.local_today)}</p> : null}
      </header>
      {status.profile === 'ready' && data.profile ? <section className="ux-card space-y-3" aria-label="Account setup">
        <h2>{data.profile.initial_setup_available ? 'Finish setting up your account' : 'Your setup'}</h2>
        <Link className="ux-button ux-button-secondary" href="/onboarding">{data.profile.initial_setup_available || data.profile.setup_status === 'planning' ? 'Resume Setup' : 'Review/Edit Setup'}</Link>
        {data.profile.setup_status === 'planning' ? <Link className="ux-button ux-button-primary" href={flexible ? '/training/setup' : data.profile.selected_program_id === 'full_body_v1' ? '/customize' : '/week'}>{flexible ? 'Review Flexible program' : 'Continue to program & dates'}</Link> : null}
      </section> : null}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <section className="space-y-4" aria-label="Next step">
          <FlexibleTraining accountToken={home.token} onResolved={trainingResolved} timeBudgetMinutes={data.profile?.session_time_budget_minutes} reloadKey={reload} />
          {!flexible ? <div className="ux-card space-y-3" aria-busy={loading}>
            <p className="text-sm text-[var(--text-secondary)]">{knownProgram}</p>
            <h2 className="text-2xl">{primaryTitle}</h2>
            <p className="ux-muted" role="status" aria-live="polite">{message}</p>
            {workout ? <p className="ux-muted">{workout.exercises.length} {workout.exercises.length === 1 ? "exercise" : "exercises"}{workout.mesocycle ? ` · Week ${workout.mesocycle.week_index}` : ""}</p> : null}
            {workout ? <WorkoutWorkload exercises={workout.exercises} timeBudgetMinutes={data.profile?.session_time_budget_minutes} mode={workloadMode(workout.program_template_id ?? workout.selected_program_id, Boolean(workout.customized))} /> : null}
            {checked && !workout && !noSchedule && status.week === "pending" ? <p className="ux-muted">Your week is still loading.</p> : null}
            {checked && workout ? <Link className="ux-button ux-button-primary w-full" href="/today">{workout.resume ? "Resume your workout" : "Open today's workout"}</Link>
              : checked ? <Link className="ux-button ux-button-primary w-full" href="/week">{noSchedule ? "Choose dates" : "Review Week"}</Link> : null}
            {home.retryAvailable ? <button className={`ux-button ${failed ? "ux-button-primary" : "ux-button-secondary"} w-full`} type="button" aria-disabled={loading} onClick={() => { if (!loading) setReload(value => value + 1); }}>Retry Home</button> : null}
          </div> : null}
          {!flexible && checked && !workout ? <NextWorkout accountToken={home.token} timeBudgetMinutes={data.profile?.session_time_budget_minutes} enabled onMoved={() => setReload(value => value + 1)} /> : null}
          <Link className="ux-card block space-y-2" href="/checkin">
            <h2>A quick check-in?</h2>
            <p className="ux-muted">Optional. You can do it after training.</p>
            {data.review?.review_required ? <p className="ux-muted">Weekly review is due for planning. Your available workout stays accessible.</p> : null}
          </Link>
        </section>
        <aside className="space-y-4" aria-label="Your training week">
          <div className="ux-card space-y-3">
            <h2>{flexible ? "Your pace" : "This week"}</h2>
            {flexible ? <p className="ux-muted">{data.profile?.expected_sessions_per_week ? `Expected ${data.profile.expected_sessions_per_week} visits per week. ` : "No expected frequency set. "}Your original source block can span calendar weeks. Missing a date does not skip work.</p> : <>
            {data.week?.week_start && currentDates.length ? <ol className="grid grid-cols-7 gap-1" aria-label="Selected training dates">
              {datesInWeek(data.week.week_start).map(date => <li key={date}>
                <Link href="/week" aria-label={`${formatCalendarDate(date)}${currentDates.includes(date) ? ", training scheduled" : ", no training scheduled"}`} aria-current={date === data.week?.local_today ? "date" : undefined}
                  className={`flex min-h-12 items-center justify-center rounded-lg border border-[var(--border-control)] ${currentDates.includes(date) ? "bg-[var(--action-fill)] text-[var(--action-text)]" : "bg-[var(--surface-raised)]"}`}>
                  {Number(date.slice(-2))}
                </Link>
              </li>)}
            </ol> : <p className="ux-muted">{status.week === "pending" ? "Checking your saved dates…" : status.week === "error" ? "Your week could not be loaded." : data.week?.plan ? "Open Week to review your saved plan." : "Choose actual dates and preview your week."}</p>}
            {data.profile ? <p className="ux-muted">{data.profile.effective_days_available ?? data.profile.days_available} training days · {programName(data.profile, data.week)}</p> : null}
            <Link className="ux-button ux-button-secondary w-full" href="/week">Open Week</Link></>}
            {!flexible && data.profile?.selected_program_id?.startsWith("pure_bodybuilding_") ? <Link className="ux-button ux-button-secondary w-full" href="/training/setup">Switch to Flexible</Link> : null}
          </div>
          <Link className="ux-card block space-y-2" href="/history"><h2>Recent training</h2><p className="ux-muted">Your previous workouts are still in History.</p><span className="underline">View History</span></Link>
        </aside>
      </div>
      <details className="ux-card">
        <summary className="min-h-12 cursor-pointer font-semibold">Training summary</summary>
        <div className="space-y-4 pt-3">
          {status.analytics === "pending" ? <p className="ux-muted">Training summary is still loading.</p> : status.analytics === "error" ? <p className="ux-muted">Training summary could not be loaded. Retry Home to check again.</p> : null}
          {bodyweight != null ? <p>Bodyweight: {displayLoad(bodyweight, preferences.weight_unit)} {preferences.weight_unit}</p> : null}
          {analytics ? <><p>{prCount ? `${prCount} PR highlights` : "No recent PR highlights"}</p>{leadTrend ? <div><p>{leadTrend.exercise_id.replaceAll("_", " ")} · {leadTrend.points.length} tracked weeks</p><p>Latest recorded weekly maximum: {displayLoad(leadTrend.latest_weight, preferences.weight_unit)} {preferences.weight_unit}</p><p className="ux-muted">This summary may include different setups. Open Analytics for separate setup histories.</p></div> : <p className="ux-muted">Log workouts to build comparable history.</p>}</> : null}
          {workout?.exercises.slice(0, 3).map((exercise, index) => <p key={`${exercise.id}-${index}`}>
            {exercise.name} · {exercise.sets} x {authoredRepLabel(exercise)} @ {isBodyweightAuthored(exercise) ? "Bodyweight" : exercise.recommended_working_weight == null ? "Record actual load" : `${displayLoad(exercise.recommended_working_weight, preferences.weight_unit)} ${preferences.weight_unit}`}
          </p>)}
          <Link className="ux-button ux-button-ghost" href="/analytics">Open Analytics</Link>
        </div>
      </details>
    </div>
  );
}
