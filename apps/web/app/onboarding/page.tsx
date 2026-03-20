"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { UiIcon } from "@/components/ui/icons";
import { api, clearAuthToken, getProgramDisplayName, setAuthToken, type ProgramTemplateOption } from "@/lib/api";
import { API_BASE_URL } from "@/lib/env";

const FALLBACK_PROGRAMS: ProgramTemplateOption[] = [
  {
    id: "pure_bodybuilding_phase_1_full_body",
    name: "Pure Bodybuilding - Phase 1 Full Body",
    split: "full_body",
    days_supported: [2, 3, 4, 5],
    description: "Workbook-faithful full body path with authored execution detail.",
  },
];

const INTRO_SLIDES = [
  {
    headline: "Science-based gym and home workouts",
    subheadline: "No gimmicks. No fads.",
    body: "Personalized training built from deterministic rules and your real constraints.",
  },
  {
    headline: "Track progress and adapt intelligently",
    subheadline: "Train. Log. Adjust.",
    body: "Every week uses your data to adapt frequency and session structure with transparent logic.",
  },
  {
    headline: "Start with a focused onboarding",
    subheadline: "One step at a time.",
    body: "We will collect only what we need to build your initial plan and keep it adaptive.",
  },
] as const;

const GENDER_OPTIONS = ["male", "female", "prefer_not_to_say"] as const;
const GOAL_OPTIONS = [
  "build_muscle",
  "lose_fat",
  "gain_strength",
  "improve_overall_health",
  "improve_performance",
  "something_else",
] as const;
const TRAINING_AGE_OPTIONS = ["getting_started", "less_than_1_year", "1_2_years", "2_5_years", "more_than_5_years"] as const;
const TRAINING_AGE_LABELS: Record<(typeof TRAINING_AGE_OPTIONS)[number], string> = {
  getting_started: "Getting started",
  less_than_1_year: "Less than 1 year",
  "1_2_years": "1 to 2 years",
  "2_5_years": "2 to 5 years",
  more_than_5_years: "More than 5 years",
};
const FREQUENCY_OPTIONS = ["never", "once_in_a_while", "1_2_per_week", "3_4_per_week", "5_plus_per_week"] as const;
const FREQUENCY_LABELS: Record<(typeof FREQUENCY_OPTIONS)[number], string> = {
  never: "Never",
  once_in_a_while: "Once in a while",
  "1_2_per_week": "1 to 2 times per week",
  "3_4_per_week": "3 to 4 times per week",
  "5_plus_per_week": "5+ per week",
};
const MOTIVATION_OPTIONS = ["accountability", "competition", "fun", "self_motivated"] as const;
const OBSTACLE_OPTIONS = [
  "lack_of_motivation",
  "not_sure_what_to_do",
  "not_enough_time",
  "dealing_with_injury",
  "something_else",
  "none_right_now",
] as const;
const LOCATION_OPTIONS = ["gym", "home"] as const;
const EXPERIENCE_LEVEL_OPTIONS = ["beginner", "intermediate", "advanced"] as const;
const DURATION_OPTIONS = [30, 45, 60] as const;
const DAYS_OPTIONS = [2, 3, 4, 5] as const;
const EQUIPMENT_TAGS = ["barbell", "bench", "dumbbell", "cable", "machine", "bands", "bodyweight"] as const;
type EquipmentTag = (typeof EQUIPMENT_TAGS)[number];
const DEFAULT_EQUIPMENT_HOME: EquipmentTag[] = ["dumbbell", "bodyweight"];
const DEFAULT_EQUIPMENT_GYM: EquipmentTag[] = ["dumbbell", "machine", "cable"];
const MOVEMENT_RESTRICTION_OPTIONS = ["overhead_pressing", "deep_knee_flexion"] as const;
type MovementRestriction = (typeof MOVEMENT_RESTRICTION_OPTIONS)[number];
const MOVEMENT_RESTRICTION_LABELS: Record<MovementRestriction, string> = {
  overhead_pressing: "Overhead pressing limitations",
  deep_knee_flexion: "Squat/lunge knee-flexion limitations",
};
const ONBOARDING_DRAFT_KEY = "hypertrophy_onboarding_draft_v1";

type Phase = "intro" | "questions" | "account" | "saving";
type AuthMode = "register" | "login";
type QuestionStepId =
  | "gender"
  | "goal"
  | "height"
  | "weight"
  | "birthday"
  | "training_age"
  | "frequency"
  | "motivation"
  | "obstacle"
  | "location"
  | "gym_setup"
  | "movement_restrictions"
  | "experience"
  | "duration"
  | "days"
  | "name";

type QuestionStep = {
  id: QuestionStepId;
  title: string;
  skipAllowed: boolean;
};

type OnboardingDraft = {
  phase: Exclude<Phase, "saving">;
  authMode: AuthMode;
  introIndex: number;
  questionIndex: number;
  gender: (typeof GENDER_OPTIONS)[number] | "";
  primaryGoal: (typeof GOAL_OPTIONS)[number] | "";
  primaryGoals: (typeof GOAL_OPTIONS)[number][];
  heightUnit: "in" | "cm";
  heightFeet: string;
  heightInches: string;
  heightCm: string;
  weightUnit: "lbs" | "kg";
  weightValue: string;
  birthday: string;
  trainingAgeBucket: (typeof TRAINING_AGE_OPTIONS)[number] | "";
  strengthFrequency: (typeof FREQUENCY_OPTIONS)[number] | "";
  motivationDriver: (typeof MOTIVATION_OPTIONS)[number] | "";
  obstacle: (typeof OBSTACLE_OPTIONS)[number] | "";
  trainingLocation: (typeof LOCATION_OPTIONS)[number] | "";
  equipmentTags: EquipmentTag[];
  movementRestrictions: string[];
  experienceLevel: (typeof EXPERIENCE_LEVEL_OPTIONS)[number] | "";
  workoutDurationMinutes: number | null;
  daysAvailable: number | null;
  firstName: string;
  lastName: string;
  email: string;
  weakAreasRaw: string;
  selectedProgramId: string | null;
};

function parseOnboardingDraft(raw: string): Partial<OnboardingDraft> | null {
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") {
      return null;
    }
    return parsed as Partial<OnboardingDraft>;
  } catch {
    return null;
  }
}

