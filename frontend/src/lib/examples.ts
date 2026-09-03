import type { DesignDoc } from "../types";

type Partial2 = Partial<DesignDoc>;

/** Mirrors backend core/examples.py so the UI menu and the regression case agree. */
export const EXAMPLES: { key: string; design: Partial2 }[] = [
  {
    key: "reference",
    design: {
      name: "Reference tube",
      grain: {
        type: "tubular",
        outer_diameter: 0.0858,
        core_diameter: 0.03459,
        segment_length: 0.14721,
        segment_count: 1,
        segment_spacing: 0,
      },
      nozzle: {
        throat_diameter: 0.017298,
        expansion_ratio: 4,
        divergence_half_angle_deg: 15,
        convergence_half_angle_deg: 45,
        efficiency: 0.95,
        throat_length: 0.005,
        erosion: { enabled: false, coefficient_mm_s: 0.05, exponent: 0.8 },
      },
      case: {
        material_id: "al6061_t6",
        inner_diameter: 0.09,
        wall_thickness: 0.004,
        length: null,
        print_method: "machined",
      },
      liner: { material_id: "graphite", thickness: 0.003 },
      meop_bar: 15,
    },
  },
  {
    key: "small",
    design: {
      name: "Small test motor",
      grain: {
        type: "bates",
        outer_diameter: 0.038,
        core_diameter: 0.014,
        segment_length: 0.064,
        segment_count: 1,
        segment_spacing: 0,
      },
      nozzle: {
        throat_diameter: 0.0085,
        expansion_ratio: 4.5,
        divergence_half_angle_deg: 15,
        convergence_half_angle_deg: 45,
        efficiency: 0.95,
        throat_length: 0.004,
        erosion: { enabled: false, coefficient_mm_s: 0.05, exponent: 0.8 },
      },
      case: {
        material_id: "pa12",
        inner_diameter: 0.044,
        wall_thickness: 0.004,
        length: null,
        print_method: "sls",
      },
      meop_bar: 45,
    },
  },
  {
    key: "mid",
    design: {
      name: "Mid flight motor",
      grain: {
        type: "bates",
        outer_diameter: 0.054,
        core_diameter: 0.02,
        segment_length: 0.091,
        segment_count: 3,
        segment_spacing: 0.003,
      },
      nozzle: {
        throat_diameter: 0.0135,
        expansion_ratio: 5,
        divergence_half_angle_deg: 15,
        convergence_half_angle_deg: 45,
        efficiency: 0.95,
        throat_length: 0.006,
        erosion: { enabled: false, coefficient_mm_s: 0.05, exponent: 0.8 },
      },
      case: {
        material_id: "pa12",
        inner_diameter: 0.062,
        wall_thickness: 0.005,
        length: null,
        print_method: "sls",
      },
      meop_bar: 70,
    },
  },
  {
    key: "unsafe",
    design: {
      name: "Intentionally unsafe",
      grain: {
        type: "bates",
        outer_diameter: 0.06,
        core_diameter: 0.012,
        segment_length: 0.2,
        segment_count: 4,
        segment_spacing: 0.003,
      },
      nozzle: {
        throat_diameter: 0.008,
        expansion_ratio: 3,
        divergence_half_angle_deg: 15,
        convergence_half_angle_deg: 45,
        efficiency: 0.95,
        throat_length: 0.004,
        erosion: { enabled: false, coefficient_mm_s: 0.05, exponent: 0.8 },
      },
      case: {
        material_id: "pla",
        inner_diameter: 0.066,
        wall_thickness: 0.002,
        length: null,
        print_method: "fdm",
      },
      liner: null,
      meop_bar: 40,
    },
  },
];
