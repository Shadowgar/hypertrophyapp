import { API_BASE_URL } from "@/lib/env";

export type WorkoutExercise = {
  id: string;
  primary_exercise_id?: string;
  name: string;
  sets: number;
  rep_range: [number, number];
  recommended_working_weight: number;
  substitution_candidates?: string[];
  notes?: string | null;
  completed_sets?: number;
  live_recommendation?: WorkoutLiveRecommendation;
  video?: {
    youtube_url?: string;
  } | null;
};

export type WorkoutLiveRecommendation = {
  completed_sets: number;
  remaining_sets: number;
  recommended_reps_min: number;
  recommended_reps_max: number;
  recommended_weight: number;
  guidance: string;
};

export type WorkoutSession = {
  session_id: string;
  title: string;
  date: string;
  resume?: boolean;
  mesocycle?: {
    week_index: number;
    trigger_weeks_base: number;
    trigger_weeks_effective: number;
    is_deload_week: boolean;
    deload_reason: string;
  };
  deload?: {
    active: boolean;
    set_reduction_pct: number;
    load_reduction_pct: number;
    reason: string;
  };
  exercises: WorkoutExercise[];
};

export type WorkoutProgress = {
  workout_id: string;
  completed_total: number;
  planned_total: number;
  percent_complete: number;
  exercises: Array<{
    exercise_id: string;
    planned_sets: number;
    completed_sets: number;
  }>;
};

export type Profile = {
  email: string;
  name: string;
  age: number;
  weight: number;
  gender: string;
  split_preference: string;
  training_location?: string | null;
  equipment_profile: string[];
  days_available: number;
  nutrition_phase: string;
  calories: number;
  protein: number;
  fat: number;
  carbs: number;
  selected_program_id?: string | null;
};

export type ProgramRecommendation = {
  current_program_id: string;
  recommended_program_id: string;
  reason: string;
  compatible_program_ids: string[];
  generated_at: string;
};

export type ProgramTemplateOption = {
  id: string;
  slug?: string;
  name?: string;
  description?: string;
};

export function getProgramDisplayName(program: ProgramTemplateOption): string {
  const preferred = program.name?.trim();
  if (preferred) {
    return preferred;
  }
  const source = program.slug?.trim() || program.id;
  const suffixMatch = /_v(\d+)$/i.exec(source);
  const withoutSuffix = suffixMatch ? source.slice(0, -suffixMatch[0].length) : source;
  const spaced = withoutSuffix.replaceAll("_", " ").replaceAll("-", " ");
  const normalized = suffixMatch ? `${spaced} v${suffixMatch[1]}` : spaced;
  return normalized
    .trim()
    .split(/\s+/)
    .map((part) => (part.length ? part[0].toUpperCase() + part.slice(1) : part))
    .join(" ");
}

export type ProgramSwitchResponse = {
  status: "confirmation_required" | "switched" | "unchanged";
  current_program_id: string;
  target_program_id: string;
  recommended_program_id: string;
  reason: string;
  requires_confirmation: boolean;
  applied: boolean;
};

export type GuideProgram = {
  id: string;
  name: string;
  split: string;
  days_supported: number[];
  description: string;
};

export type GuideProgramDetail = {
  id: string;
  name: string;
  description: string;
  split: string;
  days_supported: number[];
  days: Array<{
    day_index: number;
    day_name: string;
    exercise_count: number;
    first_exercise_id?: string | null;
  }>;
};

export type GuideDayDetail = {
  program_id: string;
  day_index: number;
  day_name: string;
  exercises: Array<{
    id: string;
    primary_exercise_id?: string | null;
    name: string;
    notes?: string | null;
    video_youtube_url?: string | null;
  }>;
};

export type GuideExerciseDetail = {
  program_id: string;
  exercise: {
    id: string;
    primary_exercise_id?: string | null;
    name: string;
    notes?: string | null;
    video_youtube_url?: string | null;
  };
};

export type WorkoutSetFeedback = {
  id: string;
  primary_exercise_id: string;
  exercise_id: string;
  set_index: number;
  reps: number;
  weight: number;
  planned_reps_min: number;
  planned_reps_max: number;
  planned_weight: number;
  rep_delta: number;
  weight_delta: number;
  next_working_weight: number;
  guidance: string;
  live_recommendation: WorkoutLiveRecommendation;
  created_at: string;
};

