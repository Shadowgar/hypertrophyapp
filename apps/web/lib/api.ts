import { API_BASE_URL } from "@/lib/env";

const PROGRAM_NAME_OVERRIDES: Record<string, string> = {
  pure_bodybuilding_phase_1_full_body: "Pure Bodybuilding - Phase 1 Full Body",
  full_body_v1: "Pure Bodybuilding - Phase 1 Full Body",
  adaptive_full_body_gold_v0_1: "Pure Bodybuilding - Phase 1 Full Body",
};

type ExerciseVideo = {
  youtube_url?: string;
} | null;

type AuthoredExecutionFields = {
  last_set_intensity_technique?: string | null;
  warm_up_sets?: string | null;
  working_sets?: string | null;
  reps?: string | null;
  early_set_rpe?: string | null;
  last_set_rpe?: string | null;
  rest?: string | null;
  tracking_set_1?: string | null;
  tracking_set_2?: string | null;
  tracking_set_3?: string | null;
  tracking_set_4?: string | null;
  substitution_option_1?: string | null;
  substitution_option_2?: string | null;
  demo_url?: string | null;
  video_url?: string | null;
  video?: ExerciseVideo;
};

export type WorkoutExercise = AuthoredExecutionFields & {
  id: string;
  primary_exercise_id?: string;
  name: string;
  sets: number;
  rep_range: [number, number];
  recommended_working_weight: number;
  /** Warmup weights in kg (from API); used to show warm-up set prescriptions. */
  warmups?: number[];
  slot_role?: string | null;
  substitution_candidates?: string[];
  notes?: string | null;
  completed_sets?: number;
  live_recommendation?: WorkoutLiveRecommendation;
};

export type WorkoutLiveRecommendation = {
  completed_sets: number;
  remaining_sets: number;
  recommended_reps_min: number;
  recommended_reps_max: number;
  recommended_weight: number;
  guidance: string;
  guidance_rationale?: string;
  decision_trace?: Record<string, unknown>;
};

