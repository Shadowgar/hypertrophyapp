import { getToken } from '@/lib/api';
import { accountScope, canonicalLoad } from '@/lib/appearance';

export const DRAFT_KEY = 'hypertrophy_onboarding_draft_v1';
export const EQUIPMENT = [['barbell', 'Barbell'], ['bench', 'Bench'], ['dumbbell', 'Dumbbells'], ['cable', 'Cable station'], ['machine', 'Machines'], ['bands', 'Bands'], ['bodyweight', 'Bodyweight']] as const;
export const RESTRICTIONS = [['overhead_pressing', 'Overhead pressing limitations'], ['deep_knee_flexion', 'Squat/lunge knee-flexion limitations']] as const;
export const OPTIONAL_OPTIONS = {
  gender: [['male', 'Male'], ['female', 'Female'], ['prefer_not_to_say', 'Prefer not to say']],
  trainingAgeBucket: [['getting_started', 'Getting started'], ['less_than_1_year', 'Less than 1 year'], ['1_2_years', '1 to 2 years'], ['2_5_years', '2 to 5 years'], ['more_than_5_years', 'More than 5 years']],
  strengthFrequency: [['never', 'Never'], ['once_in_a_while', 'Once in a while'], ['1_2_per_week', '1 to 2 times per week'], ['3_4_per_week', '3 to 4 times per week'], ['5_plus_per_week', '5+ per week']],
  motivationDriver: [['accountability', 'Accountability'], ['competition', 'Competition'], ['fun', 'Fun'], ['self_motivated', 'Self motivated']],
  obstacle: [['lack_of_motivation', 'Lack of motivation'], ['not_sure_what_to_do', 'Not sure what to do'], ['not_enough_time', 'Not enough time'], ['dealing_with_injury', 'Dealing with injury'], ['something_else', 'Something else'], ['none_right_now', 'None right now']],
  experienceLevel: [['beginner', 'Beginner'], ['intermediate', 'Intermediate'], ['advanced', 'Advanced']],
} as const;
export const GOALS = [['build_muscle', 'Build muscle'], ['lose_fat', 'Lose fat'], ['gain_strength', 'Gain strength'], ['improve_overall_health', 'Improve overall health'], ['improve_performance', 'Improve performance'], ['something_else', 'Something else']] as const;

export type SetupAnswers = {
  age: string; weightValue: string; weightUnit: 'lb' | 'kg'; birthday: string;
  heightUnit: 'in' | 'cm'; heightFeet: string; heightInches: string; heightCm: string;
  gender: string; primaryGoals: string[]; trainingAgeBucket: string; strengthFrequency: string;
  motivationDriver: string; obstacle: string; experienceLevel: string;
  trainingLocation: string; equipmentTags: string[]; movementRestrictions: string[];
  workoutDurationMinutes: string; daysAvailable: string; weakAreasRaw: string;
  selectedProgramId: string | null; chooseForMeFamily: 'full_body' | 'upper_lower' | 'push_pull';
};
export const emptyAnswers: SetupAnswers = {
  age: '', weightValue: '', weightUnit: 'lb', birthday: '', heightUnit: 'in', heightFeet: '', heightInches: '', heightCm: '',
  gender: '', primaryGoals: [], trainingAgeBucket: '', strengthFrequency: '', motivationDriver: '', obstacle: '', experienceLevel: '',
  trainingLocation: '', equipmentTags: [], movementRestrictions: [], workoutDurationMinutes: '', daysAvailable: '', weakAreasRaw: '',
  selectedProgramId: null, chooseForMeFamily: 'full_body',
};
const privateFields = new Set(['age', 'weightValue', 'birthday', 'heightFeet', 'heightInches', 'heightCm']);

// Preserve the former non-private draft inputs, never credentials, identity,
// measurements or nutrition targets. A reload requires private values again.
export function browserDraft(answers: SetupAnswers) {
  return Object.fromEntries(Object.entries(answers).filter(([key]) => !privateFields.has(key)));
}

// Draft persistence is optional and must never decide whether server setup succeeded.
export function readCachedDraft(): string | null | undefined {
  try {
    const token = getToken(); const owner = token ? accountScope(token) : 'guest';
    const savedOwner = localStorage.getItem(`${DRAFT_KEY}.owner`);
    if (token && (!owner || savedOwner !== owner)) return null;
    if (!token && savedOwner && savedOwner !== 'guest') return null;
    return localStorage.getItem(DRAFT_KEY);
  } catch { return undefined; }
}

export function writeCachedDraft(answers: SetupAnswers): boolean {
  try { localStorage.setItem(`${DRAFT_KEY}.owner`, getToken() ? accountScope(getToken()) ?? 'unrecoverable' : 'guest'); localStorage.setItem(DRAFT_KEY, JSON.stringify(browserDraft(answers))); return true; } catch { return false; }
}

export function discardCachedDraft(): boolean {
  try { localStorage.removeItem(DRAFT_KEY); localStorage.removeItem(`${DRAFT_KEY}.owner`); return true; } catch { return false; }
}