function isMeaningfulDraft(draft: OnboardingDraft): boolean {
  if (draft.phase !== "intro") {
    return true;
  }
  if (draft.introIndex > 0 || draft.questionIndex > 0) {
    return true;
  }
  return Boolean(
    draft.gender
    || draft.primaryGoal
    || (Array.isArray(draft.primaryGoals) && draft.primaryGoals.length > 0)
    || draft.birthday
    || draft.trainingAgeBucket
    || draft.strengthFrequency
    || draft.motivationDriver
    || draft.obstacle
    || draft.trainingLocation
    || (Array.isArray(draft.equipmentTags) && draft.equipmentTags.length > 0)
    || (Array.isArray(draft.movementRestrictions) && draft.movementRestrictions.length > 0)
    || draft.experienceLevel
    || draft.firstName.trim()
    || draft.lastName.trim()
    || draft.email.trim() !== "athlete@example.com"
    || draft.weakAreasRaw.trim()
    || draft.selectedProgramId,
  );
}

function applyStringDraftValue(value: unknown, setter: (next: string) => void): void {
  if (typeof value === "string") {
    setter(value);
  }
}

function applyStringOptionDraftValue(
  value: unknown,
  options: readonly string[],
  setter: (next: string) => void,
): void {
  if (typeof value === "string" && options.includes(value)) {
    setter(value);
  }
}

function applyNumberOptionDraftValue(
  value: unknown,
  options: readonly number[],
  setter: (next: number) => void,
): void {
  if (typeof value === "number" && options.includes(value)) {
    setter(value);
  }
}

async function parseApiError(response: Response, fallback: string): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown; message?: string };
    const detail = payload.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((item) => {
          if (typeof item === "string") {
            return item;
          }
          if (item && typeof item === "object" && "msg" in item) {
            const msg = (item as { msg?: unknown }).msg;
            return typeof msg === "string" ? msg : JSON.stringify(item);
          }
          return JSON.stringify(item);
        })
        .join("; ");
    }
    if (typeof payload.message === "string" && payload.message.trim()) {
      return payload.message;
    }
  } catch {
    try {
      const text = await response.text();
      if (text.trim()) {
        return text;
      }
    } catch {
      // no-op: fallback below
    }
  }
  return fallback;
}

function resolveStatusTone(status: string): "green" | "yellow" | "red" {
  const lowered = status.toLowerCase();
  if (lowered.includes("saved") || lowered.includes("ready") || lowered.includes("wiped")) {
    return "green";
  }
  if (lowered.includes("failed") || lowered.includes("error")) {
    return "red";
  }
  return "yellow";
}

function parseWeakAreas(raw: string): string[] {
  return raw
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter((item) => item.length > 0);
}

function normalizeEmailInput(value: string): string {
  return value.trim().toLowerCase();
}

function deriveAgeFromBirthday(birthday: string): number {
  if (!birthday) {
    return 30;
  }
  const parsed = new Date(birthday);
  if (Number.isNaN(parsed.getTime())) {
    return 30;
  }
  const today = new Date();
  let age = today.getFullYear() - parsed.getFullYear();
  const monthDiff = today.getMonth() - parsed.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < parsed.getDate())) {
    age -= 1;
  }
  return Math.max(14, Math.min(90, age));
}

function convertWeightToKg(value: number, unit: "lbs" | "kg"): number {
  if (unit === "kg") {
    return value;
  }
  return Number((value * 0.45359237).toFixed(1));
}

function deriveSplitPreference(daysAvailable: number): "full_body" | "upper_lower" | "ppl" {
  if (daysAvailable <= 3) {
    return "full_body";
  }
  if (daysAvailable === 4) {
    return "upper_lower";
  }
  return "ppl";
}

function defaultEquipmentTagsForLocation(location: "gym" | "home"): EquipmentTag[] {
  return location === "home" ? DEFAULT_EQUIPMENT_HOME : DEFAULT_EQUIPMENT_GYM;
}

