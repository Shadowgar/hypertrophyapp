"use client";

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Disclosure } from "@/components/ui/disclosure";
import { UiIcon } from "@/components/ui/icons";
import {
  api,
  type CoachingRecommendationTimelineEntry,
  getProgramDisplayName,
  type HistoryAnalyticsResponse,
  type HistoryCalendarResponse,
  type HistoryDayDetailResponse,
} from "@/lib/api";
import { kgToLbs } from "@/lib/weight";

function formatTimestamp(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return iso;
  }
  return parsed.toLocaleString();
}

function formatSignedDelta(value: number): string {
  return `${value >= 0 ? "+" : ""}${value}`;
}

function formatPlannedSuffix(plannedSets?: number | null, delta?: number | null): string {
  let text = "";
  if (typeof plannedSets === "number") {
    text += ` / ${plannedSets} planned`;
  }
  if (typeof delta === "number") {
    text += ` (${formatSignedDelta(delta)})`;
  }
  return text;
}

type CalendarViewMode = "week" | "month";
type CalendarCompletionFilter = "all" | "completed" | "missed" | "pr_days";

function calendarRangeForMode(mode: CalendarViewMode, windowOffset: number): { startDate: string; endDate: string } {
  const windowDays = mode === "week" ? 7 : 28;
  const end = new Date();
  end.setDate(end.getDate() - (Math.max(0, windowOffset) * windowDays));
  const start = new Date(end);
  start.setDate(end.getDate() - (windowDays - 1));
  return {
    startDate: start.toISOString().slice(0, 10),
    endDate: end.toISOString().slice(0, 10),
  };
}

function uniqueSorted(values: string[]): string[] {
  return Array.from(new Set(values.filter((value) => value.trim().length > 0))).sort((a, b) => a.localeCompare(b));
}

function filterCalendarDays(
  days: HistoryCalendarResponse["days"],
  completion: CalendarCompletionFilter,
  program: string,
  muscle: string,
): HistoryCalendarResponse["days"] {
  return days.filter((day) => {
    if (completion === "completed" && !day.completed) {
      return false;
    }
    if (completion === "missed" && day.completed) {
      return false;
    }
    if (completion === "pr_days" && day.pr_count <= 0) {
      return false;
    }
    if (program !== "all" && !day.program_ids.includes(program)) {
      return false;
    }
    if (muscle !== "all" && !day.muscles.includes(muscle)) {
      return false;
    }
    return true;
  });
}

function dayClassName(isSelected: boolean, isCompleted: boolean): string {
  if (isSelected) {
    return "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white";
  }
  if (isCompleted) {
    return "border-red-500/40 bg-red-500/10 text-zinc-100";
  }
  return "border-white/10 bg-zinc-900/70 text-zinc-400";
}

function calendarTrendMetrics(days: HistoryCalendarResponse["days"]): {
  completionPct: number;
  recent7: number;
  previous7: number;
  weekdayChampion: string;
  prDays: number;
} {
  if (days.length === 0) {
    return { completionPct: 0, recent7: 0, previous7: 0, weekdayChampion: "n/a", prDays: 0 };
  }

  const ordered = [...days].sort((a, b) => a.date.localeCompare(b.date));
  const completedTotal = ordered.filter((day) => day.completed).length;
  const completionPct = Math.round((completedTotal / Math.max(1, ordered.length)) * 100);

  const recent7 = ordered.slice(-7).filter((day) => day.completed).length;
  const previous7 = ordered.slice(-14, -7).filter((day) => day.completed).length;
  const prDays = ordered.filter((day) => day.pr_count > 0).length;

  const weekdayCounts: Record<number, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0 };
  for (const day of ordered) {
    if (day.completed) {
      weekdayCounts[day.weekday] += 1;
    }
  }

  let championWeekday = 0;
  let championValue = -1;
  for (let weekday = 0; weekday < 7; weekday += 1) {
    const value = weekdayCounts[weekday] ?? 0;
    if (value > championValue) {
      championWeekday = weekday;
      championValue = value;
    }
  }
  const weekdayLabel = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][championWeekday] ?? "Mon";
  return { completionPct, recent7, previous7, weekdayChampion: weekdayLabel, prDays };
}

