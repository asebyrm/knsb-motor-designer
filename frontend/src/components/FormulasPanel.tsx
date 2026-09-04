import { useTranslation } from "react-i18next";

import { Accordion, AccordionItem } from "./ui";

/**
 * Documents which formula the platform actually uses, stage by stage (Section 5).
 * The formulas below are transcribed from the module docstrings they implement -
 * keep this file in sync when those change; the source is always the final
 * authority if this page ever lags behind it.
 */

interface FormulaEntry {
  id: string;
  formula: string;
  source: string;
}

const GROUPS: { id: string; entries: FormulaEntry[] }[] = [
  {
    id: "grain",
    entries: [
      {
        id: "burn_area_bates",
        formula:
          "core_r = d/2 + x\nA_b(x) = N · [ 2π·core_r·(L_s − 2x) + 2π·((D_o/2)² − core_r²) ]\nweb = min( (D_o − d)/2 , L_s/2 )",
        source: "backend/core/grains/bates.py",
      },
      {
        id: "burn_area_tubular",
        formula: "r_p = d/2 + x\nA_b(x) = N · 2π·r_p·L   (ends and OD inhibited - always progressive)",
        source: "backend/core/grains/tubular.py",
      },
      {
        id: "burn_area_rod_tube",
        formula:
          "r_rod(x)     = max(d_rod/2 − x, 0)\nr_tube_id(x) = min(d_tube_id/2 + x, D_o/2)\nA_b(x)       = N · L · 2π · (r_rod(x) + r_tube_id(x))",
        source: "backend/core/grains/rod_tube.py",
      },
      {
        id: "burn_area_star_wagon",
        formula:
          "No closed form: the bore is a real 2D polygon, grown outward by the burnt web\nusing an exact polygon-offset (shapely `buffer`), clipped to the case bore.\nA_b(x) = −d(solid cross-section area)/dx, by definition of \"web\" - a central\nfinite difference of that exact area, sampled onto a lookup table once per design.",
        source: "backend/core/grains/_slotted.py",
      },
    ],
  },
  {
    id: "ballistics",
    entries: [
      {
        id: "kn",
        formula: "K_n = A_b / A_t",
        source: "backend/core/grains/base.py",
      },
      {
        id: "burn_rate",
        formula:
          "r_b[mm/s] = a · (p_c[MPa])ⁿ        (Saint-Robert / Vieille's law, piecewise in p_c)\nr_b[m/s]  = a · (p_c[Pa] / 1e6)ⁿ / 1000",
        source: "backend/core/propellant.py",
      },
      {
        id: "equilibrium_pressure",
        formula:
          "Mass balance:  ρ_p · A_b · r_b(p) = p · A_t / c*_eff\np_eq = ( ρ_p · η_c* · a_SI · c*_ideal · K_n ) ^ ( 1 / (1 − n) )\n(self-consistent row per piecewise (a, n) band; Brent root-find as a fallback)",
        source: "backend/core/propellant.py",
      },
      {
        id: "ballistics_march",
        formula:
          "Per timestep: burn area → K_n → equilibrium p_c → burn rate → thrust\ncoefficient → thrust → mass flow → integrate impulse → advance web (+ throat\nerosion, if enabled). Exponential tail-off after web burnout: τ = V_c/(c*·A_t).",
        source: "backend/core/ballistics.py",
      },
      {
        id: "lstar",
        formula: "L* = free chamber volume at ignition / throat area",
        source: "backend/core/assembly.py",
      },
    ],
  },
  {
    id: "nozzle",
    entries: [
      {
        id: "thrust_coefficient",
        formula:
          "Cf_ideal  = √( (2γ²/(γ−1)) · (2/(γ+1))^((γ+1)/(γ−1)) · (1 − (p_e/p_c)^((γ−1)/γ)) )\n            + (p_e − p_a)/p_c · ε\nλ         = (1 + cos α) / 2            (divergence loss; α/2 for a \"bell\" contour)\nCf_actual = λ · η_nozzle · Cf_ideal\nF         = Cf_actual · p_c · A_t",
        source: "backend/core/nozzle.py",
      },
      {
        id: "specific_impulse",
        formula: "I_t = ∫ F dt        Isp = I_t / (m_p · g0)",
        source: "backend/core/ballistics.py",
      },
      {
        id: "erosion",
        formula: "dr_t/dt = K · (p_c[MPa])^m     (never a way to raise MEOP - always judged erosionless)",
        source: "backend/core/nozzle.py",
      },
    ],
  },
  {
    id: "structural",
    entries: [
      {
        id: "fos_thin",
        formula:
          "Thin wall (t / r_i ≤ 0.1):\nσ_hoop = p·r_i/t     σ_axial = p·r_i/(2t)\nσ_vm   = √(σ_hoop² − σ_hoop·σ_axial + σ_axial²)\nFoS    = (tensile_strength · print-direction factor) / σ_vm",
        source: "backend/core/structure.py",
      },
      {
        id: "fos_thick",
        formula:
          "Thick wall (t / r_i > 0.1), Lamé, evaluated at the bore:\nσ_hoop = p·(r_o² + r_i²)/(r_o² − r_i²)     σ_radial = −p     σ_axial = p·r_i²/(r_o² − r_i²)\nMinimum FoS is 2.0 - below that, export is locked. Pressure used is always the\nerosionless peak (MEOP), never the design point.",
        source: "backend/core/structure.py",
      },
    ],
  },
  {
    id: "thermal",
    entries: [
      {
        id: "thermal_soak",
        formula:
          "Semi-infinite solid, liner inner face held at the flame temperature:\nT(x, t) = T_i + (T_s − T_i) · erfc( x / (2·√(α·t)) )\nx = liner thickness, t = burn time, α = liner thermal diffusivity",
        source: "backend/core/thermal.py",
      },
    ],
  },
  {
    id: "mission",
    entries: [
      {
        id: "flight",
        formula:
          "m(t) = m_dry + m_prop_remaining(t)\nD    = 0.5 · ρ_air(h) · v² · Cd · A\na    = (F(t) − D − m·g) / m\nISA troposphere (≤ 11 km), RK4 integration, dt = 0.01 s - not a full 6-DOF sim.",
        source: "backend/core/flight.py",
      },
    ],
  },
];

export function FormulasPanel() {
  const { t } = useTranslation();
  return (
    <div className="space-y-3 p-3">
      <p className="rounded bg-surface-2 p-2 text-xs text-text-secondary">{t("ui.formulas_hint")}</p>
      <Accordion defaultOpen={["grain", "ballistics"]}>
        {GROUPS.map((group) => (
          <AccordionItem key={group.id} id={group.id} title={t(`formulas.group.${group.id}`)}>
            <div className="space-y-3">
              {group.entries.map((e) => (
                <div key={e.id}>
                  <div className="mb-1 flex items-baseline justify-between gap-2">
                    <span className="text-sm font-medium">{t(`formulas.${e.id}.title`)}</span>
                    <span className="font-mono text-[10px] text-text-secondary">{e.source}</span>
                  </div>
                  <pre className="overflow-x-auto rounded bg-surface-2 p-2 font-mono text-[11px]
                                  leading-relaxed text-text">
                    {e.formula}
                  </pre>
                  <p className="mt-1 text-xs text-text-secondary">{t(`formulas.${e.id}.desc`)}</p>
                </div>
              ))}
            </div>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}
