import type { DesignDoc } from "../types";

/**
 * The one bundled example: the İTÜ PARS internal-ballistics reference case
 * (spec Section 13.1). Mirrors backend `core/examples.py::reference_case`:
 *   A_t = 235 mm^2  ->  r_t0 = 8.6489 mm  ->  d_throat = 17.2977 mm
 *   J = A_p/A_t = 4  ->  r_p0 = 17.2977 mm  ->  d_core = 34.5955 mm
 *   L = 147.21 mm ,  D_o = 85.8 mm ,  eps = 4
 *   KNSB run at rho_factor = 1.0 and eta_c* = 1.0 (report uses Phi = 1.0),
 *   so the calibrated 0.95 defaults are overridden here.
 * Expected outcome is deliberately UNSAFE: the progressive tube climbs from the
 * 10 bar design point to ~22 bar and trips WARN_MEOP_EXCEEDED against a 15 bar MEOP.
 */
export const EXAMPLES: { key: string; design: Partial<DesignDoc> }[] = [
  {
    key: "reference",
    design: {
      name: "İTÜ PARS reference tube",
      prefix: "PARS",
      propellant: { id: "knsb", density_factor: 1.0, c_star_efficiency: 1.0 },
      grain: {
        type: "tubular",
        outer_diameter: 0.0858,
        core_diameter: 0.0345955,
        segment_length: 0.14721,
        segment_count: 1,
        segment_spacing: 0,
        point_diameter: 0.03,
        n_points: 6,
      },
      nozzle: {
        throat_diameter: 0.0172977,
        expansion_ratio: 4,
        divergence_half_angle_deg: 15,
        convergence_half_angle_deg: 45,
        efficiency: 0.95,
        throat_length: 0.006,
        contour_type: "conic",
        material_id: null,
        erosion: { enabled: false, coefficient_mm_s: 0.05, exponent: 0.8 },
      },
      case: {
        material_id: "al6061_t6",
        inner_diameter: 0.092,
        wall_thickness: 0.005,
        length: null,
        print_method: "machined",
      },
      liner: { material_id: "graphite", thickness: 0.002 },
      bulkhead: { material_id: "al6061_t6", thickness: 0.012 },
      meop_bar: 15,
    },
  },
];
