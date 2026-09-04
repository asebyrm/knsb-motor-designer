import { create } from "zustand";

import { setToken } from "./api";
import type { DesignDoc, SimResult } from "./types";

export function defaultDesign(): DesignDoc {
  return {
    schema_version: 1,
    name: "New motor",
    prefix: "PARS",
    designer: "anonymous",
    propellant: { id: "knsb", density_factor: 0.95, c_star_efficiency: 0.95 },
    grain: {
      type: "bates",
      outer_diameter: 0.045,
      core_diameter: 0.018,
      segment_length: 0.075,
      segment_count: 3,
      segment_spacing: 0.003,
      point_diameter: 0.03,
      n_points: 6,
    },
    nozzle: {
      throat_diameter: 0.0115,
      expansion_ratio: 5,
      divergence_half_angle_deg: 15,
      convergence_half_angle_deg: 45,
      efficiency: 0.95,
      throat_length: 0.006,
      contour_type: "conic",
      material_id: null,
      erosion: { enabled: false, coefficient_mm_s: 0.05, exponent: 0.8 },
    },
    case: {
      material_id: "pa12",
      inner_diameter: 0.052,
      wall_thickness: 0.005,
      length: null,
      print_method: "sls",
    },
    liner: { material_id: "kraft_phenolic", thickness: 0.003 },
    bulkhead: { material_id: "pa12", thickness: 0.01 },
    assembly: { forward_gap: 0.002, aft_gap: 0.002 },
    environment: { ambient_pressure: 101325 },
    meop_bar: 45,
    bolt: { diameter: 0.004, shear_strength: 200e6 },
  };
}

function clone<T>(o: T): T {
  return JSON.parse(JSON.stringify(o)) as T;
}

function setPath(obj: Record<string, unknown>, path: string, value: unknown) {
  const keys = path.split(".");
  let node = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    const k = keys[i];
    if (node[k] == null || typeof node[k] !== "object") node[k] = {};
    node = node[k] as Record<string, unknown>;
  }
  node[keys[keys.length - 1]] = value;
}

export function getPath(obj: unknown, path: string): unknown {
  return path.split(".").reduce<unknown>((n, k) => (n == null ? n : (n as Record<string, unknown>)[k]), obj);
}

const LS_DESIGN = "knsb.design";
const LS_TOKEN = "knsb.token";

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

/** Deep-merges `saved` onto `base`, so a design saved before a field (grain.n_points,
 * nozzle.contour_type, ...) existed still gets that field's default instead of
 * `undefined` - a shallow `{...base, ...saved}` only merges top-level keys and would
 * silently drop new nested fields for any pre-existing localStorage/saved design. */
export function deepMerge<T>(base: T, saved: unknown): T {
  if (!isPlainObject(saved) || !isPlainObject(base)) return (saved as T) ?? base;
  const out: Record<string, unknown> = { ...base };
  for (const [k, v] of Object.entries(saved)) {
    out[k] = isPlainObject(v) && isPlainObject((base as Record<string, unknown>)[k])
      ? deepMerge((base as Record<string, unknown>)[k], v)
      : v;
  }
  return out as T;
}

function loadDesign(): DesignDoc {
  try {
    const raw = localStorage.getItem(LS_DESIGN);
    if (raw) return deepMerge(defaultDesign(), JSON.parse(raw));
  } catch {
    /* ignore */
  }
  return defaultDesign();
}

interface AppState {
  design: DesignDoc;
  mode: "basic" | "expert";
  units: "metric" | "imperial";
  theme: "light" | "dark";
  webFraction: number;
  lastResult: SimResult | null;
  user: Record<string, unknown> | null;
  setField: (path: string, value: unknown) => void;
  setDesign: (d: DesignDoc) => void;
  setMode: (m: "basic" | "expert") => void;
  setUnits: (u: "metric" | "imperial") => void;
  setTheme: (t: "light" | "dark") => void;
  setWebFraction: (f: number) => void;
  setLastResult: (r: SimResult | null) => void;
  setUser: (u: Record<string, unknown> | null, token?: string | null) => void;
}

export const useStore = create<AppState>((set, get) => ({
  design: loadDesign(),
  mode: (localStorage.getItem("knsb.mode") as "basic" | "expert") || "basic",
  units: (localStorage.getItem("knsb.units") as "metric" | "imperial") || "metric",
  theme: (localStorage.getItem("knsb.theme") as "light" | "dark") ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
  webFraction: 0,
  lastResult: null,
  user: null,
  setField: (path, value) => {
    const design = clone(get().design);
    setPath(design as unknown as Record<string, unknown>, path, value);
    localStorage.setItem(LS_DESIGN, JSON.stringify(design));
    set({ design });
  },
  setDesign: (design) => {
    localStorage.setItem(LS_DESIGN, JSON.stringify(design));
    set({ design });
  },
  setMode: (mode) => {
    localStorage.setItem("knsb.mode", mode);
    set({ mode });
  },
  setUnits: (units) => {
    localStorage.setItem("knsb.units", units);
    set({ units });
  },
  setTheme: (theme) => {
    localStorage.setItem("knsb.theme", theme);
    document.documentElement.classList.toggle("dark", theme === "dark");
    set({ theme });
  },
  setWebFraction: (webFraction) => set({ webFraction }),
  setLastResult: (lastResult) => set({ lastResult }),
  setUser: (user, token) => {
    if (token !== undefined) {
      if (token) localStorage.setItem(LS_TOKEN, token);
      else localStorage.removeItem(LS_TOKEN);
      setToken(token);
    }
    set({ user });
  },
}));

export function bootToken(): string | null {
  const t = localStorage.getItem(LS_TOKEN);
  if (t) setToken(t);
  return t;
}
