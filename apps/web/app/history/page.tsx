"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
import {
  api,
  type CoachingRecommendationTimelineEntry,
  type HistoryAnalyticsResponse,
} from "@/lib/api";

function formatTimestamp(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return iso;
  }
  return parsed.toLocaleString();
}

export default function HistoryPage() {
  const [history, setHistory] = useState("No analytics snapshot loaded.");
  const [dashboard, setDashboard] = useState<HistoryAnalyticsResponse | null>(null);
  const [trendStatus, setTrendStatus] = useState("Loading trend data...");
  const [timelineEntries, setTimelineEntries] = useState<CoachingRecommendationTimelineEntry[]>([]);
  const [timelineStatus, setTimelineStatus] = useState("Loading recommendation timeline...");

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const payload = await api.getHistoryAnalytics(8, 24);
        if (!mounted) {
          return;
        }
        setDashboard(payload);
        setTrendStatus(payload.checkins.length > 0 ? "" : "No weekly check-ins yet.");
      } catch {
        if (!mounted) {
          return;
        }
        setDashboard(null);
        setTrendStatus("Unable to load weekly check-in trends.");
      }

      try {
        const timeline = await api.getCoachingRecommendationTimeline(24);
        if (!mounted) {
          return;
        }
        setTimelineEntries(timeline.entries);
        setTimelineStatus(timeline.entries.length > 0 ? "" : "No coaching recommendations yet.");
      } catch {
        if (!mounted) {
          return;
        }
        setTimelineEntries([]);
        setTimelineStatus("Unable to load recommendation timeline.");
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const weeklyCheckins = useMemo(() => dashboard?.checkins ?? [], [dashboard]);

  const adherencePct = useMemo(() => {
    return dashboard?.adherence.average_pct ?? 0;
  }, [dashboard]);

  const adherenceStreak = useMemo(() => {
    return dashboard?.adherence.high_readiness_streak ?? 0;
  }, [dashboard]);

  const adherenceTrendDelta = useMemo(() => {
    return dashboard?.adherence.trend_delta ?? 0;
  }, [dashboard]);

  const measurementTrendCount = useMemo(() => dashboard?.body_measurement_trends.length ?? 0, [dashboard]);

  const bodyWeightTrend = useMemo(() => dashboard?.bodyweight_trend.map((item) => item.body_weight) ?? [], [dashboard]);

  const bodyWeightBounds = useMemo(() => {
    if (bodyWeightTrend.length === 0) {
      return { min: 0, max: 0, spread: 1 };
    }
    const min = Math.min(...bodyWeightTrend);
    const max = Math.max(...bodyWeightTrend);
    return { min, max, spread: Math.max(0.1, max - min) };
  }, [bodyWeightTrend]);

  const primaryStrengthTrend = useMemo(() => dashboard?.strength_trends[0] ?? null, [dashboard]);
  const strengthBounds = useMemo(() => {
    const points = primaryStrengthTrend?.points ?? [];
    if (points.length === 0) {
      return { min: 0, max: 0, spread: 1 };
    }
    const values = points.map((point) => point.max_weight);
    const min = Math.min(...values);
    const max = Math.max(...values);
    return { min, max, spread: Math.max(0.1, max - min) };
  }, [primaryStrengthTrend]);

  const adherenceMix = useMemo(() => {
    if (weeklyCheckins.length === 0) {
      return [0, 0, 0] as const;
    }
    const high = weeklyCheckins.filter((item) => item.adherence_score >= 4).length;
    const medium = weeklyCheckins.filter((item) => item.adherence_score === 3).length;
    const low = weeklyCheckins.filter((item) => item.adherence_score <= 2).length;
    const total = weeklyCheckins.length;
    return [
      Math.round((high / total) * 100),
      Math.round((medium / total) * 100),
      Math.round((low / total) * 100),
    ] as const;
  }, [weeklyCheckins]);

  const [mixHigh, mixMedium, mixLow] = adherenceMix;
  const prHighlights = dashboard?.pr_highlights ?? [];
  const measurementTrends = dashboard?.body_measurement_trends ?? [];

  const heatmap = dashboard?.volume_heatmap;
  const heatmapMax = Math.max(heatmap?.max_volume ?? 0, 1);

  async function loadHistory() {
    if (!dashboard) {
      setHistory("History dashboard data is unavailable.");
      return;
    }
    setHistory(JSON.stringify(dashboard, null, 2));
  }

  return (
    <div className="space-y-4">
      <h1 className="ui-title-page">History</h1>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">Adherence</p>
          <p className="telemetry-value">{adherencePct}% recent average</p>
        </div>
        <div className="main-card main-card--module main-card--accent">
          <p className="telemetry-kicker">Check-ins Logged</p>
          <p className="telemetry-value">{weeklyCheckins.length}</p>
        </div>
        <div className="main-card main-card--shell">
          <p className="telemetry-kicker">High-Readiness Streak</p>
          <p className="telemetry-value">{adherenceStreak} weeks</p>
        </div>
        <div className="main-card main-card--module">
          <p className="telemetry-kicker">Body Trend Series</p>
          <p className="telemetry-value">{measurementTrendCount}</p>
          <p className="telemetry-meta">Adherence trend {adherenceTrendDelta >= 0 ? "+" : ""}{adherenceTrendDelta}</p>
        </div>
      </div>
      <div className="main-card main-card--module">
        <p className="telemetry-kicker mb-2">History Controls</p>
        <Button className="w-full" onClick={loadHistory}>
          <span className="inline-flex items-center gap-2">
            <UiIcon name="analytics" className="ui-icon--action" />
            Load Analytics Snapshot
          </span>
        </Button>
      </div>
      <div className="main-card main-card--module spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">History Output</p>
        <pre className="overflow-x-auto text-xs text-zinc-200">{history}</pre>
      </div>

      <div className="main-card main-card--module spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Coaching Decision Timeline</p>
        {timelineEntries.length > 0 ? (
          <div className="space-y-2">
            {timelineEntries.map((entry) => (
              <div key={entry.recommendation_id} className="rounded-md border border-white/10 bg-zinc-900/60 p-2 text-xs text-zinc-200">
                <p className="flex items-center justify-between gap-2">
                  <span className="font-medium">{entry.recommendation_type.replaceAll("_", " ")}</span>
                  <span className="telemetry-meta uppercase">{entry.status}</span>
                </p>
                <p className="telemetry-meta">{entry.template_id} · {entry.current_phase} to {entry.recommended_phase}</p>
                <p className="telemetry-meta">Progression action: {entry.progression_action}</p>
                <p>Rationale: {entry.rationale}</p>
                <p>Focus muscles: {entry.focus_muscles.length > 0 ? entry.focus_muscles.join(", ") : "none"}</p>
                <p className="telemetry-meta">Created: {formatTimestamp(entry.created_at)}</p>
                {entry.applied_at ? <p className="telemetry-meta">Applied: {formatTimestamp(entry.applied_at)}</p> : null}
                <p className="telemetry-meta">Recommendation ID: {entry.recommendation_id}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-zinc-500">{timelineStatus}</p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-4">
        <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Bodyweight Trend</p>
          <div className="flex items-end gap-1 h-16">
            {bodyWeightTrend.length > 0 ? (
              bodyWeightTrend.map((value, index) => {
                const normalized = 25 + ((value - bodyWeightBounds.min) / bodyWeightBounds.spread) * 75;
                return (
                  <div
                    key={`weight-${value}-${index}`}
                    className="flex-1 rounded-sm bg-zinc-700/70"
                    style={{ height: `${Math.round(normalized)}%` }}
                    aria-label={`Week ${index + 1} bodyweight ${value}`}
                    title={`Week ${index + 1}: ${value} kg`}
                  />
                );
              })
            ) : (
              <div className="text-xs text-zinc-500">No trend data</div>
            )}
          </div>
          <p className="telemetry-meta">Last {Math.max(weeklyCheckins.length, 0)} check-ins</p>
        </div>

        <div className="main-card main-card--module spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Strength Trend</p>
          {primaryStrengthTrend ? (
            <>
              <p className="telemetry-meta">{primaryStrengthTrend.exercise_id}</p>
              <div className="flex items-end gap-1 h-16">
                {primaryStrengthTrend.points.map((point) => {
                  const normalized = 25 + ((point.max_weight - strengthBounds.min) / strengthBounds.spread) * 75;
                  return (
                    <div
                      key={`${primaryStrengthTrend.exercise_id}-${point.week_start}`}
                      className="flex-1 rounded-sm bg-zinc-700/70"
                      style={{ height: `${Math.round(normalized)}%` }}
                      title={`${point.week_start}: ${point.max_weight} kg`}
                    />
                  );
                })}
              </div>
              <p className="telemetry-meta">PR {primaryStrengthTrend.pr_weight} kg ({primaryStrengthTrend.pr_delta >= 0 ? "+" : ""}{primaryStrengthTrend.pr_delta})</p>
            </>
          ) : (
            <p className="text-xs text-zinc-500">No strength trend data</p>
          )}
        </div>

        <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">PR Highlights</p>
          {prHighlights.length > 0 ? (
            <div className="space-y-1 text-xs text-zinc-200">
              {prHighlights.map((item) => (
                <p key={`pr-${item.exercise_id}`} className="flex items-center justify-between rounded-md border border-red-500/30 bg-red-500/10 px-2 py-1">
                  <span>{item.exercise_id}</span>
                  <span className="inline-flex items-center gap-2">
                    <span className="status-dot status-dot--green" />
                    {item.pr_delta >= 0 ? "+" : ""}{item.pr_delta} kg
                  </span>
                </p>
              ))}
            </div>
          ) : (
            <p className="text-xs text-zinc-500">No PR highlights yet</p>
          )}
          <p className="telemetry-meta">Window: {dashboard?.window.limit_weeks ?? 0} weeks</p>
        </div>

        <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Readiness Mix</p>
          <div className="h-3 w-full overflow-hidden rounded-full border border-white/10 bg-zinc-900/80 flex">
            <div className="bg-zinc-300/85" style={{ width: `${mixHigh}%` }} />
            <div className="bg-zinc-500/85" style={{ width: `${mixMedium}%` }} />
            <div className="bg-zinc-700/85" style={{ width: `${mixLow}%` }} />
          </div>
          <p className="telemetry-meta">High {mixHigh}% · Medium {mixMedium}% · Low {mixLow}%</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        {measurementTrends.length > 0 ? (
          measurementTrends.map((trend) => (
            <div key={`measurement-${trend.name}-${trend.unit}`} className="main-card main-card--module spacing-grid spacing-grid--tight">
              <p className="telemetry-kicker">Measurement Trend</p>
              <p className="telemetry-value">{trend.name}</p>
              <div className="flex items-end gap-1 h-16">
                {trend.points.map((point) => {
                  const values = trend.points.map((item) => item.value);
                  const min = Math.min(...values);
                  const max = Math.max(...values);
                  const spread = Math.max(0.1, max - min);
                  const normalized = 25 + ((point.value - min) / spread) * 75;
                  return (
                    <div
                      key={`${trend.name}-${point.measured_on}`}
                      className="flex-1 rounded-sm bg-zinc-700/70"
                      style={{ height: `${Math.round(normalized)}%` }}
                      title={`${point.measured_on}: ${point.value} ${trend.unit}`}
                    />
                  );
                })}
              </div>
              <p className="telemetry-meta">Latest {trend.latest_value} {trend.unit} ({trend.delta >= 0 ? "+" : ""}{trend.delta})</p>
            </div>
          ))
        ) : (
          <div className="main-card main-card--module lg:col-span-3">
            <p className="text-xs text-zinc-500">No body measurement trend data</p>
          </div>
        )}
      </div>

      <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Volume Heat Map</p>
        {heatmap && heatmap.weeks.length > 0 ? (
          <div className="space-y-2">
            {heatmap.weeks.map((week) => (
              <div key={`heat-${week.week_start}`} className="grid grid-cols-[90px_repeat(7,minmax(0,1fr))] gap-1 text-[10px]">
                <p className="text-zinc-500">{week.week_start}</p>
                {week.days.map((day) => {
                  const ratio = Math.max(0, Math.min(1, day.volume / heatmapMax));
                  const alpha = 0.1 + ratio * 0.8;
                  return (
                    <div
                      key={`${week.week_start}-${day.day_index}`}
                      className="rounded border border-white/10 px-1 py-1 text-center text-zinc-200"
                      style={{ backgroundColor: `rgba(220, 38, 38, ${alpha.toFixed(2)})` }}
                      title={`Day ${day.day_index + 1}: ${day.volume} volume (${day.sets} sets)`}
                    >
                      {day.volume > 0 ? Math.round(day.volume) : "-"}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-zinc-500">No volume heat map data</p>
        )}
      </div>

      {trendStatus ? <p className="text-xs text-zinc-500">{trendStatus}</p> : null}
    </div>
  );
}