export type WorkoutExerciseSummary = {
  exercise_id: string;
  primary_exercise_id?: string | null;
  name: string;
  planned_sets: number;
  planned_reps_min: number;
  planned_reps_max: number;
  planned_weight: number;
  performed_sets: number;
  average_performed_reps: number;
  average_performed_weight: number;
  completion_pct: number;
  rep_delta: number;
  weight_delta: number;
  next_working_weight: number;
  guidance: string;
};

export type WorkoutSummary = {
  workout_id: string;
  completed_total: number;
  planned_total: number;
  percent_complete: number;
  overall_guidance: string;
  exercises: WorkoutExerciseSummary[];
};

export type WeeklyCheckinPayload = {
  week_start: string;
  body_weight: number;
  adherence_score: number;
  notes?: string;
};

export type HistoryWeeklyCheckinEntry = {
  week_start: string;
  body_weight: number;
  adherence_score: number;
  notes?: string | null;
  created_at: string;
};

export type HistoryWeeklyCheckinResponse = {
  entries: HistoryWeeklyCheckinEntry[];
};

export type HistoryBodyweightPoint = {
  week_start: string;
  body_weight: number;
};

export type HistoryStrengthTrendPoint = {
  week_start: string;
  max_weight: number;
  avg_est_1rm: number;
};

export type HistoryStrengthTrend = {
  exercise_id: string;
  total_sets: number;
  latest_weight: number;
  pr_weight: number;
  pr_delta: number;
  points: HistoryStrengthTrendPoint[];
};

export type HistoryPrHighlight = {
  exercise_id: string;
  pr_weight: number;
  previous_pr_weight: number;
  pr_delta: number;
};

export type HistoryBodyMeasurementTrend = {
  name: string;
  unit: string;
  latest_value: number;
  delta: number;
  points: Array<{
    measured_on: string;
    value: number;
  }>;
};

export type HistoryHeatmapCell = {
  day_index: number;
  sets: number;
  volume: number;
};

export type HistoryVolumeHeatmap = {
  max_volume: number;
  weeks: Array<{
    week_start: string;
    days: HistoryHeatmapCell[];
  }>;
};

export type HistoryAnalyticsResponse = {
  window: {
    start_date: string;
    end_date: string;
    limit_weeks: number;
    checkin_limit: number;
  };
  checkins: HistoryWeeklyCheckinEntry[];
  adherence: {
    average_score: number;
    average_pct: number;
    latest_score: number;
    trend_delta: number;
    high_readiness_streak: number;
  };
  bodyweight_trend: HistoryBodyweightPoint[];
  strength_trends: HistoryStrengthTrend[];
  pr_highlights: HistoryPrHighlight[];
  body_measurement_trends: HistoryBodyMeasurementTrend[];
  volume_heatmap: HistoryVolumeHeatmap;
};

export type WeeklyExerciseFault = {
  primary_exercise_id: string;
  exercise_id: string;
  name: string;
  planned_sets: number;
  completed_sets: number;
  completion_pct: number;
  target_reps_min: number;
  target_reps_max: number;
  average_performed_reps: number;
  target_weight: number;
  average_performed_weight: number;
  guidance: string;
  fault_score: number;
  fault_level: string;
  fault_reasons: string[];
};

export type WeeklyPerformanceSummary = {
  previous_week_start: string;
  previous_week_end: string;
  planned_sets_total: number;
  completed_sets_total: number;
  completion_pct: number;
  faulty_exercise_count: number;
  exercise_faults: WeeklyExerciseFault[];
};

export type WeeklyReviewStatus = {
  today_is_sunday: boolean;
  review_required: boolean;
  current_week_start: string;
  week_start: string;
  previous_week_start: string;
  previous_week_end: string;
  existing_review_submitted: boolean;
  previous_week_summary?: WeeklyPerformanceSummary | null;
};

export type WeeklyExerciseAdjustment = {
  primary_exercise_id: string;
  set_delta: number;
  weight_scale: number;
  rationale: string;
};

export type WeeklyPlanAdjustment = {
  global_set_delta: number;
  global_weight_scale: number;
  weak_point_exercises: string[];
  exercise_overrides: WeeklyExerciseAdjustment[];
};