export default function OnboardingPage() {
  const router = useRouter();

  const [phase, setPhase] = useState<Phase>("intro");
  const [authMode, setAuthMode] = useState<AuthMode>("register");
  const [introIndex, setIntroIndex] = useState(0);
  const [questionIndex, setQuestionIndex] = useState(0);

  const [gender, setGender] = useState<(typeof GENDER_OPTIONS)[number] | "">("");
  const [primaryGoal, setPrimaryGoal] = useState<(typeof GOAL_OPTIONS)[number] | "">("");
  const [primaryGoals, setPrimaryGoals] = useState<(typeof GOAL_OPTIONS)[number][]>([]);
  const [heightUnit, setHeightUnit] = useState<"in" | "cm">("in");
  const [heightFeet, setHeightFeet] = useState("5");
  const [heightInches, setHeightInches] = useState("9");
  const [heightCm, setHeightCm] = useState("175");
  const [weightUnit, setWeightUnit] = useState<"lbs" | "kg">("lbs");
  const [weightValue, setWeightValue] = useState("180");
  const [birthday, setBirthday] = useState("");
  const [trainingAgeBucket, setTrainingAgeBucket] = useState<(typeof TRAINING_AGE_OPTIONS)[number] | "">("");
  const [strengthFrequency, setStrengthFrequency] = useState<(typeof FREQUENCY_OPTIONS)[number] | "">("");
  const [motivationDriver, setMotivationDriver] = useState<(typeof MOTIVATION_OPTIONS)[number] | "">("");
  const [obstacle, setObstacle] = useState<(typeof OBSTACLE_OPTIONS)[number] | "">("");
  const [trainingLocation, setTrainingLocation] = useState<(typeof LOCATION_OPTIONS)[number] | "">("");
  const [equipmentTags, setEquipmentTags] = useState<EquipmentTag[]>([]);
  const [movementRestrictions, setMovementRestrictions] = useState<string[]>([]);
  const [experienceLevel, setExperienceLevel] = useState<(typeof EXPERIENCE_LEVEL_OPTIONS)[number] | "">("");
  const [workoutDurationMinutes, setWorkoutDurationMinutes] = useState<number | null>(null);
  const [daysAvailable, setDaysAvailable] = useState<number | null>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");

  const [email, setEmail] = useState("athlete@example.com");
  const [password, setPassword] = useState("athlete123");
  const [showPassword, setShowPassword] = useState(false);
  const [weakAreasRaw, setWeakAreasRaw] = useState("");

  const [programs, setPrograms] = useState<ProgramTemplateOption[]>([]);
  const [programCatalogStatus, setProgramCatalogStatus] = useState("Loading program catalog...");
  const [selectedProgramId, setSelectedProgramId] = useState<string | null>(null);

  const [status, setStatus] = useState("Idle");
  const [draftReady, setDraftReady] = useState(false);
  const [hasSavedDraft, setHasSavedDraft] = useState(false);
  const statusTone = resolveStatusTone(status);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const list = await api.listPrograms();
        if (!mounted) {
          return;
        }
        const normalized = Array.isArray(list) && list.length > 0 ? list : FALLBACK_PROGRAMS;
        setPrograms(normalized);
        setProgramCatalogStatus(`Loaded ${normalized.length} active training template${normalized.length === 1 ? "" : "s"}.`);
      } catch {
        if (!mounted) {
          return;
        }
        setPrograms(FALLBACK_PROGRAMS);
        setProgramCatalogStatus("Using default program template. (API unreachable from this browser — check Docker containers.)");
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const effectiveDaysAvailable = daysAvailable ?? 3;
  const splitPreference = deriveSplitPreference(effectiveDaysAvailable);
  const visiblePrograms = useMemo(() => {
    const scored = programs.map((program) => {
      const splitCompatible = !program.split || program.split === splitPreference;
      const daysCompatible =
        !Array.isArray(program.days_supported)
        || program.days_supported.length === 0
        || program.days_supported.includes(effectiveDaysAvailable);
      return {
        program,
        score: (splitCompatible ? 2 : 0) + (daysCompatible ? 1 : 0),
      };
    });

    scored.sort((a, b) => {
      if (a.score !== b.score) {
        return b.score - a.score;
      }
      return getProgramDisplayName(a.program).localeCompare(getProgramDisplayName(b.program));
    });
    return scored.map((entry) => entry.program);
  }, [effectiveDaysAvailable, programs, splitPreference]);

  useEffect(() => {
    if (selectedProgramId && !visiblePrograms.some((program) => program.id === selectedProgramId)) {
      setSelectedProgramId(null);
    }
  }, [selectedProgramId, visiblePrograms]);

  // Prefill equipment defaults based on location, but do not override explicit user selections.
  useEffect(() => {
    if (!trainingLocation) return;
    if (equipmentTags.length > 0) return;
    setEquipmentTags(defaultEquipmentTagsForLocation(trainingLocation));
  }, [trainingLocation, equipmentTags.length]);

  const questionSteps: QuestionStep[] = useMemo(
    () => [
      { id: "gender", title: "What is your gender?", skipAllowed: false },
      { id: "goal", title: "What is your primary fitness goal?", skipAllowed: false },
      { id: "height", title: "How tall are you?", skipAllowed: false },
      { id: "weight", title: "What is your current weight?", skipAllowed: false },
      { id: "birthday", title: "When is your birthday?", skipAllowed: false },
      { id: "training_age", title: "How long have you been strength training consistently?", skipAllowed: false },
      { id: "frequency", title: "How often do you currently strength train?", skipAllowed: true },
      { id: "motivation", title: "What helps you stay motivated to work out?", skipAllowed: true },
      { id: "obstacle", title: "What obstacle is biggest right now?", skipAllowed: true },
      { id: "location", title: "Where will you be primarily working out?", skipAllowed: true },
      { id: "gym_setup", title: "Which best describes your gym setup?", skipAllowed: true },
      { id: "movement_restrictions", title: "Do you have any movement limitations right now?", skipAllowed: true },
      { id: "experience", title: "How much lifting experience do you have?", skipAllowed: true },
      { id: "duration", title: "How long would you like workouts to be?", skipAllowed: true },
      { id: "days", title: "How many days per week can you train?", skipAllowed: true },
      { id: "name", title: "What should we call you?", skipAllowed: false },
    ],
    [],
  );

  const currentQuestion = questionSteps[Math.min(questionIndex, questionSteps.length - 1)];

  useEffect(() => {
    const raw = localStorage.getItem(ONBOARDING_DRAFT_KEY);
    if (!raw) {
      setDraftReady(true);
      return;
    }

    const draft = parseOnboardingDraft(raw);
    if (!draft) {
      localStorage.removeItem(ONBOARDING_DRAFT_KEY);
      setDraftReady(true);
      return;
    }

    const restoredPhase = draft.phase === "questions" || draft.phase === "account" ? draft.phase : "intro";
    const restoredAuthMode = draft.authMode === "login" ? "login" : "register";
    const restoredIntroIndex = Number.isFinite(draft.introIndex) ? Math.min(Math.max(0, Number(draft.introIndex)), INTRO_SLIDES.length - 1) : 0;
    const restoredQuestionIndex = Number.isFinite(draft.questionIndex)
      ? Math.min(Math.max(0, Number(draft.questionIndex)), questionSteps.length - 1)
      : 0;

    if (Array.isArray(draft.primaryGoals) && draft.primaryGoals.length > 0) {
      setPrimaryGoals(draft.primaryGoals.filter((g): g is (typeof GOAL_OPTIONS)[number] => GOAL_OPTIONS.includes(g)));
    } else if (draft.primaryGoal && GOAL_OPTIONS.includes(draft.primaryGoal as (typeof GOAL_OPTIONS)[number])) {
      setPrimaryGoals([draft.primaryGoal as (typeof GOAL_OPTIONS)[number]]);
    }
    const optionDraftBindings: Array<{ value: unknown; options: readonly string[]; setter: (next: string) => void }> = [
      { value: draft.gender, options: GENDER_OPTIONS, setter: setGender as (next: string) => void },
      { value: draft.primaryGoal, options: GOAL_OPTIONS, setter: setPrimaryGoal as (next: string) => void },
      { value: draft.heightUnit, options: ["in", "cm"], setter: setHeightUnit as (next: string) => void },
      { value: draft.weightUnit, options: ["lbs", "kg"], setter: setWeightUnit as (next: string) => void },
      { value: draft.trainingAgeBucket, options: TRAINING_AGE_OPTIONS, setter: setTrainingAgeBucket as (next: string) => void },
      { value: draft.strengthFrequency, options: FREQUENCY_OPTIONS, setter: setStrengthFrequency as (next: string) => void },
      { value: draft.motivationDriver, options: MOTIVATION_OPTIONS, setter: setMotivationDriver as (next: string) => void },
      { value: draft.obstacle, options: OBSTACLE_OPTIONS, setter: setObstacle as (next: string) => void },
      { value: draft.trainingLocation, options: LOCATION_OPTIONS, setter: setTrainingLocation as (next: string) => void },
      { value: draft.experienceLevel, options: EXPERIENCE_LEVEL_OPTIONS, setter: setExperienceLevel as (next: string) => void },
    ];
    for (const binding of optionDraftBindings) {
      applyStringOptionDraftValue(binding.value, binding.options, binding.setter);
    }

    if (Array.isArray(draft.equipmentTags)) {
      const filtered = draft.equipmentTags.filter((t): t is EquipmentTag => EQUIPMENT_TAGS.includes(t as EquipmentTag));
      setEquipmentTags(Array.from(new Set(filtered)));
    }
    if (Array.isArray(draft.movementRestrictions)) {
      const cleaned = draft.movementRestrictions
        .map((t) => (typeof t === "string" ? t.trim() : ""))
        .filter((t): t is string => t.length > 0);
      setMovementRestrictions(Array.from(new Set(cleaned)));
    }

    const numberBindings: Array<{ value: unknown; options: readonly number[]; setter: (next: number) => void }> = [
      { value: draft.workoutDurationMinutes, options: DURATION_OPTIONS, setter: setWorkoutDurationMinutes as (next: number) => void },
      { value: draft.daysAvailable, options: DAYS_OPTIONS, setter: setDaysAvailable as (next: number) => void },
    ];
    for (const binding of numberBindings) {
      applyNumberOptionDraftValue(binding.value, binding.options, binding.setter);
    }

    const stringBindings: Array<{ value: unknown; setter: (next: string) => void }> = [
      { value: draft.heightFeet, setter: setHeightFeet },
      { value: draft.heightInches, setter: setHeightInches },
      { value: draft.heightCm, setter: setHeightCm },
      { value: draft.weightValue, setter: setWeightValue },
      { value: draft.birthday, setter: setBirthday },
      { value: draft.firstName, setter: setFirstName },
      { value: draft.lastName, setter: setLastName },
      { value: draft.email, setter: setEmail },
      { value: draft.weakAreasRaw, setter: setWeakAreasRaw },
    ];
    for (const binding of stringBindings) {
      applyStringDraftValue(binding.value, binding.setter);
    }

    if (typeof draft.selectedProgramId === "string") {
      setSelectedProgramId(draft.selectedProgramId || null);
    }
    if (draft.selectedProgramId === null) {
      setSelectedProgramId(null);
    }

    setPhase(restoredPhase);
    setAuthMode(restoredAuthMode);
    setIntroIndex(restoredIntroIndex);
    setQuestionIndex(restoredQuestionIndex);
    setHasSavedDraft(true);
    setStatus("Recovered saved onboarding draft");
    setDraftReady(true);
  }, [questionSteps.length]);

  useEffect(() => {
    if (!draftReady) {
      return;
    }

    const draft: OnboardingDraft = {
      phase: phase === "saving" ? "account" : phase,
      authMode,
      introIndex,
      questionIndex,
      gender,
      primaryGoal,
      primaryGoals,
      heightUnit,
      heightFeet,
      heightInches,
      heightCm,
      weightUnit,
      weightValue,
      birthday,
      trainingAgeBucket,
      strengthFrequency,
      motivationDriver,
      obstacle,
      trainingLocation,
      equipmentTags,
      movementRestrictions,
      experienceLevel,
      workoutDurationMinutes,
      daysAvailable,
      firstName,
      lastName,
      email,
      weakAreasRaw,
      selectedProgramId,
    };

    if (!isMeaningfulDraft(draft)) {
      localStorage.removeItem(ONBOARDING_DRAFT_KEY);
      setHasSavedDraft(false);
      return;
    }

    localStorage.setItem(ONBOARDING_DRAFT_KEY, JSON.stringify(draft));
    setHasSavedDraft(true);
  }, [
    authMode,
    birthday,
    daysAvailable,
    draftReady,
    email,
    experienceLevel,
    firstName,
    gender,
    equipmentTags,
    heightCm,
    heightFeet,
    heightInches,
    heightUnit,
    introIndex,
    lastName,
    motivationDriver,
    obstacle,
    phase,
    primaryGoal,
    primaryGoals,
    questionIndex,
    movementRestrictions,
    selectedProgramId,
    strengthFrequency,
    trainingAgeBucket,
    trainingLocation,
    weakAreasRaw,
    weightUnit,
    weightValue,
    workoutDurationMinutes,
  ]);

  function isCurrentQuestionValid(): boolean {
    if (!currentQuestion) {
      return false;
    }
    switch (currentQuestion.id) {
      case "gender":
        return gender.length > 0;
      case "goal":
        return primaryGoals.length > 0;
      case "height":
        if (heightUnit === "in") {
          const feet = Number(heightFeet);
          const inches = Number(heightInches);
          return Number.isFinite(feet) && Number.isFinite(inches) && feet >= 3 && feet <= 8 && inches >= 0 && inches <= 11;
        }
        return Number(heightCm) > 100;
      case "weight":
        return Number(weightValue) > 30;
      case "birthday":
        return birthday.length > 0;
      case "training_age":
        return trainingAgeBucket.length > 0;
      case "frequency":
        return strengthFrequency.length > 0;
      case "motivation":
        return motivationDriver.length > 0;
      case "obstacle":
        return obstacle.length > 0;
      case "location":
        return trainingLocation.length > 0;
      case "gym_setup":
        return equipmentTags.length > 0;
      case "movement_restrictions":
        // empty means "no restrictions" which is a valid choice
        return true;
      case "experience":
        return experienceLevel.length > 0;
      case "duration":
        return workoutDurationMinutes !== null;
      case "days":
        return daysAvailable !== null;
      case "name":
        return firstName.trim().length > 0;
      default:
        return false;
    }
  }

  function skipCurrentQuestion() {
    if (!currentQuestion?.skipAllowed) {
      return;
    }
    if (currentQuestion.id === "location" && !trainingLocation) {
      setTrainingLocation("home");
    }
    if (currentQuestion.id === "duration" && workoutDurationMinutes === null) {
      setWorkoutDurationMinutes(45);
    }
    if (currentQuestion.id === "days" && daysAvailable === null) {
      setDaysAvailable(3);
    }
    if (currentQuestion.id === "gym_setup" && equipmentTags.length === 0) {
      const resolvedLocation = trainingLocation || "home";
      setEquipmentTags(defaultEquipmentTagsForLocation(resolvedLocation));
    }
    if (currentQuestion.id === "experience" && !experienceLevel) {
      setExperienceLevel("intermediate");
    }
    goToNextQuestion();
  }

  function goToNextQuestion() {
    if (questionIndex >= questionSteps.length - 1) {
      setPhase("account");
      return;
    }
    setQuestionIndex((prev) => Math.min(prev + 1, questionSteps.length - 1));
  }

  function goToPreviousQuestion() {
    if (questionIndex <= 0) {
      setPhase("intro");
      return;
    }
    setQuestionIndex((prev) => Math.max(prev - 1, 0));
  }

  function buildOnboardingAnswers() {
    return {
      gender,
      primary_goal: primaryGoals[0] ?? primaryGoal ?? "",
      primary_goals: primaryGoals.length > 0 ? primaryGoals : [primaryGoal].filter(Boolean),
      height: {
        unit: heightUnit,
        feet: heightUnit === "in" ? Number(heightFeet) : null,
        inches: heightUnit === "in" ? Number(heightInches) : null,
        cm: heightUnit === "cm" ? Number(heightCm) : null,
      },
      weight: {
        unit: weightUnit,
        value: Number(weightValue),
      },
      birthday,
      training_age_bucket: trainingAgeBucket,
      strength_frequency_bucket: strengthFrequency,
      motivation_driver: motivationDriver,
      primary_obstacle: obstacle,
      training_location: trainingLocation,
      equipment_tags: equipmentTags,
      movement_restrictions: movementRestrictions,
      strength_experience_level: experienceLevel,
      preferred_workout_duration_minutes: workoutDurationMinutes,
      days_available: daysAvailable,
    };
  }

  async function resolveAccessToken(resolvedName: string): Promise<string | null> {
    const normalizedEmail = normalizeEmailInput(email);
    if (!normalizedEmail) {
      setStatus("Email is required");
      setPhase("account");
      return null;
    }

    if (authMode === "login") {
      const loginRes = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: normalizedEmail, password }),
      });
      if (!loginRes.ok) {
        const loginError = await parseApiError(loginRes, "Login failed");
        setStatus(`Login failed: ${loginError}`);
        setPhase("account");
        return null;
      }
      const token = (await loginRes.json()) as { access_token: string };
      return token.access_token;
    }

    const registerRes = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: normalizedEmail, password, name: resolvedName }),
    });
    if (registerRes.ok) {
      const token = (await registerRes.json()) as { access_token: string };
      return token.access_token;
    }

    const registerError = await parseApiError(registerRes, "Registration failed");
    const looksLikeExistingAccount = registerRes.status === 400 && registerError.toLowerCase().includes("already used");
    if (!looksLikeExistingAccount) {
      const message =
        registerError === "Registration failed" || registerError.startsWith("Registration failed:")
          ? "Registration failed. If the program catalog above shows “unavailable”, the API may not be reachable — ensure Docker containers are running (e.g. docker compose up -d)."
          : `Registration failed: ${registerError}`;
      setStatus(message);
      setPhase("account");
      return null;
    }

    const loginRes = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: normalizedEmail, password }),
    });
    if (!loginRes.ok) {
      const loginError = await parseApiError(loginRes, "Login failed");
      setStatus(`Registration/login failed: ${registerError}; ${loginError}. Use Wipe Test User By Email or password reset.`);
      setPhase("account");
      return null;
    }
    const token = (await loginRes.json()) as { access_token: string };
    return token.access_token;
  }

  async function saveOnboardingProfile(accessToken: string, resolvedName: string): Promise<boolean> {
    const resolvedWeightKg = convertWeightToKg(Number(weightValue), weightUnit);
    const resolvedDays = daysAvailable ?? 3;
    const resolvedSplit = deriveSplitPreference(resolvedDays);
    const resolvedLocation = trainingLocation || "home";
    const resolvedEquipment =
      equipmentTags.length > 0 ? equipmentTags : defaultEquipmentTagsForLocation(resolvedLocation);
    const weakAreas = parseWeakAreas(weakAreasRaw);
    const resolvedWeakAreas = weakAreas.length > 0 ? weakAreas : [];
    const nutritionPhase = primaryGoals.includes("lose_fat") || primaryGoal === "lose_fat" ? "cut" : "maintenance";
    const calories = nutritionPhase === "cut" ? 2200 : 2600;

    const profileRes = await fetch(`${API_BASE_URL}/profile`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accessToken}`,
      },
      body: JSON.stringify({
        name: resolvedName,
        age: deriveAgeFromBirthday(birthday),
        weight: resolvedWeightKg,
        gender: gender || "prefer_not_to_say",
        split_preference: resolvedSplit,
        training_location: resolvedLocation,
        equipment_profile: resolvedEquipment,
        session_time_budget_minutes: workoutDurationMinutes ?? null,
        movement_restrictions: movementRestrictions,
        weak_areas: resolvedWeakAreas,
        onboarding_answers: buildOnboardingAnswers(),
        days_available: resolvedDays,
        nutrition_phase: nutritionPhase,
        calories,
        protein: 180,
        fat: 70,
        carbs: 280,
        selected_program_id: selectedProgramId,
      }),
    });

    if (!profileRes.ok) {
      const detail = await parseApiError(profileRes, "Profile save failed");
      setStatus(`Profile save failed: ${detail}`);
      setPhase("account");
      return false;
    }
    return true;
  }

  async function submitOnboarding(event: FormEvent) {
    event.preventDefault();
    setStatus(authMode === "login" ? "Logging in..." : "Creating account...");
    setPhase("saving");

    try {
      const fullName = [firstName.trim(), lastName.trim()].filter(Boolean).join(" ");
      const resolvedName = fullName || firstName.trim() || "Athlete";

      const accessToken = await resolveAccessToken(resolvedName);
      if (!accessToken) {
        return;
      }

      setAuthToken(accessToken);

      const profileSaved = await saveOnboardingProfile(accessToken, resolvedName);
      if (!profileSaved) {
        return;
      }

      let initialProgramId = selectedProgramId;
      // If the user did not explicitly choose a program, ask the engine and apply its recommendation.
      // This keeps onboarding deterministic while preserving explicit user choice.
      if (!selectedProgramId) {
        try {
          const recommendation = await api.getProgramRecommendation();
          if (
            typeof recommendation.recommended_program_id === "string"
            && recommendation.recommended_program_id
            && recommendation.recommended_program_id !== recommendation.current_program_id
          ) {
            const switchResponse = await api.switchProgram({
              target_program_id: recommendation.recommended_program_id,
              confirm: true,
            });
            initialProgramId = switchResponse.target_program_id;
            setStatus(`Applied recommendation: ${switchResponse.target_program_id}`);
          }
        } catch {
          // non-blocking: fall back to profile/default selection
        }
      }

      setStatus("Creating your workouts...");
      try {
        await api.generateWeek(initialProgramId);
      } catch {
        // keep onboarding successful even if initial pre-generation fails
      }

      // Submit an initial weekly review so the user is not required to do Sunday review before using the app
      try {
        const reviewStatus = await api.getWeeklyReviewStatus();
        const reviewWeightKg = convertWeightToKg(Number(weightValue), weightUnit);
        const reviewCalories = primaryGoals.includes("lose_fat") || primaryGoal === "lose_fat" ? 2200 : 2600;
        await api.submitWeeklyReview({
          body_weight: reviewWeightKg,
          calories: reviewCalories,
          protein: 180,
          fat: 70,
          carbs: 280,
          adherence_score: 5,
          week_start: reviewStatus.week_start,
        });
      } catch {
        // non-blocking: user can still use the app; they may see Sunday review prompt later
      }

      setStatus("Onboarding saved and first plan initialized");
      localStorage.removeItem(ONBOARDING_DRAFT_KEY);
      setHasSavedDraft(false);
      router.push("/today");
    } catch {
      setStatus("Network error during onboarding");
      setPhase("account");
    }
  }

  function clearSavedDraft() {
    localStorage.removeItem(ONBOARDING_DRAFT_KEY);
    setHasSavedDraft(false);
    setStatus("Saved onboarding draft cleared");
  }

  async function wipeTestUserByEmail() {
    const normalizedEmail = normalizeEmailInput(email);
    if (!normalizedEmail) {
      setStatus("Enter an email before wipe-by-email");
      return;
    }

    const confirmed = globalThis.confirm(
      "This will permanently delete the user account for this email and all related data. Continue?",
    );
    if (!confirmed) {
      return;
    }

    setStatus("Wiping test user...");
    try {
      const response = await api.devWipeUser({ email: normalizedEmail, confirmation: "WIPE" });
      clearAuthToken();
      setStatus(response.status === "already_absent" ? "Test user already absent" : "Test user wiped");
    } catch {
      setStatus("Test user wipe failed");
    }
  }

  async function requestPasswordResetForEmail() {
    const normalizedEmail = normalizeEmailInput(email);
    if (!normalizedEmail) {
      setStatus("Enter an email before requesting password reset");
      return;
    }

    setStatus("Requesting password reset...");
    try {
      const response = await api.requestPasswordReset({ email: normalizedEmail });
      if (response.reset_token) {
        setStatus(`Password reset token issued: ${response.reset_token}`);
        return;
      }
      setStatus("Password reset request accepted");
    } catch {
      setStatus("Password reset request failed");
    }
  }

  async function wipeCurrentLoggedInUserData() {
    const confirmed = globalThis.confirm(
      "This will wipe data for the currently authenticated user token stored in this browser. Continue?",
    );
    if (!confirmed) {
      return;
    }

    setStatus("Wiping current logged-in user data...");
    try {
      await api.wipeProfileData();
      clearAuthToken();
      setStatus("Current user data wiped");
    } catch {
      setStatus("Current user wipe failed (log in first or use wipe-by-email)");
    }
  }

  async function resetCurrentLoggedInUserToPhase1() {
    const confirmed = globalThis.confirm(
      "This will clear training history/state for the current logged-in user and reset them to the canonical Phase 1 path. Continue?",
    );
    if (!confirmed) {
      return;
    }

    setStatus("Resetting current logged-in user to clean Phase 1...");
    try {
      await api.resetProfileToPhase1();
      setSelectedProgramId("pure_bodybuilding_phase_1_full_body");
      setDaysAvailable(5);
      setStatus("Current user reset to clean Phase 1 state");
    } catch {
      setStatus("Current user Phase 1 reset failed (log in first or use wipe-by-email)");
    }
  }

  function renderQuestionStep() {
    if (!currentQuestion) {
      return null;
    }

    switch (currentQuestion.id) {
      case "gender":
        return (
          <div className="grid grid-cols-1 gap-2">
            {GENDER_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={gender === option}
                onClick={() => setGender(option)}
                className={`rounded-md border p-4 text-left text-base capitalize transition-colors ${
                  gender === option
                    ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white"
                    : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-100"
                }`}
              >
                {option.replaceAll("_", " ")}
              </button>
            ))}
          </div>
        );
      case "goal":
        return (
          <div className="grid grid-cols-1 gap-2">
            <p className="ui-meta mb-1">Select all that apply.</p>
            {GOAL_OPTIONS.map((option) => {
              const isSelected = primaryGoals.includes(option);
              return (
                <button
                  key={option}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => {
                    setPrimaryGoals((prev) =>
                      isSelected ? prev.filter((g) => g !== option) : [...prev, option],
                    );
                    if (!primaryGoal) setPrimaryGoal(option);
                  }}
                  className={`rounded-md border p-4 text-left text-base capitalize transition-colors ${
                    isSelected
                      ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white"
                      : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-100"
                  }`}
                >
                  {option.replaceAll("_", " ")}
                </button>
              );
            })}
          </div>
        );
      case "height":
        return (
          <div className="space-y-3">
            <div className="flex gap-2">
              <Button type="button" variant={heightUnit === "in" ? "default" : "secondary"} onClick={() => setHeightUnit("in")}>in</Button>
              <Button type="button" variant={heightUnit === "cm" ? "default" : "secondary"} onClick={() => setHeightUnit("cm")}>cm</Button>
            </div>
            {heightUnit === "in" ? (
              <div className="grid grid-cols-2 gap-2">
                <input aria-label="Height feet" className="ui-input" value={heightFeet} onChange={(e) => setHeightFeet(e.target.value)} placeholder="ft" />
                <input aria-label="Height inches" className="ui-input" value={heightInches} onChange={(e) => setHeightInches(e.target.value)} placeholder="in" />
              </div>
            ) : (
              <input aria-label="Height cm" className="ui-input" value={heightCm} onChange={(e) => setHeightCm(e.target.value)} placeholder="cm" />
            )}
          </div>
        );
      case "weight":
        return (
          <div className="space-y-3">
            <div className="flex gap-2">
              <Button type="button" variant={weightUnit === "lbs" ? "default" : "secondary"} onClick={() => setWeightUnit("lbs")}>lbs</Button>
              <Button type="button" variant={weightUnit === "kg" ? "default" : "secondary"} onClick={() => setWeightUnit("kg")}>kg</Button>
            </div>
            <input aria-label="Current weight" className="ui-input" value={weightValue} onChange={(e) => setWeightValue(e.target.value)} placeholder={weightUnit} />
          </div>
        );
      case "birthday":
        return (
          <input aria-label="Birthday" type="date" className="ui-input" value={birthday} onChange={(e) => setBirthday(e.target.value)} />
        );
      case "training_age":
        return (
          <div className="grid grid-cols-1 gap-2">
            {TRAINING_AGE_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={trainingAgeBucket === option}
                onClick={() => setTrainingAgeBucket(option)}
                className={`rounded-md border p-4 text-left text-base transition-colors ${
                  trainingAgeBucket === option
                    ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white"
                    : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-100"
                }`}
              >
                {TRAINING_AGE_LABELS[option]}
              </button>
            ))}
          </div>
        );
      case "frequency":
        return (
          <div className="grid grid-cols-1 gap-2">
            {FREQUENCY_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={strengthFrequency === option}
                onClick={() => setStrengthFrequency(option)}
                className={`rounded-md border p-4 text-left text-base transition-colors ${
                  strengthFrequency === option
                    ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white"
                    : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-100"
                }`}
              >
                {FREQUENCY_LABELS[option]}
              </button>
            ))}
          </div>
        );
      case "motivation":
        return (
          <div className="grid grid-cols-1 gap-2">
            {MOTIVATION_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={motivationDriver === option}
                onClick={() => setMotivationDriver(option)}
                className={`rounded-md border p-4 text-left text-base capitalize transition-colors ${
                  motivationDriver === option
                    ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white"
                    : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-100"
                }`}
              >
                {option.replaceAll("_", " ")}
              </button>
            ))}
          </div>
        );
      case "obstacle":
        return (
          <div className="grid grid-cols-1 gap-2">
            {OBSTACLE_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={obstacle === option}
                onClick={() => setObstacle(option)}
                className={`rounded-md border p-4 text-left text-base transition-colors ${
                  obstacle === option
                    ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white"
                    : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-100"
                }`}
              >
                {option.replaceAll("_", " ")}
              </button>
            ))}
          </div>
        );
      case "location":
        return (
          <div className="grid grid-cols-1 gap-2">
            {LOCATION_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={trainingLocation === option}
                onClick={() => setTrainingLocation(option)}
                className={`rounded-md border p-4 text-left text-base capitalize transition-colors ${
                  trainingLocation === option
                    ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white"
                    : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-100"
                }`}
              >
                {option}
              </button>
            ))}
          </div>
        );
      case "gym_setup":
        return (
          <div className="space-y-3">
            <p className="text-xs text-zinc-400">
              We use this to suggest exercises that match your equipment. Select all that apply.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {EQUIPMENT_TAGS.map((tag) => {
                const active = equipmentTags.includes(tag);
                return (
                  <button
                    key={tag}
                    type="button"
                    aria-pressed={active}
                    onClick={() =>
                      setEquipmentTags((prev) =>
                        active ? prev.filter((t) => t !== tag) : [...prev, tag],
                      )
                    }
                    className={`rounded-full border px-3 py-1 text-[11px] transition-colors ${
                      active
                        ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white"
                        : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-100"
                    }`}
                  >
                    {tag}
                  </button>
                );
              })}
            </div>
          </div>
        );
      case "movement_restrictions":
        return (
          <div className="space-y-3">
            <p className="text-xs text-zinc-400">
              Choose any movements you need to limit right now. Leave everything unselected for “no restrictions”.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {MOVEMENT_RESTRICTION_OPTIONS.map((r) => {
                const active = movementRestrictions.includes(r);
                return (
                  <button
                    key={r}
                    type="button"
                    aria-pressed={active}
                    onClick={() =>
                      setMovementRestrictions((prev) =>
                        active ? prev.filter((x) => x !== r) : [...prev, r],
                      )
                    }
                    className={`rounded-full border px-3 py-1 text-[11px] transition-colors ${
                      active
                        ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white"
                        : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-100"
                    }`}
                  >
                    {MOVEMENT_RESTRICTION_LABELS[r]}
                  </button>
                );
              })}
            </div>
          </div>
        );
      case "experience":
        return (
          <div className="grid grid-cols-1 gap-2">
            {EXPERIENCE_LEVEL_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={experienceLevel === option}
                onClick={() => setExperienceLevel(option)}
                className={`rounded-md border p-4 text-left text-base capitalize transition-colors ${
                  experienceLevel === option
                    ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white"
                    : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-100"
                }`}
              >
                {option}
              </button>
            ))}
          </div>
        );
      case "duration":
        return (
          <div className="grid grid-cols-1 gap-2">
            {DURATION_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={workoutDurationMinutes === option}
                onClick={() => setWorkoutDurationMinutes(option)}
                className={`rounded-md border p-4 text-left text-base transition-colors ${
                  workoutDurationMinutes === option
                    ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white"
                    : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-100"
                }`}
              >
                {option} minutes
              </button>
            ))}
          </div>
        );
      case "days":
        return (
          <div className="grid grid-cols-2 gap-2">
            {DAYS_OPTIONS.map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={daysAvailable === option}
                onClick={() => setDaysAvailable(option)}
                className={`rounded-md border p-4 text-left text-base transition-colors ${
                  daysAvailable === option
                    ? "border-[var(--ui-edge-active)] bg-[var(--ui-accent-active)] text-white"
                    : "border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] text-zinc-100"
                }`}
              >
                {option} days
              </button>
            ))}
          </div>
        );
      case "name":
        return (
          <div className="space-y-2">
            <input aria-label="First name" className="ui-input" value={firstName} onChange={(e) => setFirstName(e.target.value)} placeholder="First name" />
            <input aria-label="Last name" className="ui-input" value={lastName} onChange={(e) => setLastName(e.target.value)} placeholder="Last name (optional)" />
          </div>
        );
      default:
        return null;
    }
  }

  function renderProgress(current: number, total: number) {
    const segments = Array.from({ length: total + 1 }, (_, segment) => segment);
    return (
      <div className="flex gap-1">
        {segments.map((segment) => (
          <span
            key={`segment-${segment}`}
            className={`h-1.5 flex-1 rounded-full ${segment <= current ? "bg-[var(--ui-edge-active)]" : "bg-[var(--ui-edge-idle)]"}`}
          />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <h1 className="ui-title-page">Onboarding</h1>

      <div className="main-card main-card--module main-card--accent spacing-grid spacing-grid--tight">
        <div className="telemetry-header">
          <p className="telemetry-kicker">Adaptive Onboarding</p>
          <p className="telemetry-status">
            <span className={`status-dot status-dot--${statusTone}`} /> {status}
          </p>
        </div>
        <p className="telemetry-meta">{programCatalogStatus}</p>
        {hasSavedDraft ? (
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <p className="telemetry-meta">Draft autosave active on this browser.</p>
            <Button type="button" variant="secondary" onClick={clearSavedDraft}>Clear Saved Draft</Button>
          </div>
        ) : null}
      </div>

      {phase === "intro" ? (
        <div className="main-card main-card--module spacing-grid">
          {renderProgress(introIndex, INTRO_SLIDES.length - 1)}
          <p className="telemetry-kicker">Welcome</p>
          <h2 className="text-2xl font-semibold text-zinc-100">{INTRO_SLIDES[introIndex].headline}</h2>
          <p className="text-lg text-zinc-300">{INTRO_SLIDES[introIndex].subheadline}</p>
          <p className="telemetry-meta">{INTRO_SLIDES[introIndex].body}</p>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            <Button
              type="button"
              onClick={() => {
                if (introIndex < INTRO_SLIDES.length - 1) {
                  setIntroIndex((prev) => prev + 1);
                  return;
                }
                setPhase("questions");
                setStatus("Questionnaire started");
              }}
            >
              <span className="inline-flex items-center gap-2">
                <UiIcon name="onboarding" className="ui-icon--action" />
                {introIndex < INTRO_SLIDES.length - 1 ? "Next Slide" : "Get Started"}
              </span>
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setAuthMode("login");
                setPhase("account");
                setStatus("Login mode");
              }}
            >
              <span className="inline-flex items-center gap-2">
                <UiIcon name="login" className="ui-icon--action" />
                I already have an account
              </span>
            </Button>
          </div>
        </div>
      ) : null}

      {phase === "questions" ? (
        <div className="main-card main-card--module spacing-grid">
          {renderProgress(questionIndex, questionSteps.length - 1)}
          <p className="telemetry-kicker">Step {questionIndex + 1} of {questionSteps.length}</p>
          <h2 className="text-2xl font-semibold text-zinc-100">{currentQuestion?.title}</h2>
          {questionIndex === 0 ? (
            <p className="text-xs text-zinc-400">Your answers are saved to your profile and used to tailor your plan: days per week, equipment, and recovery settings.</p>
          ) : null}
          {renderQuestionStep()}
          <div className="grid grid-cols-1 gap-2 md:grid-cols-3">
            <Button type="button" variant="secondary" onClick={goToPreviousQuestion}>Back</Button>
            <Button
              type="button"
              variant="secondary"
              onClick={skipCurrentQuestion}
              disabled={!currentQuestion?.skipAllowed}
            >
              Skip
            </Button>
            <Button type="button" onClick={goToNextQuestion} disabled={!isCurrentQuestionValid()}>
              Next
            </Button>
          </div>
        </div>
      ) : null}

      {phase === "account" ? (
        <form className="main-card main-card--module spacing-grid" onSubmit={submitOnboarding}>
          {renderProgress(questionSteps.length - 1, questionSteps.length - 1)}
          <p className="telemetry-kicker">Create Account</p>
          {(status.toLowerCase().includes("failed") || status.toLowerCase().includes("error")) && status !== "Idle" ? (
            <div className="rounded-md border border-red-500/50 bg-red-950/30 p-3 text-sm text-red-200" role="alert">
              {status}
            </div>
          ) : null}
          <input aria-label="Email address" className="ui-input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
          <div className="space-y-2">
            <input
              className="ui-input"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              aria-label="Password"
            />
            <button
              className="h-8 w-full rounded-md border border-[var(--ui-edge-idle)] bg-[var(--ui-surface-1)] px-3 text-xs text-zinc-100 transition-colors hover:border-[var(--ui-edge-active)]"
              onClick={() => setShowPassword((prev) => !prev)}
              type="button"
            >
              {showPassword ? "Hide Password" : "Show Password"}
            </button>
          </div>

          <div className="space-y-1">
            <label htmlFor="program-select" className="ui-meta">Program</label>
            <select
              id="program-select"
              className="ui-select"
              value={selectedProgramId ?? ""}
              onChange={(e) => setSelectedProgramId(e.target.value || null)}
              aria-label="Program"
            >
              <option value="">Default - trainer recommendation</option>
              {visiblePrograms.map((p) => (
                <option key={p.id} value={p.id}>
                  {getProgramDisplayName(p)}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <label htmlFor="weak-areas" className="ui-meta">Weak Areas (optional, comma-separated)</label>
            <input
              id="weak-areas"
              className="ui-input"
              value={weakAreasRaw}
              onChange={(event) => setWeakAreasRaw(event.target.value)}
              placeholder="chest, hamstrings"
            />
          </div>

          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setAuthMode(authMode === "register" ? "login" : "register");
                setStatus(authMode === "register" ? "Switched to login mode" : "Switched to register mode");
              }}
            >
              {authMode === "register" ? "Use Login Instead" : "Create New Account Instead"}
            </Button>
            <Button type="submit">
              <span className="inline-flex items-center gap-2">
                <UiIcon name="save" className="ui-icon--action" />
                {authMode === "register" ? "Continue" : "Log In and Continue"}
              </span>
            </Button>
          </div>
        </form>
      ) : null}

      {phase === "saving" ? (
        <div className="main-card main-card--module spacing-grid">
          <p className="telemetry-kicker">Finalizing</p>
          <h2 className="text-2xl font-semibold text-zinc-100">{status}</h2>
          <p className="telemetry-meta">
            {status.toLowerCase().includes("failed") || status.toLowerCase().includes("error")
              ? "Fix any error above and try again. Your account may already exist — try logging in or use Developer Tools to wipe the test user."
              : "Saving profile, applying constraints, and generating your initial training week."}
          </p>
        </div>
      ) : null}

      <div className="rounded-md border border-red-700/40 bg-red-950/20 p-3">
        <p className="telemetry-kicker">Developer Tools</p>
        <p className="telemetry-meta">Reset onboarding/program test state without leaving this screen.</p>
        <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
          <Button type="button" variant="secondary" onClick={wipeTestUserByEmail}>
            <span className="inline-flex items-center gap-2">
              <UiIcon name="reset" className="ui-icon--action" />
              Wipe Test User By Email
            </span>
          </Button>
          <Button type="button" variant="secondary" onClick={resetCurrentLoggedInUserToPhase1}>
            <span className="inline-flex items-center gap-2">
              <UiIcon name="reset" className="ui-icon--action" />
              Reset Current User to Clean Phase 1
            </span>
          </Button>
          <Button type="button" variant="secondary" onClick={wipeCurrentLoggedInUserData}>
            <span className="inline-flex items-center gap-2">
              <UiIcon name="reset" className="ui-icon--action" />
              Wipe Current Logged-In User Data
            </span>
          </Button>
          <Button type="button" variant="secondary" onClick={requestPasswordResetForEmail}>
            <span className="inline-flex items-center gap-2">
              <UiIcon name="reset" className="ui-icon--action" />
              Request Password Reset Token
            </span>
          </Button>
        </div>
      </div>
    </div>
  );
}
