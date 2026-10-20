/** User-declared equipment. These values do not authorize prescription changes. */
export type InventoryUnit = 'kg' | 'lb';
export type InventoryKind = 'dumbbell' | 'barbell' | 'machine_stack' | 'bodyweight';
export type InventoryWeight = {weight: number; count: number};
export type InventorySetup = {
  key: string;
  label: string;
  kind: InventoryKind;
  unit: InventoryUnit;
  weights: InventoryWeight[];
  plates: InventoryWeight[];
  bar_weight: number | null;
  stack: {minimum: number; maximum: number; increment: number} | null;
  min_load: number | null;
  max_load: number | null;
  setup_note: string;
};
export type StrengthReport = {
  report_id: string;
  variant_id: string;
  setup_key: string;
  kind: '1rm' | 'e1rm';
  load: number;
  unit: InventoryUnit;
  observed_on: string;
  confirmed: boolean;
  method_reference: string | null;
  /** Server-owned binding, returned unchanged for existing reports. */
  setup_fingerprint?: string | null;
};
export type LocationProfile = {
  location_id: string;
  location_name: string;
  equipment: string[];
  unavailable_variants: string[];
  setups: InventorySetup[];
  assignments: Record<string, string>;
  strength_reports: StrengthReport[];
};
export type InventoryDocument = {version: string; revision: number; profile: LocationProfile | null};
export type InventoryVariant = {id: string; name: string; implement: string; basis: string};
