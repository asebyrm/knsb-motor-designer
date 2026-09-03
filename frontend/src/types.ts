export interface GrainSpec {
  type: "bates" | "tubular" | "endburner";
  outer_diameter: number;
  core_diameter: number;
  segment_length: number;
  segment_count: number;
  segment_spacing: number;
}

export interface NozzleSpec {
  throat_diameter: number;
  expansion_ratio: number;
  divergence_half_angle_deg: number;
  convergence_half_angle_deg: number;
  efficiency: number;
  throat_length: number;
  erosion: { enabled: boolean; coefficient_mm_s: number; exponent: number };
}

export interface DesignDoc {
  schema_version: number;
  name: string;
  prefix: string;
  designer: string;
  propellant: { id: string; density_factor?: number; c_star_efficiency?: number };
  grain: GrainSpec;
  nozzle: NozzleSpec;
  case: {
    material_id: string;
    inner_diameter: number;
    wall_thickness: number;
    length: number | null;
    print_method: "fdm" | "sls" | "machined";
  };
  liner: { material_id: string; thickness: number } | null;
  bulkhead: { material_id: string; thickness: number };
  assembly: { forward_gap: number; aft_gap: number };
  environment: { ambient_pressure: number };
  meop_bar: number;
  bolt: { diameter: number; shear_strength: number };
}

export interface WarningItem {
  code: string;
  level: "info" | "warning" | "danger";
  params: Record<string, unknown>;
}

export interface SimResult {
  summary: Record<string, number | string | null>;
  structure: Record<string, unknown>;
  thermal: Record<string, unknown>;
  assembly: {
    parts: Array<{
      name: string;
      material_id: string;
      x_start_mm: number;
      x_end_mm: number;
      outer_diameter_mm: number;
      inner_diameter_mm: number;
      mass_g: number;
    }>;
    bom: Array<Record<string, number | string | null>>;
    fit_warnings: WarningItem[];
    free_volume_cm3: number;
    lstar_mm: number;
  };
  warnings: WarningItem[];
  is_safe: boolean;
  export_locked: boolean;
  max_warning_level: "info" | "warning" | "danger";
  series: Record<string, number[]>;
  grain_cross_section_svg: string;
  engine_version: string;
}

export interface MissionCandidate {
  outer_diameter: number;
  core_diameter: number;
  segment_length: number;
  segment_count: number;
  throat_diameter: number;
  designation: string;
  apogee: number;
  apogee_low: number;
  apogee_high: number;
  peak_pressure_bar: number;
  fos: number;
  min_j: number;
  rail_exit_velocity: number;
  max_accel_g: number;
  thrust_to_weight: number;
  propellant_mass: number;
  motor_mass: number;
  total_length: number;
  total_impulse: number;
  burn_time: number;
  feasible: boolean;
  warnings: WarningItem[];
  thrust_curve: number[][];
}

export interface MissionResult {
  feasible: boolean;
  candidates: MissionCandidate[];
  binding_constraint: string | null;
  suggestion: Record<string, unknown> | null;
  iterations: number;
  elapsed_s: number;
  uncertainty_fraction: number;
  note_key: string;
}
