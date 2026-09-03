/**
 * Single source of truth for every editable parameter, every result metric and
 * every derived (non-editable) measure. The parameter form, the engine
 * cross-section editable labels and the i18n tooltip-coverage test all read this.
 */

export type UnitKind =
  | "length_mm"
  | "length_m"
  | "pressure_bar"
  | "pressure_pa"
  | "angle_deg"
  | "ratio"
  | "count"
  | "mass_kg"
  | "accel_g"
  | "rate_mm_s"
  | "none";

export interface FieldDef {
  id: string;
  group: string;
  path: string; // dot path into DesignDoc
  kind: "number" | "select" | "bool";
  unit: UnitKind;
  basic?: boolean; // shown in Basic mode
  options?: string[]; // for select
  step?: number;
  min?: number;
  max?: number;
}

export const FIELDS: FieldDef[] = [
  // propellant
  { id: "propellant_id", group: "propellant", path: "propellant.id", kind: "select", unit: "none", basic: true },
  { id: "density_factor", group: "calibration", path: "propellant.density_factor", kind: "number", unit: "ratio", step: 0.01, min: 0.7, max: 1 },
  { id: "c_star_efficiency", group: "calibration", path: "propellant.c_star_efficiency", kind: "number", unit: "ratio", step: 0.01, min: 0.7, max: 1 },
  // grain
  { id: "grain_type", group: "grain", path: "grain.type", kind: "select", unit: "none", basic: true, options: ["bates", "tubular", "endburner"] },
  { id: "outer_diameter", group: "grain", path: "grain.outer_diameter", kind: "number", unit: "length_mm", basic: true, step: 1, min: 5 },
  { id: "core_diameter", group: "grain", path: "grain.core_diameter", kind: "number", unit: "length_mm", basic: true, step: 1, min: 1 },
  { id: "segment_length", group: "grain", path: "grain.segment_length", kind: "number", unit: "length_mm", basic: true, step: 1, min: 5 },
  { id: "segment_count", group: "grain", path: "grain.segment_count", kind: "number", unit: "count", basic: true, step: 1, min: 1, max: 12 },
  { id: "segment_spacing", group: "grain", path: "grain.segment_spacing", kind: "number", unit: "length_mm", step: 0.5, min: 0 },
  // nozzle
  { id: "throat_diameter", group: "nozzle", path: "nozzle.throat_diameter", kind: "number", unit: "length_mm", basic: true, step: 0.5, min: 2 },
  { id: "expansion_ratio", group: "nozzle", path: "nozzle.expansion_ratio", kind: "number", unit: "ratio", basic: true, step: 0.25, min: 1 },
  { id: "divergence_half_angle", group: "nozzle", path: "nozzle.divergence_half_angle_deg", kind: "number", unit: "angle_deg", step: 1, min: 8, max: 25 },
  { id: "convergence_half_angle", group: "nozzle", path: "nozzle.convergence_half_angle_deg", kind: "number", unit: "angle_deg", step: 1, min: 20, max: 60 },
  { id: "nozzle_efficiency", group: "nozzle", path: "nozzle.efficiency", kind: "number", unit: "ratio", step: 0.01, min: 0.8, max: 1 },
  { id: "throat_length", group: "nozzle", path: "nozzle.throat_length", kind: "number", unit: "length_mm", step: 0.5, min: 0 },
  { id: "erosion_enabled", group: "nozzle", path: "nozzle.erosion.enabled", kind: "bool", unit: "none" },
  { id: "erosion_coefficient", group: "nozzle", path: "nozzle.erosion.coefficient_mm_s", kind: "number", unit: "rate_mm_s", step: 0.01, min: 0 },
  { id: "erosion_exponent", group: "nozzle", path: "nozzle.erosion.exponent", kind: "number", unit: "ratio", step: 0.05, min: 0 },
  // case
  { id: "case_material", group: "case", path: "case.material_id", kind: "select", unit: "none", basic: true },
  { id: "case_inner_diameter", group: "case", path: "case.inner_diameter", kind: "number", unit: "length_mm", basic: true, step: 1, min: 6 },
  { id: "case_wall_thickness", group: "case", path: "case.wall_thickness", kind: "number", unit: "length_mm", basic: true, step: 0.25, min: 0.5 },
  { id: "case_length", group: "case", path: "case.length", kind: "number", unit: "length_mm", step: 1, min: 0 },
  { id: "print_method", group: "case", path: "case.print_method", kind: "select", unit: "none", basic: true, options: ["fdm", "sls", "machined"] },
  // liner
  { id: "liner_material", group: "liner", path: "liner.material_id", kind: "select", unit: "none", basic: true },
  { id: "liner_thickness", group: "liner", path: "liner.thickness", kind: "number", unit: "length_mm", basic: true, step: 0.25, min: 0 },
  // bulkhead
  { id: "bulkhead_material", group: "bulkhead", path: "bulkhead.material_id", kind: "select", unit: "none" },
  { id: "bulkhead_thickness", group: "bulkhead", path: "bulkhead.thickness", kind: "number", unit: "length_mm", step: 0.5, min: 1 },
  // assembly / env
  { id: "forward_gap", group: "assembly", path: "assembly.forward_gap", kind: "number", unit: "length_mm", step: 0.5, min: 0 },
  { id: "aft_gap", group: "assembly", path: "assembly.aft_gap", kind: "number", unit: "length_mm", step: 0.5, min: 0 },
  { id: "ambient_pressure", group: "environment", path: "environment.ambient_pressure", kind: "number", unit: "pressure_pa", step: 1000, min: 1000 },
  { id: "meop_bar", group: "case", path: "meop_bar", kind: "number", unit: "pressure_bar", basic: true, step: 1, min: 1 },
  { id: "bolt_diameter", group: "bulkhead", path: "bolt.diameter", kind: "number", unit: "length_mm", step: 0.5, min: 2 },
  { id: "bolt_shear_strength", group: "bulkhead", path: "bolt.shear_strength", kind: "number", unit: "pressure_pa", step: 1e7, min: 1e7 },
];

