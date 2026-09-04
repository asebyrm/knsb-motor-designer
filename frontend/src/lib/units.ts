import type { UnitKind } from "./registry";

export type UnitSystem = "metric" | "imperial";

interface Conv {
  label: (s: UnitSystem) => string;
  toDisplay: (si: number, s: UnitSystem) => number;
  fromDisplay: (disp: number, s: UnitSystem) => number;
  digits: number;
}

const IN = 25.4; // mm per inch
const LBF = 4.4482216152605;
const LB = 0.45359237;
const PSI = 6894.757293168;

export const CONV: Record<UnitKind, Conv> = {
  // SI base is METRES; shown as mm (metric) / inch (imperial)
  length_mm: {
    label: (s) => (s === "imperial" ? "in" : "mm"),
    toDisplay: (si, s) => (s === "imperial" ? (si * 1000) / IN : si * 1000),
    fromDisplay: (d, s) => (s === "imperial" ? (d * IN) / 1000 : d / 1000),
    digits: 2,
  },
  length_m: {
    label: (s) => (s === "imperial" ? "ft" : "m"),
    toDisplay: (si, s) => (s === "imperial" ? si * 3.280839895 : si),
    fromDisplay: (d, s) => (s === "imperial" ? d / 3.280839895 : d),
    digits: 1,
  },
  pressure_bar: {
    label: (s) => (s === "imperial" ? "psi" : "bar"),
    toDisplay: (si, s) => (s === "imperial" ? (si * 1e5) / PSI : si),
    fromDisplay: (d, s) => (s === "imperial" ? (d * PSI) / 1e5 : d),
    digits: 1,
  },
  pressure_pa: {
    label: (s) => (s === "imperial" ? "psi" : "bar"),
    toDisplay: (si, s) => (s === "imperial" ? si / PSI : si / 1e5),
    fromDisplay: (d, s) => (s === "imperial" ? d * PSI : d * 1e5),
    digits: 2,
  },
  angle_deg: { label: () => "°", toDisplay: (si) => si, fromDisplay: (d) => d, digits: 1 },
  ratio: { label: () => "", toDisplay: (si) => si, fromDisplay: (d) => d, digits: 3 },
  count: { label: () => "", toDisplay: (si) => si, fromDisplay: (d) => Math.round(d), digits: 0 },
  mass_kg: {
    label: (s) => (s === "imperial" ? "lb" : "kg"),
    toDisplay: (si, s) => (s === "imperial" ? si / LB : si),
    fromDisplay: (d, s) => (s === "imperial" ? d * LB : d),
    digits: 3,
  },
  accel_g: { label: () => "g", toDisplay: (si) => si, fromDisplay: (d) => d, digits: 1 },
  rate_mm_s: { label: () => "mm/s", toDisplay: (si) => si, fromDisplay: (d) => d, digits: 3 },
  none: { label: () => "", toDisplay: (si) => si, fromDisplay: (d) => d, digits: 0 },
};

export function fmtMetricValue(id: string, value: number, s: UnitSystem, locale: string): string {
  const nf = (n: number, d: number) =>
    new Intl.NumberFormat(locale, { maximumFractionDigits: d }).format(n);
  const force = (n: number) =>
    s === "imperial" ? `${nf(n / LBF, 1)} lbf` : `${nf(n, 1)} N`;
  switch (id) {
    case "total_impulse":
      return s === "imperial" ? `${nf(value / LBF, 1)} lbf·s` : `${nf(value, 1)} N·s`;
    case "average_thrust":
    case "peak_thrust":
      return force(value);
    case "burn_time":
      return `${nf(value, 2)} s`;
    case "peak_pressure":
    case "meop":
      return s === "imperial" ? `${nf((value * 1e5) / PSI, 0)} psi` : `${nf(value, 2)} bar`;
    case "specific_impulse":
      return `${nf(value, 1)} s`;
    case "propellant_mass":
    case "total_mass":
    case "motor_mass":
    case "inert_mass":
      return s === "imperial" ? `${nf(value / LB, 3)} lb` : `${nf(value * 1000, 1)} g`;
    case "total_length":
      return s === "imperial" ? `${nf(value / IN, 2)} in` : `${nf(value, 1)} mm`;
    case "cg_initial":
    case "cg_burnout":
      return s === "imperial" ? `${nf(value / IN, 2)} in` : `${nf(value, 1)} mm`;
    case "lstar":
      return `${nf(value, 0)} mm`;
    case "fos":
    case "mass_ratio":
    case "min_j":
    case "thrust_to_weight":
    case "kn":
      return nf(value, 2);
    default:
      return typeof value === "number" ? nf(value, 2) : String(value);
  }
}

/** Units that can never go negative in the real world (lengths, masses). Fields
 * bound to these must reject/clamp a typed-in negative value instead of storing
 * a physically meaningless size. */
const NON_NEGATIVE_UNITS: ReadonlySet<UnitKind> = new Set([
  "length_mm", "length_m", "mass_kg", "count",
]);

export function isNonNegativeUnit(unit: UnitKind): boolean {
  return NON_NEGATIVE_UNITS.has(unit);
}

/** Clamp a value typed in a field's display unit to a physically valid minimum. */
export function clampForUnit(displayValue: number, unit: UnitKind): number {
  return isNonNegativeUnit(unit) ? Math.max(0, displayValue) : displayValue;
}
