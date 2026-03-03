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
  video?: {
    youtube_url?: string;
  } | null;
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

export type WeeklyCheckinPayload = {
  week_start: string;
  body_weight: number;
  adherence_score: number;
  notes?: string;
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
  weeklyCheckin: (payload: WeeklyCheckinPayload) =>
    request<{ status: string; phase: string }>("/weekly-checkin", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  listSoreness: (startDate: string, endDate: string) =>
    request<SorenessEntry[]>(`/soreness?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`),
  createSoreness: (payload: SorenessCreatePayload) =>
    request<SorenessEntry>("/soreness", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  logSet: (workoutId: string, payload: { primary_exercise_id?: string | null; exercise_id: string; set_index: number; reps: number; weight: number; rpe?: number | null }) =>
    request<Record<string, unknown>>(`/workout/${encodeURIComponent(workoutId)}/log-set`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