export function readDraft(raw: string): SetupAnswers | null {
  try {
    const value = JSON.parse(raw) as Record<string, unknown>;
    if (!value || typeof value !== 'object') return null;
    const result = { ...emptyAnswers };
    for (const key of ['trainingLocation', 'weakAreasRaw', 'daysAvailable', 'workoutDurationMinutes'] as const) {
      if (typeof value[key] === 'string' || typeof value[key] === 'number') result[key] = String(value[key]);
    }
    for (const key of Object.keys(OPTIONAL_OPTIONS) as Array<keyof typeof OPTIONAL_OPTIONS>) {
      if (OPTIONAL_OPTIONS[key].some(([choice]) => choice === value[key])) result[key] = String(value[key]);
    }
    for (const [key, choices] of [['equipmentTags', EQUIPMENT], ['movementRestrictions', RESTRICTIONS], ['primaryGoals', GOALS]] as const) {
      if (Array.isArray(value[key])) result[key] = (value[key] as unknown[]).filter((choice): choice is string => typeof choice === 'string' && choices.some(([allowed]) => allowed === choice));
    }
    if (result.primaryGoals.length === 0 && GOALS.some(([goal]) => goal === value.primaryGoal)) result.primaryGoals = [String(value.primaryGoal)];
    if (typeof value.selectedProgramId === 'string') result.selectedProgramId = value.selectedProgramId || null;
    if (value.weightUnit === 'kg') result.weightUnit = 'kg';
    if (value.heightUnit === 'cm') result.heightUnit = 'cm';
    if (value.chooseForMeFamily === 'upper_lower' || value.chooseForMeFamily === 'push_pull') result.chooseForMeFamily = value.chooseForMeFamily;
    return result;
  } catch { return null; }
}

export function validBasics(answers: SetupAnswers): boolean {
  const age = Number(answers.age), weight = Number(answers.weightValue), days = Number(answers.daysAvailable);
  return answers.age.trim() !== '' && Number.isInteger(age) && age >= 14 && age <= 90
    && answers.weightValue.trim() !== '' && Number.isFinite(weight) && weight > 0
    && Number.isInteger(days) && days >= 2 && days <= 5
    && (answers.workoutDurationMinutes === '' || (Number(answers.workoutDurationMinutes) >= 15 && Number(answers.workoutDurationMinutes) <= 240));
}

export function setupPayload(answers: SetupAnswers, name: string, targets: Record<string, string>) {
  if (!validBasics(answers) || !name.trim()) throw new Error('Complete the required setup answers before saving.');
  const present = (value: string) => value.trim() || null;
  const numeric = (value: string) => value.trim() === '' ? null : Number(value);
  const days = Number(answers.daysAvailable);
  // Existing compatibility mapping is retained; it is not generation or consent.
  const split = days <= 3 ? 'full_body' : days === 4 ? 'upper_lower' : 'ppl';
  const time = numeric(answers.workoutDurationMinutes);
  const weakAreas = answers.weakAreasRaw.split(',').map(value => value.trim().toLowerCase()).filter(Boolean);
  return {
    name: name.trim(), age: Number(answers.age), weight: canonicalLoad(Number(answers.weightValue), answers.weightUnit),
    gender: answers.gender, split_preference: split, days_available: days,
    training_location: present(answers.trainingLocation), equipment_profile: answers.equipmentTags,
    session_time_budget_minutes: time, movement_restrictions: answers.movementRestrictions, weak_areas: weakAreas,
    selected_program_id: answers.selectedProgramId, program_selection_mode: answers.selectedProgramId ? 'manual' : 'auto',
    choose_for_me_family: answers.selectedProgramId ? null : answers.chooseForMeFamily,
    onboarding_answers: {
      gender: present(answers.gender), primary_goal: answers.primaryGoals[0] ?? null, primary_goals: answers.primaryGoals,
      height: { unit: answers.heightUnit, feet: answers.heightUnit === 'in' ? numeric(answers.heightFeet) : null, inches: answers.heightUnit === 'in' ? numeric(answers.heightInches) : null, cm: answers.heightUnit === 'cm' ? numeric(answers.heightCm) : null },
      weight: { unit: answers.weightUnit === 'lb' ? 'lbs' : 'kg', value: Number(answers.weightValue) }, birthday: present(answers.birthday),
      training_age_bucket: present(answers.trainingAgeBucket), strength_frequency_bucket: present(answers.strengthFrequency), motivation_driver: present(answers.motivationDriver), primary_obstacle: present(answers.obstacle),
      training_location: present(answers.trainingLocation), equipment_tags: answers.equipmentTags, movement_restrictions: answers.movementRestrictions,
      strength_experience_level: present(answers.experienceLevel), preferred_workout_duration_minutes: time, days_available: days,
    },
    choose_for_me_diagnostics: {
      readiness: { training_age_bucket: present(answers.trainingAgeBucket), strength_frequency: present(answers.strengthFrequency), motivation_driver: present(answers.motivationDriver), obstacle: present(answers.obstacle) },
      movement_screen: { movement_restrictions: answers.movementRestrictions, experience_level: present(answers.experienceLevel) },
      recovery_profile: { preferred_workout_duration_minutes: time, days_available: days, session_time_budget_minutes: time },
      weak_spot_profile: { weak_areas: weakAreas }, equipment_constraints: { training_location: present(answers.trainingLocation), equipment_profile: answers.equipmentTags },
    },
    ...Object.fromEntries(Object.entries(targets).filter(([, value]) => value.trim() !== '').map(([key, value]) => [key, Number(value)])),
  };
}