function previousSameWeekdayDay(
  days: HistoryCalendarResponse["days"],
  selectedDay: string | null,
): HistoryCalendarResponse["days"][number] | null {
  if (!selectedDay) {
    return null;
  }
  const selected = days.find((day) => day.date === selectedDay);
  if (!selected) {
    return null;
  }

  const ordered = [...days]
    .filter((day) => day.date < selected.date && day.weekday === selected.weekday)
    .sort((a, b) => b.date.localeCompare(a.date));
  return ordered.length > 0 ? ordered[0] : null;
}

function roundOneDecimal(value: number): number {
  return Math.round(value * 10) / 10;
}

function resolveBodyweightSignal(points: HistoryAnalyticsResponse["bodyweight_trend"]): {
  label: string;
  detail: string;
} {
  if (points.length < 2) {
    return { label: "No trend", detail: "Need at least two check-ins." };
  }
  const first = points[0].body_weight;
  const last = points.at(-1)?.body_weight ?? first;
  const firstLbs = kgToLbs(first);
  const lastLbs = kgToLbs(last);
  const deltaLbs = roundOneDecimal(lastLbs - firstLbs);
  return {
    label: `${deltaLbs >= 0 ? "+" : ""}${deltaLbs} lbs`,
    detail: `${firstLbs} lbs to ${lastLbs} lbs across the visible window`,
  };
}

function resolveCoachQueue(entries: CoachingRecommendationTimelineEntry[]): {
  pending: number;
  latestType: string | null;
  latestRationale: string | null;
} {
  const pending = entries.filter((entry) => entry.status !== "applied").length;
  const latest = entries[0];
  return {
    pending,
    latestType: latest?.recommendation_type ?? null,
    latestRationale: latest?.rationale?.trim() || null,
  };
}

