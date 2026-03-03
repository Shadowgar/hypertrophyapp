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
  listPrograms: () => request<Array<{id: string; slug?: string; name: string; description?: string}>>("/plan/programs"),
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