export type WeeklyReviewPayload = {
  body_weight: number;
  calories: number;
  protein: number;
  fat: number;
  carbs: number;
  adherence_score: number;
  notes?: string;
  nutrition_phase?: string;
  week_start?: string;
};

export type WeeklyReviewResponse = {
  status: string;
  week_start: string;
  previous_week_start: string;
  readiness_score: number;
  global_guidance: string;
  fault_count: number;
  summary: WeeklyPerformanceSummary;
  adjustments: WeeklyPlanAdjustment;
};

export type SorenessSeverity = "none" | "mild" | "moderate" | "severe";

export type SorenessEntry = {
  id: string;
  entry_date: string;
  severity_by_muscle: Record<string, SorenessSeverity>;
  notes?: string | null;
  created_at: string;
};

export type SorenessCreatePayload = {
  entry_date: string;
  severity_by_muscle: Record<string, SorenessSeverity>;
  notes?: string;
};

export function getToken(): string | null {
  if (globalThis.window === undefined) {
    return null;
  }
  return localStorage.getItem("hypertrophy_token");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }

  return (await res.json()) as T;
}

export const api = {
  health: () => request<{ status: string; date: string }>("/health"),
  getTodayWorkout: () => request<WorkoutSession>("/workout/today"),
  getWorkoutProgress: (workoutId: string) => request<WorkoutProgress>(`/workout/${encodeURIComponent(workoutId)}/progress`),
  getWorkoutSummary: (workoutId: string) => request<WorkoutSummary>(`/workout/${encodeURIComponent(workoutId)}/summary`),
  generateWeek: (templateId?: string | null) => request<Record<string, unknown>>("/plan/generate-week", { method: "POST", body: JSON.stringify(templateId ? { template_id: templateId } : {}) }),
  getProfile: () => request<Profile>("/profile"),
  listPrograms: () => request<ProgramTemplateOption[]>("/plan/programs"),
  listGuidePrograms: () => request<GuideProgram[]>("/plan/guides/programs"),
  getProgramGuide: (programId: string) =>
    request<GuideProgramDetail>(`/plan/guides/programs/${encodeURIComponent(programId)}`),
  getProgramDayGuide: (programId: string, dayIndex: number) =>
    request<GuideDayDetail>(`/plan/guides/programs/${encodeURIComponent(programId)}/days/${encodeURIComponent(String(dayIndex))}`),
  getProgramExerciseGuide: (programId: string, exerciseId: string) =>
    request<GuideExerciseDetail>(
      `/plan/guides/programs/${encodeURIComponent(programId)}/exercise/${encodeURIComponent(exerciseId)}`,
    ),
  getProgramRecommendation: () => request<ProgramRecommendation>("/profile/program-recommendation"),
  switchProgram: (payload: { target_program_id: string; confirm?: boolean }) =>
    request<ProgramSwitchResponse>("/profile/program-switch", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateProfile: (payload: Partial<Profile>) => request<Profile>("/profile", { method: "POST", body: JSON.stringify(payload) }),
  getWeeklyReviewStatus: () => request<WeeklyReviewStatus>("/weekly-review/status"),
  submitWeeklyReview: (payload: WeeklyReviewPayload) =>
    request<WeeklyReviewResponse>("/weekly-review", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  weeklyCheckin: (payload: WeeklyCheckinPayload) =>
    request<{ status: string; phase: string }>("/weekly-checkin", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getWeeklyCheckinHistory: (limit = 12) =>
    request<HistoryWeeklyCheckinResponse>(`/history/weekly-checkins?limit=${encodeURIComponent(String(limit))}`),
  getHistoryAnalytics: (limitWeeks = 8, checkinLimit = 24) =>
    request<HistoryAnalyticsResponse>(
      `/history/analytics?limit_weeks=${encodeURIComponent(String(limitWeeks))}&checkin_limit=${encodeURIComponent(String(checkinLimit))}`,
    ),
  listSoreness: (startDate: string, endDate: string) =>
    request<SorenessEntry[]>(`/soreness?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`),
  createSoreness: (payload: SorenessCreatePayload) =>
    request<SorenessEntry>("/soreness", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  logSet: (workoutId: string, payload: { primary_exercise_id?: string | null; exercise_id: string; set_index: number; reps: number; weight: number; rpe?: number | null }) =>
    request<WorkoutSetFeedback>(`/workout/${encodeURIComponent(workoutId)}/log-set`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
