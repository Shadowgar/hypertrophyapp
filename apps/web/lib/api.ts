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
};

export type WeeklyCheckinPayload = {
  week_start: string;
  body_weight: number;
  adherence_score: number;
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
  generateWeek: () => request<Record<string, unknown>>("/plan/generate-week", { method: "POST", body: JSON.stringify({}) }),
  getProfile: () => request<Profile>("/profile"),
  weeklyCheckin: (payload: WeeklyCheckinPayload) =>
    request<{ status: string; phase: string }>("/weekly-checkin", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
