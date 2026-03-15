"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
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
import { kgToLbs } from "@/lib/weight";

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

function humanizeTokenLabel(value: string): string {
  return value
    .split(/[_-]/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

function formatExercisePrescription(exercise: WorkoutExercise): string {
  const [minReps, maxReps] = exercise.rep_range;
  return `${exercise.sets} x ${minReps}-${maxReps} @ ${kgToLbs(exercise.recommended_working_weight)} lbs`;
}

function formatLeadExercise(workout: WorkoutSession | null): string {
  const firstExercise = workout?.exercises[0];
  if (!firstExercise) {
    return "No lead lift queued yet";
  }
  return `${firstExercise.name} · ${formatExercisePrescription(firstExercise)}`;
}

function resolveWeakAreasLabel(profile: Profile | null): string {
  const weakAreas = profile?.weak_areas?.filter((item) => item.trim().length > 0) ?? [];
  if (weakAreas.length === 0) {
    return "No weak-area bias saved";
  }
  return weakAreas.map(humanizeTokenLabel).join(", ");
}

function resolveCoachPriorities(hasToken: boolean, dashboard: DashboardState): string[] {
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
    priorities.push(`Start with ${firstExercise.name}: ${formatExercisePrescription(firstExercise)}.`);
  }

  const weakAreas = dashboard.profile?.weak_areas?.filter((item) => item.trim().length > 0) ?? [];
  if (weakAreas.length > 0) {
    priorities.push(`Bias effort toward ${weakAreas.slice(0, 2).map(humanizeTokenLabel).join(" and ")} while readiness is good.`);
  }

  if (dashboard.analytics?.pr_highlights.length) {
    priorities.push(
      `Momentum is positive: ${dashboard.analytics.pr_highlights.length} PR highlight${dashboard.analytics.pr_highlights.length === 1 ? "" : "s"} in the current analytics window.`,
    );
  }

  if (priorities.length === 0) {
    priorities.push("Generate a week to queue the next session and unlock adaptive coaching signals.");
  }

  return priorities.slice(0, 3);
}

function resolveMomentumInsights(analytics: HistoryAnalyticsResponse | null): DashboardInsight[] {
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
        ? `Latest ${strengthTrend.latest_weight} top set across ${strengthTrend.points.length} tracked sessions`
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
  const priorities = resolveCoachPriorities(hasToken, dashboard);

  return (
    <div className="main-card main-card--module spacing-grid">
      <div className="telemetry-header">
        <div>
          <p className="telemetry-kicker">Coach Brief</p>
          <p className="telemetry-value">{hasToken ? "Today&apos;s command deck" : "How the app coaches"}</p>
        </div>
        <span className="telemetry-status">
          <span className={`status-dot status-dot--${dashboard.reviewStatus?.review_required ? "yellow" : "green"}`} />
          {dashboard.reviewStatus?.review_required ? "Needs review" : "Actionable"}
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
              <p className="text-xs text-zinc-300">{formatExercisePrescription(exercise)}</p>
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
  return (
    <div className="main-card main-card--module spacing-grid">
      <div className="telemetry-header">
        <div>
          <p className="telemetry-kicker">Block Radar</p>
          <p className="telemetry-value">{formatProgramName(profile)}</p>
        </div>
        <p className="telemetry-meta">{profile ? `${profile.days_available} training days` : "Profile not set"}</p>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2">
          <p className="telemetry-kicker">Lead Lift</p>
          <p className="text-sm text-zinc-100">{formatLeadExercise(workout)}</p>
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
  const insights = resolveMomentumInsights(analytics);

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
  const selectedProgramId = profile?.selected_program_id?.trim();
  if (!selectedProgramId) {
    return "Choose a program";
  }
  return getProgramDisplayName({ id: selectedProgramId });
}

function formatBodyweight(analytics: HistoryAnalyticsResponse | null, profile: Profile | null): string {
  const latest = analytics?.bodyweight_trend.at(-1);
  if (latest?.body_weight !== undefined && latest?.body_weight !== null) {
    return `${latest.body_weight} lb`;
  }
  if (profile?.weight !== undefined && profile?.weight !== null) {
    return `${profile.weight} lb`;
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
  return `${profile.days_available} training days · ${formatProgramName(profile)}`;
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

function resolveDashboardPresentation(hasToken: boolean, dashboard: DashboardState): DashboardPresentation {
  if (!hasToken) {
    return {
      intro: "Start with onboarding, then generate your week.",
      readinessTone: "green",
      readinessLabel: "Guest Preview",
      weekLabel: "Week not started",
      statsLabel: "No trend stats yet",
      workoutMeta: formatWorkoutMeta(null),
      weekMeta: formatWeekMeta(null),
    };
  }

  let readinessLabel = "Ready To Train";
  let readinessTone: "green" | "yellow" = "green";
  if (dashboard.reviewStatus?.review_required) {
    readinessLabel = "Review Required";
    readinessTone = "yellow";
  } else if (dashboard.workout?.deload?.active) {
    readinessLabel = "Deload Week";
    readinessTone = "yellow";
  }

  return {
    intro: "Open today’s session, review readiness, and keep the current training block moving.",
    readinessTone,
    readinessLabel,
    weekLabel: dashboard.workout?.mesocycle ? `Week ${dashboard.workout.mesocycle.week_index}` : "Week not started",
    statsLabel: resolveStatsLabel(dashboard.analytics),
    workoutMeta: formatWorkoutMeta(dashboard.workout),
    weekMeta: formatWeekMeta(dashboard.profile),
  };
}

export default function HomePage() {
  const [dashboard, setDashboard] = useState<DashboardState>({
    profile: null,
    workout: null,
    analytics: null,
    reviewStatus: null,
  });
  const [dashboardStatus, setDashboardStatus] = useState("Sign in to load your training dashboard.");
  const [hasToken, setHasToken] = useState(false);

  useEffect(() => {
    const token = getToken();
    setHasToken(Boolean(token));

    if (!token) {
      setDashboardStatus("Sign in to load your training dashboard.");
      return;
    }

    let mounted = true;
    setDashboardStatus("Loading dashboard...");

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

      const loadedCount = Object.values(nextState).filter(Boolean).length;
      if (loadedCount === 0) {
        setDashboardStatus("Dashboard data is unavailable. Log in again or finish onboarding.");
        return;
      }

      if (nextState.reviewStatus?.review_required) {
        setDashboardStatus("Weekly review required before the next planning cycle.");
        return;
      }

      if (nextState.workout) {
        setDashboardStatus("Today’s session is ready.");
        return;
      }

      setDashboardStatus("Dashboard synced. Generate a week to load today’s session.");
    });

    return () => {
      mounted = false;
    };
  }, []);

  const presentation = useMemo(() => resolveDashboardPresentation(hasToken, dashboard), [dashboard, hasToken]);
  const bodyweightLabel = formatBodyweight(dashboard.analytics, dashboard.profile);

  return (
    <div className="space-y-4">
      <h1 className="ui-title-hero text-center">Rocco&apos;s HyperTrophy Plan</h1>
      <p className="ui-body-sm text-center">{presentation.intro}</p>

      <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Dashboard Status</p>
        <div className="telemetry-header">
          <p className="telemetry-value">{presentation.readinessLabel}</p>
          <span className="telemetry-status">
            <span className={`status-dot status-dot--${presentation.readinessTone}`} /> {hasToken ? "Synced" : "Ready"}
          </span>
        </div>
        <p className="telemetry-meta">{dashboardStatus}</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Today&apos;s Workout</p>
          <p className="telemetry-value">{dashboard.workout?.title ?? "No session queued"}</p>
          <p className="telemetry-meta">{presentation.workoutMeta}</p>
        </div>
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Current Week</p>
          <p className="telemetry-value">{presentation.weekLabel}</p>
          <p className="telemetry-meta">{presentation.weekMeta}</p>
        </div>
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Bodyweight</p>
          <p className="telemetry-value">{bodyweightLabel}</p>
          <p className="telemetry-meta">
            {dashboard.analytics?.bodyweight_trend.length
              ? `Latest check-in inside ${dashboard.analytics.window.limit_weeks}-week window`
              : "Track weekly review check-ins to build the trend"}
          </p>
        </div>
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Training Stats</p>
          <p className="telemetry-value">{presentation.statsLabel}</p>
          <p className="telemetry-meta">{formatTrendMeta(dashboard.analytics)}</p>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <CoachBriefCard hasToken={hasToken} dashboard={dashboard} />
        <SessionBlueprintCard workout={dashboard.workout} />
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <BlockRadarCard profile={dashboard.profile} workout={dashboard.workout} />
        <MomentumRadarCard analytics={dashboard.analytics} />
      </div>

      <div className="main-card main-card--module spacing-grid">
        <div className="grid grid-cols-2 gap-3">
          <Link href="/login" className="block">
            <Button className="w-full" variant="secondary">
              <span className="inline-flex items-center gap-2">
                <UiIcon name="login" className="ui-icon--action" />
                Login
              </span>
            </Button>
          </Link>
          <Link href="/reset-password" className="block">
            <Button className="w-full" variant="secondary">
              <span className="inline-flex items-center gap-2">
                <UiIcon name="reset" className="ui-icon--action" />
                Reset Password
              </span>
            </Button>
          </Link>
          <Link href="/onboarding" className="block">
            <Button className="w-full">
              <span className="inline-flex items-center gap-2">
                <UiIcon name="onboarding" className="ui-icon--action" />
                Start Onboarding
              </span>
            </Button>
          </Link>
          <Link href="/today" className="block">
            <Button className="w-full" variant="secondary">
              <span className="inline-flex items-center gap-2">
                <UiIcon name="workout" className="ui-icon--action" />
                Go To Today
              </span>
            </Button>
          </Link>
          <Link href="/week" className="block">
            <Button className="w-full" variant="secondary">
              <span className="inline-flex items-center gap-2">
                <UiIcon name="plan" className="ui-icon--action" />
                Generate Week
              </span>
            </Button>
          </Link>
          <Link href="/history" className="block">
            <Button className="w-full" variant="secondary">
              <span className="inline-flex items-center gap-2">
                <UiIcon name="history" className="ui-icon--action" />
                Open History
              </span>
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