function HistoryCalendarPanel() {
  const [calendar, setCalendar] = useState<HistoryCalendarResponse | null>(null);
  const [calendarStatus, setCalendarStatus] = useState("Loading calendar history...");
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [dayDetail, setDayDetail] = useState<HistoryDayDetailResponse | null>(null);
  const [dayDetailStatus, setDayDetailStatus] = useState("Select a day to inspect performed exercises.");
  const [viewMode, setViewMode] = useState<CalendarViewMode>("month");
  const [windowOffset, setWindowOffset] = useState(0);
  const [calendarReloadCount, setCalendarReloadCount] = useState(0);
  const [completionFilter, setCompletionFilter] = useState<CalendarCompletionFilter>("all");
  const [selectedProgram, setSelectedProgram] = useState("all");
  const [selectedMuscle, setSelectedMuscle] = useState("all");

  const allDays = useMemo(() => calendar?.days ?? [], [calendar]);
  const programOptions = useMemo(
    () => uniqueSorted(allDays.flatMap((day) => day.program_ids)),
    [allDays],
  );
  const muscleOptions = useMemo(
    () => uniqueSorted(allDays.flatMap((day) => day.muscles)),
    [allDays],
  );
  const filteredDays = useMemo(
    () => filterCalendarDays(allDays, completionFilter, selectedProgram, selectedMuscle),
    [allDays, completionFilter, selectedProgram, selectedMuscle],
  );
  const trends = useMemo(() => calendarTrendMetrics(allDays), [allDays]);
  const selectedCalendarDay = useMemo(
    () => allDays.find((day) => day.date === selectedDay) ?? null,
    [allDays, selectedDay],
  );
  const previousSameWeekday = useMemo(() => previousSameWeekdayDay(filteredDays, selectedDay), [filteredDays, selectedDay]);
  const weekdayComparison = useMemo(() => {
    if (!selectedCalendarDay || !previousSameWeekday) {
      return null;
    }
    return {
      setDelta: selectedCalendarDay.set_count - previousSameWeekday.set_count,
      volumeDelta: roundOneDecimal(selectedCalendarDay.total_volume - previousSameWeekday.total_volume),
      prDelta: selectedCalendarDay.pr_count - previousSameWeekday.pr_count,
    };
  }, [selectedCalendarDay, previousSameWeekday]);

  useEffect(() => {
    setWindowOffset(0);
  }, [viewMode]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const { startDate, endDate } = calendarRangeForMode(viewMode, windowOffset);
        const payload = await api.getHistoryCalendar(startDate, endDate);
        if (!mounted) {
          return;
        }
        if (!Array.isArray(payload.days) || payload.days.length === 0) {
          setCalendar(null);
          setCalendarStatus("No calendar history yet.");
          setSelectedDay(null);
          setDayDetail(null);
          setDayDetailStatus("Select a day to inspect performed exercises.");
          return;
        }
        setCalendar(payload);
        setCalendarStatus("");
        const latestCompleted = [...payload.days].reverse().find((day) => day.completed);
        setSelectedDay(latestCompleted?.date ?? payload.days.at(-1)?.date ?? null);
      } catch {
        if (!mounted) {
          return;
        }
        setCalendar(null);
        setCalendarStatus("Unable to load calendar history.");
        setSelectedDay(null);
        setDayDetail(null);
        setDayDetailStatus("Select a day to inspect performed exercises.");
      }
    })();

    return () => {
      mounted = false;
    };
  }, [viewMode, windowOffset, calendarReloadCount]);

  useEffect(() => {
    if (selectedProgram !== "all" && !programOptions.includes(selectedProgram)) {
      setSelectedProgram("all");
    }
  }, [programOptions, selectedProgram]);

  useEffect(() => {
    if (selectedMuscle !== "all" && !muscleOptions.includes(selectedMuscle)) {
      setSelectedMuscle("all");
    }
  }, [muscleOptions, selectedMuscle]);

  async function loadDayDetail(day: string) {
    setSelectedDay(day);
    setDayDetailStatus("Loading day detail...");
    try {
      const detail = await api.getHistoryDayDetail(day);
      setDayDetail(detail);
      const plannedSetCount = detail.totals.planned_set_count ?? 0;
      if (detail.totals.set_count === 0 && plannedSetCount > 0) {
        setDayDetailStatus(`No logged sets on this day. Planned sets: ${plannedSetCount}.`);
        return;
      }
      if (detail.totals.set_count === 0) {
        setDayDetailStatus("No logged sets on this day.");
        return;
      }
      setDayDetailStatus("");
    } catch {
      setDayDetail(null);
      setDayDetailStatus("Unable to load day detail.");
    }
  }

  return (
    <>
      <div className="main-card main-card--module spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Training Calendar</p>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-4">
          <div className="space-y-1">
            <p className="ui-meta">View</p>
            <div className="grid grid-cols-2 gap-1">
              <Button type="button" variant={viewMode === "week" ? "default" : "secondary"} onClick={() => setViewMode("week")}>Week</Button>
              <Button type="button" variant={viewMode === "month" ? "default" : "secondary"} onClick={() => setViewMode("month")}>Month</Button>
            </div>
          </div>
          <div className="space-y-1">
            <p className="ui-meta">Completion</p>
            <select
              className="ui-select"
              value={completionFilter}
              onChange={(event) => setCompletionFilter(event.target.value as CalendarCompletionFilter)}
              aria-label="Completion filter"
            >
              <option value="all">All Days</option>
              <option value="completed">Completed Only</option>
              <option value="missed">Missed Only</option>
              <option value="pr_days">PR Days</option>
            </select>
          </div>
          <div className="space-y-1">
            <p className="ui-meta">Program</p>
            <select
              className="ui-select"
              value={selectedProgram}
              onChange={(event) => setSelectedProgram(event.target.value)}
              aria-label="Program filter"
            >
              <option value="all">All Programs</option>
              {programOptions.map((program) => (
                <option key={`program-filter-${program}`} value={program}>
                  {program}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1">
            <p className="ui-meta">Muscle</p>
            <select
              className="ui-select"
              value={selectedMuscle}
              onChange={(event) => setSelectedMuscle(event.target.value)}
              aria-label="Muscle filter"
            >
              <option value="all">All Muscles</option>
              {muscleOptions.map((muscle) => (
                <option key={`muscle-filter-${muscle}`} value={muscle}>
                  {muscle}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
          <Button type="button" variant="secondary" onClick={() => setWindowOffset((value) => value + 1)}>
            Previous Window
          </Button>
          <Button type="button" variant="secondary" onClick={() => setWindowOffset((value) => Math.max(0, value - 1))} disabled={windowOffset === 0}>
            Next Window
          </Button>
          <p className="telemetry-meta flex items-center justify-center rounded-md border border-white/10 bg-zinc-900/70 px-2 py-2">
            Offset {windowOffset}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
          <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">
            <p className="telemetry-kicker">Completion</p>
            <p className="telemetry-value">{trends.completionPct}%</p>
          </div>
          <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">
            <p className="telemetry-kicker">Recent 7d</p>
            <p className="telemetry-value">{trends.recent7} days</p>
          </div>
          <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">
            <p className="telemetry-kicker">Previous 7d</p>
            <p className="telemetry-value">{trends.previous7} days</p>
          </div>
          <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">
            <p className="telemetry-kicker">Best Weekday</p>
            <p className="telemetry-value">{trends.weekdayChampion}</p>
          </div>
          <div className="rounded-md border border-white/10 bg-zinc-900/70 p-2">
            <p className="telemetry-kicker">PR Days</p>
            <p className="telemetry-value">{trends.prDays}</p>
          </div>
        </div>

        {calendar ? (
          <>
            <p className="telemetry-meta">
              Window {calendar.start_date} to {calendar.end_date} ·
              {" "}
              Active days {calendar.active_days} · Current streak {calendar.current_streak_days} · Longest streak {calendar.longest_streak_days}
            </p>
            <div className="grid grid-cols-7 gap-1">
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((wd) => (
                <div key={`header-${wd}`} className="py-1 text-center text-[10px] font-medium uppercase tracking-wide text-zinc-500">{wd}</div>
              ))}
              {filteredDays.map((day) => {
                const dateLabel = day.date.slice(8, 10);
                const isSelected = selectedDay === day.date;
                const isCompleted = day.completed;
                return (
                  <button
                    key={`calendar-day-${day.date}`}
                    type="button"
                    onClick={() => void loadDayDetail(day.date)}
                    className={`rounded border px-2 py-2 text-xs transition-colors ${dayClassName(isSelected, isCompleted)}`}
                    title={`${day.date}: ${day.set_count} sets, ${day.exercise_count} exercises, ${day.total_volume} volume, ${day.pr_count} PRs`}
                  >
                    <div>{dateLabel}</div>
                    <div>{day.set_count}</div>
                    {day.pr_count > 0 ? <div className="text-[10px] text-red-200">PR {day.pr_count}</div> : null}
                  </button>
                );
              })}
            </div>
            <div className="flex items-center gap-4 text-[10px] text-zinc-500">
              <span className="flex items-center gap-1"><span className="inline-block h-2.5 w-2.5 rounded border border-red-500/40 bg-red-500/10" /> Completed</span>
              <span className="flex items-center gap-1"><span className="inline-block h-2.5 w-2.5 rounded border border-white/10 bg-zinc-900/70" /> Missed</span>
              <span className="flex items-center gap-1"><span className="inline-block h-2.5 w-2.5 rounded border border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)]" /> Selected</span>
            </div>
            {filteredDays.length === 0 ? <p className="text-xs text-zinc-500">No days match current filters.</p> : null}
          </>
        ) : (
          <div className="space-y-2">
            <p className="text-xs text-zinc-500">{calendarStatus}</p>
            {calendarStatus === "No calendar history yet." ? (
              <p className="text-xs text-zinc-400">Generate your first week from Week Plan, then log workouts to see history here.</p>
            ) : null}
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {(calendarStatus === "No calendar history yet." || calendarStatus === "Unable to load calendar history.") ? (
                <Button type="button" variant="secondary" onClick={() => setCalendarReloadCount((value) => value + 1)} aria-label="Retry Calendar Load">
                  Retry Calendar Load
                </Button>
              ) : null}
              <a
                className="inline-flex items-center justify-center rounded-md border border-white/10 bg-zinc-900/70 px-3 py-2 text-xs text-zinc-100 hover:bg-zinc-900"
                href="/week"
              >
                Open Week Plan
              </a>
            </div>
          </div>
        )}
      </div>

      <div className="main-card main-card--module spacing-grid spacing-grid--tight">
        <p className="telemetry-kicker">Selected Day Detail</p>
        <div>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              if (previousSameWeekday) {
                void loadDayDetail(previousSameWeekday.date);
              }
            }}
            disabled={!previousSameWeekday}
          >
            Jump To Previous Same Weekday
          </Button>
          <p className="telemetry-meta mt-1">
            {previousSameWeekday ? `Previous match: ${previousSameWeekday.date}` : "No earlier same-weekday match in current filtered view."}
          </p>
          {weekdayComparison && selectedCalendarDay && previousSameWeekday ? (
            <div className="mt-2 rounded-md border border-white/10 bg-zinc-900/70 p-2">
              <p className="telemetry-kicker">Same-Weekday Comparison</p>
              <p className="telemetry-meta">
                {selectedCalendarDay.date} vs {previousSameWeekday.date}
              </p>
              <div className="mt-2 grid grid-cols-1 gap-1 md:grid-cols-3">
                <p className="rounded border border-white/10 bg-zinc-900/80 px-2 py-1 text-xs text-zinc-200">
                  Sets {formatSignedDelta(weekdayComparison.setDelta)}
                </p>
                <p className="rounded border border-white/10 bg-zinc-900/80 px-2 py-1 text-xs text-zinc-200">
                  Volume {formatSignedDelta(weekdayComparison.volumeDelta)}
                </p>
                <p className="rounded border border-white/10 bg-zinc-900/80 px-2 py-1 text-xs text-zinc-200">
                  PR Days {formatSignedDelta(weekdayComparison.prDelta)}
                </p>
              </div>
            </div>
          ) : null}
        </div>
        {dayDetail && ((dayDetail.totals.set_count > 0) || ((dayDetail.totals.planned_set_count ?? 0) > 0)) ? (
          <div className="space-y-2 text-xs text-zinc-200">
            {dayDetailStatus ? <p className="text-xs text-zinc-500">{dayDetailStatus}</p> : null}
            <p className="telemetry-meta">
              {dayDetail.date} · {dayDetail.totals.set_count} sets
              {formatPlannedSuffix(dayDetail.totals.planned_set_count, dayDetail.totals.set_delta)}
              {` · ${dayDetail.totals.exercise_count} exercises · ${dayDetail.totals.total_volume} volume`}
            </p>
            {dayDetail.workouts.map((workout) => (
              <div key={`day-workout-${workout.workout_id}`} className="rounded-md border border-white/10 bg-zinc-900/70 p-2">
                <p className="font-medium">Workout {workout.workout_id}</p>
                {workout.program_id ? <p className="telemetry-meta">Program: {workout.program_id}</p> : null}
                <p className="telemetry-meta">
                  {workout.total_sets} sets
                  {formatPlannedSuffix(workout.planned_sets_total, workout.set_delta)}
                  {` · ${workout.total_volume} volume`}
                </p>
                <div className="mt-1 space-y-1">
                  {workout.exercises.map((exercise) => (
                    <div key={`day-exercise-${workout.workout_id}-${exercise.exercise_id}-${exercise.primary_exercise_id ?? "none"}`} className="rounded border border-white/10 px-2 py-1">
                      <p>
                        {exercise.planned_name || exercise.primary_exercise_id || exercise.exercise_id}
                        {exercise.primary_exercise_id && exercise.primary_exercise_id !== exercise.exercise_id
                          ? ` (performed as ${exercise.exercise_id})`
                          : ""}
                      </p>
                      {Array.isArray(exercise.primary_muscles) && exercise.primary_muscles.length > 0 ? (
                        <p className="telemetry-meta">Muscles: {exercise.primary_muscles.join(", ")}</p>
                      ) : null}
                      <p className="telemetry-meta">
                        {exercise.total_sets} sets
                        {formatPlannedSuffix(exercise.planned_sets, exercise.set_delta)}
                        {` · ${exercise.total_volume} volume`}
                      </p>
                      <p className="telemetry-meta">
                        {exercise.sets.map((entry) => `#${entry.set_index} ${entry.reps}x${entry.weight}`).join(" · ")}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-xs text-zinc-500">{dayDetailStatus}</p>
            <a
              className="inline-flex items-center justify-center rounded-md border border-white/10 bg-zinc-900/70 px-3 py-2 text-xs text-zinc-100 hover:bg-zinc-900"
              href="/today"
            >
              Open Today Workout
            </a>
          </div>
        )}
      </div>
    </>
  );
}

export default function HistoryPage() {
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
  const coachQueue = useMemo(() => resolveCoachQueue(timelineEntries), [timelineEntries]);
  const bodyweightSignal = useMemo(() => resolveBodyweightSignal(dashboard?.bodyweight_trend ?? []), [dashboard]);
  const strengthLead = useMemo(() => {
    if (!primaryStrengthTrend) {
      return { hasData: false, label: "No lift trend", detail: "Log more repeated exposures." };
    }
    return {
      hasData: true,
      label: primaryStrengthTrend.exercise_id,
      detail: `PR ${kgToLbs(primaryStrengthTrend.pr_weight)} lbs (${primaryStrengthTrend.pr_delta >= 0 ? "+" : "-"}${kgToLbs(Math.abs(primaryStrengthTrend.pr_delta))} lbs)`,
    };
  }, [primaryStrengthTrend]);

  const heatmap = dashboard?.volume_heatmap;
  const heatmapMax = Math.max(heatmap?.max_volume ?? 0, 1);

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
      {/* History JSON output removed for cleaner UX */}

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1.3fr_1fr_1fr_1fr]">
        <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Progress Overview</p>
          <p className="telemetry-value">{prHighlights.length} PR highlights</p>
          <p className="telemetry-meta">
            {adherencePct}% adherence · {prHighlights.length} PR highlights · {coachQueue.pending} pending coach decisions
          </p>
          {coachQueue.latestRationale ? <p className="text-xs text-zinc-200">Latest rationale: {coachQueue.latestRationale}</p> : null}
        </div>

        <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Strength Lead</p>
          <p className="telemetry-value">{strengthLead.label}</p>
          <p className="telemetry-meta">{strengthLead.detail}</p>
        </div>

        <div className="main-card main-card--module spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Bodyweight Drift</p>
          <p className="telemetry-value">{bodyweightSignal.label}</p>
          <p className="telemetry-meta">{bodyweightSignal.detail}</p>
        </div>

        <div className="main-card main-card--shell spacing-grid spacing-grid--tight">
          <p className="telemetry-kicker">Upcoming Changes</p>
          <p className="telemetry-value">{coachQueue.pending} pending</p>
          <p className="telemetry-meta">Latest type: {coachQueue.latestType ?? "none"}</p>
        </div>
      </div>

      <HistoryCalendarPanel />

      <Disclosure title="Coaching Decision Timeline" badge={timelineEntries.length > 0 ? `${timelineEntries.length} decisions` : null} defaultOpen={false}>
        {timelineEntries.length > 0 ? (
          <div className="space-y-2">
            {timelineEntries.map((entry) => (
              <div key={entry.recommendation_id} className="rounded-md border border-white/10 bg-zinc-900/60 p-2 text-xs text-zinc-200">
                <p className="flex items-center justify-between gap-2">
                  <span className="font-medium">{entry.recommendation_type}</span>
                  <span className="telemetry-meta uppercase">{entry.status}</span>
                </p>
                <p className="telemetry-meta">
                  {getProgramDisplayName({ id: entry.template_id })} · {entry.current_phase} → {entry.recommended_phase}
                </p>
                <p className="telemetry-meta">Progression: {entry.progression_action}</p>
                <p>{entry.rationale}</p>
                {entry.focus_muscles.length > 0 ? <p>Focus: {entry.focus_muscles.join(", ")}</p> : null}
                <p className="telemetry-meta">{formatTimestamp(entry.created_at)}{entry.applied_at ? ` · Applied ${formatTimestamp(entry.applied_at)}` : ""}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-zinc-500">{timelineStatus}</p>
        )}
      </Disclosure>

      <Disclosure title="Bodyweight Trend" badge={bodyweightSignal.label} defaultOpen={false}>
        <div className="space-y-2">
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
                    title={`Week ${index + 1}: ${kgToLbs(value)} lbs`}
                  />
                );
              })
            ) : (
              <div className="text-xs text-zinc-500">No trend data</div>
            )}
          </div>
          <div className="flex items-center justify-between text-xs text-zinc-500">
            <span>lbs</span>
            <span>Last {Math.max(weeklyCheckins.length, 0)} check-ins</span>
          </div>
          <p className="text-xs text-zinc-400">{bodyweightSignal.detail}</p>
        </div>
      </Disclosure>

      <Disclosure title="Strength Trend" badge={strengthLead.label} defaultOpen={false}>
        {primaryStrengthTrend ? (
          <div className="space-y-2">
            <div className="flex items-end gap-1 h-16">
              {primaryStrengthTrend.points.map((point) => {
                const normalized = 25 + ((point.max_weight - strengthBounds.min) / strengthBounds.spread) * 75;
                return (
                  <div
                    key={`${primaryStrengthTrend.exercise_id}-${point.week_start}`}
                    className="flex-1 rounded-sm bg-zinc-700/70"
                    style={{ height: `${Math.round(normalized)}%` }}
                    title={`${point.week_start}: ${kgToLbs(point.max_weight)} lbs`}
                  />
                );
              })}
            </div>
            <div className="flex items-center justify-between text-xs text-zinc-500">
              <span>lbs</span>
              <span>{strengthLead.detail}</span>
            </div>
          </div>
        ) : (
          <p className="text-xs text-zinc-500">No strength trend data</p>
        )}
      </Disclosure>

      <Disclosure title="PR Highlights" badge={prHighlights.length > 0 ? `${prHighlights.length} PRs` : null} defaultOpen={false}>
        {prHighlights.length > 0 ? (
          <div className="space-y-1 text-xs text-zinc-200">
            {prHighlights.map((item) => (
              <p key={`pr-${item.exercise_id}`} className="flex items-center justify-between rounded-md border border-red-500/30 bg-red-500/10 px-2 py-1">
                <span>{item.exercise_id}</span>
                <span className="inline-flex items-center gap-2">
                  <span className="status-dot status-dot--green" />
                  {item.pr_delta >= 0 ? "+" : "-"}{kgToLbs(Math.abs(item.pr_delta))} lbs
                </span>
              </p>
            ))}
          </div>
        ) : (
          <p className="text-xs text-zinc-500">No PR highlights yet</p>
        )}
      </Disclosure>

      <Disclosure title="Readiness Mix" badge={`${mixHigh}% high`} defaultOpen={false}>
        <div className="space-y-2">
          <div className="h-3 w-full overflow-hidden rounded-full border border-white/10 bg-zinc-900/80 flex">
            <div className="bg-zinc-300/85" style={{ width: `${mixHigh}%` }} />
            <div className="bg-zinc-500/85" style={{ width: `${mixMedium}%` }} />
            <div className="bg-zinc-700/85" style={{ width: `${mixLow}%` }} />
          </div>
          <p className="text-xs text-zinc-400">High {mixHigh}% · Medium {mixMedium}% · Low {mixLow}%</p>
        </div>
      </Disclosure>

      {measurementTrends.length > 0 ? (
        <Disclosure title="Body Measurements" badge={`${measurementTrends.length} tracked`} defaultOpen={false}>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            {measurementTrends.map((trend) => (
              <div key={`measurement-${trend.name}-${trend.unit}`} className="space-y-2">
                <p className="text-sm font-medium text-zinc-200">{trend.name}</p>
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
                <p className="text-xs text-zinc-400">Latest {trend.latest_value} {trend.unit} ({trend.delta >= 0 ? "+" : ""}{trend.delta})</p>
              </div>
            ))}
          </div>
        </Disclosure>
      ) : null}

      <Disclosure title="Volume Heat Map" defaultOpen={false}>
        {heatmap && heatmap.weeks.length > 0 ? (
          <div className="space-y-2">
            <div className="grid grid-cols-[90px_repeat(7,minmax(0,1fr))] gap-1 text-[10px]">
              <p className="text-zinc-500" />
              {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((wd) => (
                <p key={`heat-header-${wd}`} className="text-center text-zinc-500">{wd}</p>
              ))}
            </div>
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
      </Disclosure>

      {trendStatus ? <p className="text-xs text-zinc-500">{trendStatus}</p> : null}
    </div>
  );
}
