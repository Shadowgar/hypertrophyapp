"use client";

import { authoredRepLabel, isBodyweightAuthored } from "@/lib/authored-prescription";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  api,
  getProgramDisplayName,
  getToken,
  type HistoryAnalyticsResponse,
  type Profile,
  type WeeklyReviewStatus,
  type WorkoutExercise,
  type WorkoutSession,
} from "@/lib/api";
import { useAppearance } from "@/components/appearance-provider";
import { displayLoad } from "@/lib/appearance";

type DashboardState = {
  profile: Profile | null;
  workout: WorkoutSession | null;
  analytics: HistoryAnalyticsResponse | null;
  reviewStatus: WeeklyReviewStatus | null;
};

type DashboardPresentation = {
  intro: string;
  readinessTone: "green" | "yellow";
  readinessLabel: string;
  weekLabel: string;
  statsLabel: string;
  workoutMeta: string;
  weekMeta: string;
};

type DashboardInsight = {
  title: string;
  value: string;
  meta: string;
};

type DashboardLoadState = "guest" | "loading" | "ready" | "partial" | "error";

function humanizeTokenLabel(value: string): string {
  return value
    .split(/[_-]/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function formatExercisePrescription(exercise: WorkoutExercise, unit: "kg" | "lb"): string {
  const load = isBodyweightAuthored(exercise) ? "Bodyweight" : exercise.recommended_working_weight == null ? "Record actual load" : `${displayLoad(exercise.recommended_working_weight, unit)} ${unit}`;
  return `${exercise.sets} x ${authoredRepLabel(exercise)} @ ${load}`;
}

function formatLeadExercise(workout: WorkoutSession | null, unit: "kg" | "lb"): string {
  const firstExercise = workout?.exercises[0];
  if (!firstExercise) {
    return "No lead lift queued yet";
  }
  return `${firstExercise.name} · ${formatExercisePrescription(firstExercise, unit)}`;
}

function resolveWeakAreasLabel(profile: Profile | null): string {
  const weakAreas = profile?.weak_areas?.filter((item) => item.trim().length > 0) ?? [];
  if (weakAreas.length === 0) {
    return "No weak-area bias saved";
  }
  return weakAreas.map(humanizeTokenLabel).join(", ");
}

function resolveCoachPriorities(hasToken: boolean, dashboard: DashboardState, unit: "kg" | "lb"): string[] {
  if (!hasToken) {
    return [
      "Finish onboarding to generate a personalized hypertrophy week.",
      "Run today’s session to unlock progression, history, and coaching signals.",
      "Use weekly review to feed recovery, adherence, and load decisions back into the plan.",
    ];
  }

  const priorities: string[] = [];
  const firstExercise = dashboard.workout?.exercises[0];
  if (dashboard.reviewStatus?.review_required) {
    priorities.push("Submit the weekly review before generating the next planning cycle.");
  }
  if (dashboard.workout?.resume) {
    priorities.push("Resume the unfinished session before rotating to a different workout day.");
  }
  if (dashboard.workout?.deload?.active) {
    priorities.push(
      `Deload is active. Keep execution clean and accept the reduced ${dashboard.workout.deload.load_reduction_pct}% load target this week.`,
    );
  }
  if (firstExercise) {
    priorities.push(`Start with ${firstExercise.name}: ${formatExercisePrescription(firstExercise, unit)}.`);
  }

  const weakAreas = dashboard.profile?.weak_areas?.filter((item) => item.trim().length > 0) ?? [];
  if (weakAreas.length > 0) {
    priorities.push(`Saved focus areas: ${weakAreas.slice(0, 2).map(humanizeTokenLabel).join(" and ")}. Follow the actual prescribed targets.`);
  }

  if (dashboard.analytics?.pr_highlights.length) {
    priorities.push(
      `Training history shows ${dashboard.analytics.pr_highlights.length} PR highlight${dashboard.analytics.pr_highlights.length === 1 ? "" : "s"} in the current analytics window.`,
    );
  }

  if (priorities.length === 0) {
    priorities.push("Generate a week to queue the next session and unlock adaptive coaching signals.");
  }

  return priorities.slice(0, 3);
}

function resolveMomentumInsights(analytics: HistoryAnalyticsResponse | null, unit: "kg" | "lb"): DashboardInsight[] {
  const adherence = analytics?.adherence;
  const strengthTrend = analytics?.strength_trends[0];
  const prCount = analytics?.pr_highlights.length ?? 0;
  let prValue = "No recent PRs";
  let prMeta = "PR highlights will surface automatically as new top sets land.";
  if (prCount > 0) {
    const suffix = prCount === 1 ? "" : "s";
    prValue = `${prCount} PR highlight${suffix}`;
    prMeta = "Use history to inspect where the momentum is coming from.";
  }

  return [
    {
      title: "Adherence",
      value: adherence ? `${adherence.average_pct}% avg` : "No adherence data",
      meta: adherence ? `Latest score ${adherence.latest_score}/5 with ${adherence.high_readiness_streak} high-readiness weeks` : "Log check-ins to build recovery-aware coaching.",
    },
    {
      title: "Strength Trend",
      value: strengthTrend ? humanizeTokenLabel(strengthTrend.exercise_id) : "No lift trend yet",
      meta: strengthTrend
        ? `Latest ${displayLoad(strengthTrend.latest_weight, unit)} ${unit} top set across ${strengthTrend.points.length} tracked sessions`
        : "Complete and log workouts to surface top moving lifts.",
    },
    {
      title: "PR Window",
      value: prValue,
      meta: prMeta,
    },
  ];
}

function CoachBriefCard({
  hasToken,
  dashboard,
}: Readonly<{
  hasToken: boolean;
  dashboard: DashboardState;
}>) {
  const { preferences } = useAppearance();
  const priorities = resolveCoachPriorities(hasToken, dashboard, preferences.weight_unit);

  return (
    <div className="main-card main-card--module spacing-grid">
      <div className="telemetry-header">
        <div>
          <p className="telemetry-kicker">Coach Brief</p>
          <p className="telemetry-value">{hasToken ? "Today&apos;s command deck" : "How the app coaches"}</p>
        </div>
        <span className="telemetry-status">
          <span className={`status-dot status-dot--${dashboard.reviewStatus?.review_required ? "yellow" : "green"}`} />
          {dashboard.reviewStatus?.review_required ? "Needs review" : dashboard.workout ? "Session available" : "Check Week"}
        </span>
      </div>
      <div className="space-y-2">
        {priorities.map((item) => (
          <div key={item} className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2 text-sm text-zinc-200">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}

function SessionBlueprintCard({ workout }: Readonly<{ workout: WorkoutSession | null }>) {
  const { preferences } = useAppearance();
  const previewExercises = workout?.exercises.slice(0, 3) ?? [];

  return (
    <div className="main-card main-card--module spacing-grid">
      <div className="telemetry-header">
        <div>
          <p className="telemetry-kicker">Session Blueprint</p>
          <p className="telemetry-value">{workout?.title ?? "No session queued"}</p>
        </div>
        <p className="telemetry-meta">{workout ? `${workout.exercises.length} exercises queued` : "Generate a week to queue training"}</p>
      </div>
      {previewExercises.length > 0 ? (
        <div className="space-y-2">
          {previewExercises.map((exercise) => (
            <div key={exercise.id} className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
              <p className="text-sm font-semibold text-zinc-100">{exercise.name}</p>
              <p className="text-xs text-zinc-300">{formatExercisePrescription(exercise, preferences.weight_unit)}</p>
            </div>
          ))}
          {workout && workout.exercises.length > previewExercises.length ? (
            <p className="text-xs text-zinc-400">+ {workout.exercises.length - previewExercises.length} more exercises in today&apos;s queue</p>
          ) : null}
        </div>
      ) : (
        <p className="telemetry-meta">Once a workout is generated, this card will show the lead lifts and prescriptions for today.</p>
      )}
    </div>
  );
}

function BlockRadarCard({
  profile,
  workout,
}: Readonly<{
  profile: Profile | null;
  workout: WorkoutSession | null;
}>) {
  const { preferences } = useAppearance();
  return (
    <div className="main-card main-card--module spacing-grid">
      <div className="telemetry-header">
        <div>
          <p className="telemetry-kicker">Block Radar</p>
          <p className="telemetry-value">{formatProgramName(profile)}</p>
        </div>
        <p className="telemetry-meta">{profile ? `${profile.effective_days_available ?? profile.days_available} training days` : "Profile not set"}</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
          <p className="telemetry-kicker">Lead Lift</p>
          <p className="text-sm text-zinc-100">{formatLeadExercise(workout, preferences.weight_unit)}</p>
        </div>
        <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
          <p className="telemetry-kicker">Nutrition Phase</p>
          <p className="text-sm text-zinc-100">{profile ? humanizeTokenLabel(profile.nutrition_phase) : "Maintenance"}</p>
        </div>
        <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
          <p className="telemetry-kicker">Weak Areas</p>
          <p className="text-sm text-zinc-100">{resolveWeakAreasLabel(profile)}</p>
        </div>
        <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
          <p className="telemetry-kicker">Equipment</p>
          <p className="text-sm text-zinc-100">
            {profile ? `${profile.equipment_profile.length} tools at ${profile.training_location ?? "your setup"}` : "Set location and equipment"}
          </p>
        </div>
      </div>
    </div>
  );
}

function MomentumRadarCard({ analytics }: Readonly<{ analytics: HistoryAnalyticsResponse | null }>) {
  const { preferences } = useAppearance();
  const insights = resolveMomentumInsights(analytics, preferences.weight_unit);

  return (
    <div className="main-card main-card--module spacing-grid">
      <div className="telemetry-header">
        <div>
          <p className="telemetry-kicker">Momentum Radar</p>
          <p className="telemetry-value">Training signal quality</p>
        </div>
        <p className="telemetry-meta">{analytics ? `${analytics.window.limit_weeks}-week window` : "Awaiting history"}</p>
      </div>
      <div className="space-y-2">
        {insights.map((insight) => (
          <div key={insight.title} className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
            <div className="flex items-center justify-between gap-3">
              <p className="telemetry-kicker">{insight.title}</p>
              <p className="text-sm font-semibold text-zinc-100">{insight.value}</p>
            </div>
            <p className="text-xs text-zinc-400">{insight.meta}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatProgramName(profile: Profile | null): string {
  const selectedProgramId = (profile?.effective_program_id ?? profile?.selected_program_id)?.trim();
  if (!selectedProgramId) {
    return "Choose a program";
  }
  return getProgramDisplayName({ id: selectedProgramId });
}

function formatBodyweight(analytics: HistoryAnalyticsResponse | null, profile: Profile | null, unit: "kg" | "lb"): string {
  const latest = analytics?.bodyweight_trend.at(-1);
  if (latest?.body_weight !== undefined && latest?.body_weight !== null) {
    return `${displayLoad(latest.body_weight, unit)} ${unit}`;
  }
  if (profile?.weight !== undefined && profile?.weight !== null) {
    return `${displayLoad(profile.weight, unit)} ${unit}`;
  }
  return "No bodyweight yet";
}

function formatTrendMeta(analytics: HistoryAnalyticsResponse | null): string {
  const leadTrend = analytics?.strength_trends[0];
  if (leadTrend?.exercise_id && leadTrend.points.length > 0) {
    const exerciseLabel = leadTrend.exercise_id
      .split("_")
      .filter(Boolean)
      .map((part) => part[0].toUpperCase() + part.slice(1))
      .join(" ");
    return `${exerciseLabel} tracked across ${leadTrend.points.length} sessions`;
  }
  const adherence = analytics?.adherence;
  if (adherence) {
    return `Adherence average ${adherence.average_pct}%`;
  }
  return "Load history to see progression trends";
}

function formatWorkoutMeta(workout: WorkoutSession | null): string {
  if (!workout) {
    return "Generate your week to load the next session";
  }
  return `${workout.exercises.length} exercises${workout.resume ? " · resumable" : ""}`;
}

function formatWeekMeta(profile: Profile | null): string {
  if (!profile) {
    return "Set your profile and preferred split";
  }
  return `${profile.effective_days_available ?? profile.days_available} training days · ${formatProgramName(profile)}`;
}

function resolveStatsLabel(analytics: HistoryAnalyticsResponse | null): string {
  if (analytics?.pr_highlights.length) {
    return `${analytics.pr_highlights.length} PR highlights`;
  }
  if (analytics?.adherence) {
    return `${analytics.adherence.high_readiness_streak} high-readiness weeks`;
  }
  return "No trend stats yet";
}

function resolveDashboardPresentation(
  hasToken: boolean,
  dashboard: DashboardState,
  loadState: DashboardLoadState,
  workoutChecked: boolean,
): DashboardPresentation {
  if (!hasToken) {
    return {
      intro: "Sign in to pick up your training where you left off.",
      readinessTone: "yellow",
      readinessLabel: "Welcome",
      weekLabel: "Not loaded",
      statsLabel: "Not loaded",
      workoutMeta: "Sign in to check your schedule",
      weekMeta: "Sign in to view your plan",
    };
  }

  if (loadState === "loading") {
    return {
      intro: "Checking your training plan and next session.",
      readinessTone: "yellow",
      readinessLabel: "Loading Home",
      weekLabel: "Loading…",
      statsLabel: "Loading…",
      workoutMeta: "Checking today's session",
      weekMeta: "Checking your program",
    };
  }

  if (loadState === "error") {
    return {
      intro: "Your saved training record is unchanged. Try loading Home again.",
      readinessTone: "yellow",
      readinessLabel: "Home unavailable",
      weekLabel: "Unavailable",
      statsLabel: "Unavailable",
      workoutMeta: "Session not checked",
      weekMeta: "Profile not checked",
    };
  }

  if (!workoutChecked) {
    return {
      intro: "The next session could not be checked. You can retry or review Week.",
      readinessTone: "yellow",
      readinessLabel: "Workout status unknown",
      weekLabel: "Not checked",
      statsLabel: dashboard.analytics ? resolveStatsLabel(dashboard.analytics) : "Unavailable",
      workoutMeta: "Session not checked",
      weekMeta: dashboard.profile ? formatWeekMeta(dashboard.profile) : "Profile unavailable",
    };
  }

  const readinessLabel = dashboard.reviewStatus?.review_required
    ? "Weekly review due"
    : dashboard.workout?.deload?.active
      ? "Scheduled deload"
      : dashboard.workout
        ? "Session available"
        : "Review your schedule";

  return {
    intro: "See your next session, review your week, and continue your training.",
    readinessTone: dashboard.workout && !dashboard.reviewStatus?.review_required && !dashboard.workout.deload?.active
      ? "green" : "yellow",
    readinessLabel,
    weekLabel: dashboard.workout?.mesocycle ? `Week ${dashboard.workout.mesocycle.week_index}` : "Week not shown",
    statsLabel: dashboard.analytics ? resolveStatsLabel(dashboard.analytics) : loadState === "partial" ? "Unavailable" : "No trend stats yet",
    workoutMeta: formatWorkoutMeta(dashboard.workout),
    weekMeta: dashboard.profile ? formatWeekMeta(dashboard.profile) : "Profile unavailable",
  };
}

export default function HomePage() {
  const { preferences } = useAppearance();
  const [dashboard, setDashboard] = useState<DashboardState>({
    profile: null,
    workout: null,
    analytics: null,
    reviewStatus: null,
  });
  const [dashboardStatus, setDashboardStatus] = useState("Sign in to view your training.");
  const [hasToken, setHasToken] = useState<boolean | null>(null);
  const [loadState, setLoadState] = useState<DashboardLoadState>("loading");
  const [workoutChecked, setWorkoutChecked] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const token = getToken();
    setHasToken(Boolean(token));

    if (!token) {
      setLoadState("guest");
      setWorkoutChecked(false);
      setDashboardStatus("Sign in to view your training.");
      return;
    }

    let mounted = true;
    setLoadState("loading");
    setWorkoutChecked(false);
    setDashboardStatus("Loading your training dashboard…");

    Promise.allSettled([
      api.getProfile(),
      api.getTodayWorkout(),
      api.getHistoryAnalytics(8, 24),
      api.getWeeklyReviewStatus(),
    ]).then((results) => {
      if (!mounted) {
        return;
      }

      const nextState: DashboardState = {
        profile: results[0].status === "fulfilled" ? results[0].value : null,
        workout: results[1].status === "fulfilled" ? results[1].value : null,
        analytics: results[2].status === "fulfilled" ? results[2].value : null,
        reviewStatus: results[3].status === "fulfilled" ? results[3].value : null,
      };
      setDashboard(nextState);

      const failedCount = results.filter((result) => result.status === "rejected").length;
      const todayChecked = results[1].status === "fulfilled";
      setWorkoutChecked(todayChecked);
      setLoadState(failedCount === results.length ? "error" : failedCount > 0 ? "partial" : "ready");

      if (!todayChecked) {
        setDashboardStatus("Could not check today's workout. Retry before assuming it is a rest day.");
      } else if (nextState.reviewStatus?.review_required) {
        setDashboardStatus("Weekly review is due before the next planning cycle.");
      } else if (nextState.workout) {
        setDashboardStatus(failedCount > 0
          ? "Today's session is available. Some other dashboard information could not load."
          : "Today's session is available.");
      } else {
        setDashboardStatus("No session was returned for today. Review Week for your actual schedule.");
      }
    });

    return () => {
      mounted = false;
    };
  }, [reloadKey]);

  const presentation = useMemo(
    () => resolveDashboardPresentation(Boolean(hasToken), dashboard, loadState, workoutChecked),
    [dashboard, hasToken, loadState, workoutChecked],
  );
  const bodyweightLabel = formatBodyweight(dashboard.analytics, dashboard.profile, preferences.weight_unit);

  if (hasToken === null) {
    return <div className="main-card main-card--module" role="status">Loading WorkoutApp Home…</div>;
  }

  if (!hasToken) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <h1 className="ui-title-hero">WorkoutApp</h1>
        <p className="ui-body-sm">Your next session starts here. Sign in to continue your plan, or set up your first program.</p>
        <div className="main-card main-card--module spacing-grid">
          <p className="telemetry-kicker">Get started</p>
          <Link className="ux-button ux-button-primary w-full" href="/login">Sign in</Link>
          <Link className="ux-button ux-button-secondary w-full" href="/onboarding">Start onboarding</Link>
          <Link className="text-sm underline" href="/reset-password">Need to reset your password?</Link>
        </div>
      </div>
    );
  }

  const showDetails = loadState !== "loading" && loadState !== "error";
  const nextSession = workoutChecked ? dashboard.workout : null;

  return (
    <div className="space-y-4">
      <h1 className="ui-title-hero text-center">Your next session</h1>
      <p className="ui-body-sm text-center">{presentation.intro}</p>

      <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Home status</p>
        <div className="telemetry-header">
          <p className="telemetry-value">{presentation.readinessLabel}</p>
          <span className="telemetry-status">
            <span className={"status-dot status-dot--" + presentation.readinessTone} />
            {loadState === "loading" ? "Checking" : loadState === "error" ? "Unavailable" : loadState === "partial" ? "Partial data" : nextSession ? "Session found" : "Checked"}
          </span>
        </div>
        <p className="telemetry-meta" role="status">{dashboardStatus}</p>
      </div>

      <div className="main-card main-card--module spacing-grid">
        <p className="telemetry-kicker">Next step</p>
        {loadState === "loading" ? (
          <p className="telemetry-meta">Checking your workout and saved schedule…</p>
        ) : nextSession ? (
          <Link className="ux-button ux-button-primary w-full" href="/today">
            {nextSession.resume ? "Resume your workout" : "Open today's workout"}
          </Link>
        ) : !workoutChecked ? (
          <button className="ux-button ux-button-primary w-full" type="button" onClick={() => setReloadKey((key) => key + 1)}>
            Retry Home
          </button>
        ) : (
          <Link className="ux-button ux-button-primary w-full" href="/week">Review Week</Link>
        )}
        <div className="flex flex-wrap gap-4 text-sm">
          <Link href="/week" className="underline">Open Week</Link>
          <Link href="/history" className="underline">View History</Link>
          <Link href="/checkin" className="underline">Check-In</Link>
        </div>
      </div>

      {showDetails ? (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div className="main-card main-card--shell">
              <p className="telemetry-kicker">Today's Workout</p>
              <p className="telemetry-value">{workoutChecked ? dashboard.workout?.title ?? "No session returned today" : "Not checked"}</p>
              <p className="telemetry-meta">{presentation.workoutMeta}</p>
            </div>
            <div className="main-card main-card--shell">
              <p className="telemetry-kicker">Current Week</p>
              <p className="telemetry-value">{presentation.weekLabel}</p>
              <p className="telemetry-meta">{presentation.weekMeta}</p>
            </div>
            {dashboard.profile || dashboard.analytics ? (
              <div className="main-card main-card--shell">
                <p className="telemetry-kicker">Bodyweight</p>
                <p className="telemetry-value">{bodyweightLabel}</p>
                <p className="telemetry-meta">
                  {dashboard.analytics?.bodyweight_trend.length
                    ? `Latest check-in inside ${dashboard.analytics.window.limit_weeks}-week window`
                    : "Track weekly review check-ins to build the trend"}
                </p>
              </div>
            ) : null}
            {dashboard.analytics ? (
              <div className="main-card main-card--shell">
                <p className="telemetry-kicker">Training Stats</p>
                <p className="telemetry-value">{presentation.statsLabel}</p>
                <p className="telemetry-meta">{formatTrendMeta(dashboard.analytics)}</p>
              </div>
            ) : null}
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            {workoutChecked ? <CoachBriefCard hasToken={hasToken} dashboard={dashboard} /> : null}
            {workoutChecked ? <SessionBlueprintCard workout={dashboard.workout} /> : null}
          </div>
          <div className="grid gap-3 lg:grid-cols-2">
            {dashboard.profile ? <BlockRadarCard profile={dashboard.profile} workout={dashboard.workout} /> : null}
            {dashboard.analytics ? <MomentumRadarCard analytics={dashboard.analytics} /> : null}
          </div>
        </>
      ) : null}
    </div>
  );
}