export const MISSION_FIELDS: FieldDef[] = [
  { id: "dry_mass", group: "mission", path: "dry_mass", kind: "number", unit: "mass_kg", basic: true, step: 0.1, min: 0.1 },
  { id: "body_diameter", group: "mission", path: "body_diameter", kind: "number", unit: "length_mm", basic: true, step: 1, min: 10 },
  { id: "drag_coefficient", group: "mission", path: "drag_coefficient", kind: "number", unit: "ratio", basic: true, step: 0.01, min: 0.1, max: 1.5 },
  { id: "target_apogee", group: "mission", path: "target_apogee", kind: "number", unit: "length_m", basic: true, step: 10, min: 10 },
  { id: "rail_length", group: "mission", path: "rail_length", kind: "number", unit: "length_m", step: 0.1, min: 0.5 },
  { id: "max_accel_g", group: "mission", path: "max_accel_g", kind: "number", unit: "accel_g", step: 1, min: 3 },
  { id: "launch_altitude", group: "mission", path: "launch_altitude", kind: "number", unit: "length_m", step: 10, min: 0 },
];

/** Result metrics — must all have metric.<id> + info.metric.<id>. */
export const METRICS = [
  "total_impulse", "average_thrust", "peak_thrust", "burn_time", "peak_pressure",
  "specific_impulse", "propellant_mass", "total_mass", "mass_ratio", "designation",
  "fos", "min_j", "lstar", "thrust_to_weight", "kn", "motor_mass", "inert_mass",
  "total_length", "cg_initial", "cg_burnout",
] as const;

/** Derived, non-editable measures shown on the drawing — need info.derived.<id>. */
export const DERIVED = [
  "web", "total_length", "lstar", "free_volume", "ullage", "cg",
  "port_diameter", "exit_diameter", "grain_length",
] as const;

export const ACTIONS = [
  "make_neutral", "optimum_expansion", "estimate_from_altitude", "run_mission",
  "toggle_units", "apply_suggestion",
] as const;