export type WorkoutSession = {
  session_id: string;
  title: string;
  date: string;
  day_role?: string | null;
  resume?: boolean;
  daily_quote?: {
    text: string;
    author: string;
    source: string;
  };
  mesocycle?: {
    week_index: number;
    authored_week_index?: number | null;
    authored_week_role?: string | null;
    authored_sequence_complete?: boolean;
    phase_transition_pending?: boolean;
    post_authored_behavior?: string | null;
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
  weak_areas?: string[];
  onboarding_answers?: Record<string, unknown>;
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
  rationale?: string;
  decision_trace?: Record<string, unknown>;
  compatible_program_ids: string[];
  generated_at: string;
};

export type ProgramTemplateOption = {
  id: string;
  slug?: string;
  name?: string;
  description?: string;
  split?: string;
  days_supported?: number[];
};

export type GeneratedWeekExercise = AuthoredExecutionFields & {
  id: string;
  primary_exercise_id?: string | null;
  name: string;
  sets: number;
  rep_range: [number, number];
  recommended_working_weight: number;
  slot_role?: string | null;
  primary_muscles?: string[];
  substitution_candidates?: string[];
  notes?: string | null;
  adaptive_rationale?: string;
};

export type GeneratedWeekSession = {
  session_id: string;
  title: string;
  date: string;
  day_role?: string | null;
  exercises: GeneratedWeekExercise[];
};

export type GeneratedWeekPlan = {
  program_template_id: string;
  split: string;
  phase: string;
  week_start: string;
  user: {
    name?: string | null;
    days_available: number;
  };
  sessions: GeneratedWeekSession[];
  missed_day_policy: string;
  weekly_volume_by_muscle: Record<string, number>;
  muscle_coverage: {
    minimum_sets_per_muscle?: number;
    covered_muscles?: string[];
    under_target_muscles?: string[];
    untracked_exercise_count?: number;
  };
  mesocycle: {
    week_index: number;
    authored_week_index?: number | null;
    authored_week_role?: string | null;
    authored_sequence_complete?: boolean;
    phase_transition_pending?: boolean;
    post_authored_behavior?: string | null;
    trigger_weeks_base: number;
    trigger_weeks_effective: number;
    is_deload_week: boolean;
    deload_reason: string;
  };
  deload: {
    active: boolean;
    set_reduction_pct: number;
    load_reduction_pct: number;
    reason: string;
  };
  adaptive_review?: {
    global_set_delta: number;
    global_weight_scale: number;
    weak_point_exercises: string[];
    week_start?: string;
    reviewed_on?: string;
    decision_trace?: Record<string, unknown>;
  };
  applied_frequency_adaptation?: {
    template_id: string;
    target_days: number;
    duration_weeks: number;
    weeks_remaining_before_apply: number;
    weeks_remaining_after_apply: number;
    weak_areas: string[];
    completed?: boolean;
    decision_trace?: Record<string, unknown>;
  };
  template_selection_trace: Record<string, unknown>;
  generation_runtime_trace: Record<string, unknown>;
  decision_trace?: Record<string, unknown>;
};

export function getProgramDisplayName(program: ProgramTemplateOption): string {
  const aliasName = PROGRAM_NAME_OVERRIDES[program.id];
  if (aliasName) {
    return aliasName;
  }
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
  rationale?: string;
  decision_trace?: Record<string, unknown>;
  requires_confirmation: boolean;
  applied: boolean;
};

export type IntelligenceCoachPreviewRequest = {
  template_id?: string | null;
  from_days: number;
  to_days: number;
  completion_pct: number;
  adherence_score: number;
  soreness_level: SorenessSeverity;
  average_rpe?: number | null;
  current_phase: "accumulation" | "intensification" | "deload";
  weeks_in_phase: number;
  stagnation_weeks: number;
  readiness_score?: number | null;
  lagging_muscles: string[];
  target_min_sets: number;
};

export type IntelligenceCoachPreviewResponse = {
  recommendation_id: string;
  template_id: string;
  program_name: string;
  schedule: {
    from_days: number;
    to_days: number;
    kept_sessions: string[];
    dropped_sessions: string[];
    added_sessions: string[];
    risk_level: "low" | "medium" | "high";
    muscle_set_delta: Record<string, number>;
    tradeoffs: string[];
  };
  progression: {
    action: "progress" | "hold" | "deload";
    load_scale: number;
    set_delta: number;
    reason: string;
    rationale?: string;
  };
  phase_transition: {
    next_phase: "accumulation" | "intensification" | "deload";
    reason: string;
    rationale?: string;
    authored_sequence_complete?: boolean;
    transition_pending?: boolean;
    recommended_action?: string | null;
    post_authored_behavior?: string | null;
  };
  specialization: {
    focus_muscles: string[];
    focus_adjustments: Record<string, number>;
    donor_adjustments: Record<string, number>;
    uncompensated_added_sets: number;
  };
  media_warmups: {
    total_exercises: number;
    video_linked_exercises: number;
    video_coverage_pct: number;
    sample_warmups: Array<{
      exercise_id: string;
      warmups: number[];
    }>;
  };
  decision_trace: Record<string, unknown>;
};

export type ApplyPhaseDecisionResponse = {
  status: string;
  recommendation_id: string;
  applied_recommendation_id?: string | null;
  requires_confirmation: boolean;
  applied: boolean;
  next_phase: "accumulation" | "intensification" | "deload";
  reason: string;
  rationale?: string;
  decision_trace: Record<string, unknown>;
};

export function resolveReasonText(rationale?: string | null, reason?: string | null): string | null {
  const preferred = rationale?.trim();
  if (preferred) {
    return preferred;
  }
  const fallback = reason?.trim();
  if (!fallback) {
    return null;
  }
  return fallback;
}

export type ApplySpecializationDecisionResponse = {
  status: string;
  recommendation_id: string;
  applied_recommendation_id?: string | null;
  requires_confirmation: boolean;
  applied: boolean;
  focus_muscles: string[];
  focus_adjustments: Record<string, number>;
  donor_adjustments: Record<string, number>;
  uncompensated_added_sets: number;
  decision_trace: Record<string, unknown>;
};

export type CoachingRecommendationTimelineEntry = {
  recommendation_id: string;
  recommendation_type: string;
  status: string;
  template_id: string;
  current_phase: string;
  recommended_phase: string;
  progression_action: string;
  rationale: string;
  focus_muscles: string[];
  created_at: string;
  applied_at?: string | null;
};

export type CoachingRecommendationTimelineResponse = {
  entries: CoachingRecommendationTimelineEntry[];
};

export type FrequencyAdaptationDecision = {
  action: "preserve" | "combine" | "rotate" | "reduce";
  exercise_id: string;
  source_day_id: string;
  target_day_id?: string | null;
  reason: string;
};

export type FrequencyAdaptationWeekResult = {
  week_index: number;
  adapted_training_days: number;
  adapted_days: Array<{
    day_id: string;
    source_day_ids: string[];
    exercise_ids: string[];
  }>;
  decisions: FrequencyAdaptationDecision[];
  coverage_before: Record<string, number>;
  coverage_after: Record<string, number>;
  rationale: string;
};

export type FrequencyAdaptationResult = {
  program_id: string;
  from_days: number;
  to_days: number;
  duration_weeks: number;
  weak_areas: string[];
  weeks: FrequencyAdaptationWeekResult[];
  rejoin_policy: string;
  decision_trace?: Record<string, unknown>;
};

export type FrequencyAdaptationApplyResponse = {
  status: string;
  program_id: string;
  target_days: number;
  duration_weeks: number;
  weeks_remaining: number;
  weak_areas: string[];
  decision_trace?: Record<string, unknown>;
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
  guidance_rationale: string;
  decision_trace?: Record<string, unknown>;
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
  guidance_rationale: string;
  decision_trace?: Record<string, unknown>;
};

export type WorkoutSummary = {
  workout_id: string;
  completed_total: number;
  planned_total: number;
  percent_complete: number;
  overall_guidance: string;
  overall_rationale: string;
  decision_trace?: Record<string, unknown>;
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

export type HistoryCalendarDay = {
  date: string;
  weekday: number;
  set_count: number;
  exercise_count: number;
  total_volume: number;
  completed: boolean;
  program_ids: string[];
  muscles: string[];
  pr_count: number;
  pr_exercises: string[];
};

export type HistoryCalendarResponse = {
  start_date: string;
  end_date: string;
  active_days: number;
  current_streak_days: number;
  longest_streak_days: number;
  days: HistoryCalendarDay[];
};

export type HistoryDaySet = {
  set_index: number;
  reps: number;
  weight: number;
  rpe?: number | null;
  created_at: string;
};

export type HistoryDayExercise = {
  exercise_id: string;
  primary_exercise_id?: string | null;
  planned_name?: string | null;
  primary_muscles?: string[];
  total_sets: number;
  total_volume: number;
  planned_sets?: number | null;
  set_delta?: number | null;
  sets: HistoryDaySet[];
};

export type HistoryDayWorkout = {
  workout_id: string;
  program_id?: string | null;
  total_sets: number;
  total_volume: number;
  planned_sets_total?: number;
  set_delta?: number;
  exercises: HistoryDayExercise[];
};

export type HistoryDayDetailResponse = {
  date: string;
  workouts: HistoryDayWorkout[];
  totals: {
    set_count: number;
    exercise_count: number;
    total_volume: number;
    planned_set_count?: number;
    set_delta?: number;
  };
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
  decision_trace: Record<string, unknown>;
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

export type PasswordResetRequestResponse = {
  status: string;
  reset_token?: string | null;
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
  health: () => request<{ status: string; date: string; version?: string }>("/health"),
  getTodayWorkout: () => request<WorkoutSession>("/workout/today"),
  getWorkoutProgress: (workoutId: string) => request<WorkoutProgress>(`/workout/${encodeURIComponent(workoutId)}/progress`),
  getWorkoutSummary: (workoutId: string) => request<WorkoutSummary>(`/workout/${encodeURIComponent(workoutId)}/summary`),
  generateWeek: (templateId?: string | null) =>
    request<GeneratedWeekPlan>("/plan/generate-week", {
      method: "POST",
      body: JSON.stringify(templateId ? { template_id: templateId } : {}),
    }),
  getLatestWeekPlan: () => request<GeneratedWeekPlan>("/plan/latest-week"),
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
  coachPreview: (payload: IntelligenceCoachPreviewRequest) =>
    request<IntelligenceCoachPreviewResponse>("/plan/intelligence/coach-preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  applyPhaseDecision: (payload: { recommendation_id: string; confirm?: boolean }) =>
    request<ApplyPhaseDecisionResponse>("/plan/intelligence/apply-phase", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  applySpecializationDecision: (payload: { recommendation_id: string; confirm?: boolean }) =>
    request<ApplySpecializationDecisionResponse>("/plan/intelligence/apply-specialization", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getCoachingRecommendationTimeline: (limit = 20) =>
    request<CoachingRecommendationTimelineResponse>(
      `/plan/intelligence/recommendations?limit=${encodeURIComponent(String(limit))}`,
    ),
  previewFrequencyAdaptation: (payload: {
    program_id?: string | null;
    target_days: number;
    duration_weeks?: number;
    weak_areas?: string[];
  }) =>
    request<FrequencyAdaptationResult>("/plan/adaptation/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  applyFrequencyAdaptation: (payload: {
    program_id?: string | null;
    target_days: number;
    duration_weeks?: number;
    weak_areas?: string[];
  }) =>
    request<FrequencyAdaptationApplyResponse>("/plan/adaptation/apply", {
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
  getHistoryCalendar: (startDate: string, endDate: string) =>
    request<HistoryCalendarResponse>(
      `/history/calendar?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`,
    ),
  getHistoryDayDetail: (day: string) =>
    request<HistoryDayDetailResponse>(`/history/day/${encodeURIComponent(day)}`),
  listSoreness: (startDate: string, endDate: string) =>
    request<SorenessEntry[]>(`/soreness?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`),
  createSoreness: (payload: SorenessCreatePayload) =>
    request<SorenessEntry>("/soreness", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  wipeProfileData: () =>
    request<{ status: string }>("/profile/dev/wipe", {
      method: "POST",
      body: JSON.stringify({}),
    }),
  resetProfileToPhase1: () =>
    request<{ status: string }>("/profile/dev/reset-phase1", {
      method: "POST",
      body: JSON.stringify({}),
    }),
  devWipeUser: (payload: { email: string; confirmation: string }) =>
    request<{ status: string }>("/auth/dev/wipe-user", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  requestPasswordReset: (payload: { email: string }) =>
    request<PasswordResetRequestResponse>("/auth/password-reset/request", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  logSet: (workoutId: string, payload: { primary_exercise_id?: string | null; exercise_id: string; set_index: number; reps: number; weight: number; rpe?: number | null }) =>
    request<WorkoutSetFeedback>(`/workout/${encodeURIComponent(workoutId)}/log-set`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  undoLastSet: (workoutId: string, exerciseId: string) =>
    request<{ status: string }>(`/workout/${encodeURIComponent(workoutId)}/undo-last-set`, {
      method: "POST",
      body: JSON.stringify({ exercise_id: exerciseId }),
    }),
};
