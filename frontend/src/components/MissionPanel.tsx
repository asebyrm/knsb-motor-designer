import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../api";
import { CONV } from "../lib/units";
import { MISSION_FIELDS } from "../lib/registry";
import { useStore } from "../store";
import type { MissionCandidate, MissionResult } from "../types";
import { Info } from "./ui";

const DEFAULTS: Record<string, number> = {
  dry_mass: 6,
  body_diameter: 0.1,
  drag_coefficient: 0.55,
  target_apogee: 800,
  rail_length: 2,
  max_accel_g: 15,
  launch_altitude: 0,
};

export function MissionPanel() {
  const { t } = useTranslation();
  const { units, design, setDesign } = useStore();
  const [vals, setVals] = useState<Record<string, number>>({ ...DEFAULTS });
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [result, setResult] = useState<MissionResult | null>(null);
  const [err, setErr] = useState("");

  async function run(extra: Partial<Record<string, number>> = {}) {
    setStatus("running");
    setErr("");
    setResult(null);
    const payload = {
      ...vals,
      ...extra,
      case_inner_diameter: design.case.inner_diameter,
      case_wall_thickness: design.case.wall_thickness,
      case_material_id: design.case.material_id,
      print_method: design.case.print_method,
      propellant_id: design.propellant.id,
      meop_bar: design.meop_bar,
      time_budget_s: 25,
    };
    try {
      const { job_id } = await api.startMission(payload);
      for (let i = 0; i < 90; i++) {
        await new Promise((r) => setTimeout(r, 700));
        const j = await api.job(job_id);
        if (j.status === "done") {
          setResult(j.result);
          setStatus("done");
          return;
        }
        if (j.status === "failed") {
          setErr(j.error || "failed");
          setStatus("error");
          return;
        }
      }
      setErr("timeout");
      setStatus("error");
    } catch (e) {
      setErr(String(e));
      setStatus("error");
    }
  }

  function applySuggestion() {
    const s = result?.suggestion;
    if (!s) return;
    const field = String(s.field);
    const value = Number(s.suggested);
    if (field === "meop_bar") setDesign({ ...design, meop_bar: value });
    else if (field === "case_wall_thickness")
      setDesign({ ...design, case: { ...design.case, wall_thickness: value / 1000 } });
    else if (field === "liner_thickness" && design.liner)
      setDesign({ ...design, liner: { ...design.liner, thickness: value / 1000 } });
    else if (field === "rail_length") {
      setVals((v) => ({ ...v, rail_length: value }));
      void run({ rail_length: value });
      return;
    } else if (field === "max_accel_g") {
      setVals((v) => ({ ...v, max_accel_g: value }));
      void run({ max_accel_g: value });
      return;
    }
    void run();
  }

  function openInDesigner(c: MissionCandidate) {
    setDesign({
      ...design,
      grain: {
        ...design.grain,
        type: "bates",
        outer_diameter: c.outer_diameter,
        core_diameter: c.core_diameter,
        segment_length: c.segment_length,
        segment_count: c.segment_count,
      },
      nozzle: { ...design.nozzle, throat_diameter: c.throat_diameter },
    });
  }

  const scopeNote = <p className="rounded bg-surface-2 p-2 text-xs text-text-secondary">{t("info.flight.scope")}</p>;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1 text-sm font-semibold">
        {t("mission.title")}
      </div>
      {scopeNote}

      <div className="grid grid-cols-2 gap-2">
        {MISSION_FIELDS.map((f) => {
          const conv = CONV[f.unit];
          return (
            <label key={f.id} className="text-xs">
              <span className="flex items-center field-label">
                {t(`param.${f.id}`)}
                <Info tKey={`info.param.${f.id}`} />
              </span>
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  className="input"
                  step={f.step}
                  value={Number(conv.toDisplay(vals[f.id] ?? 0, units).toFixed(3))}
                  onChange={(e) =>
                    setVals((v) => ({
                      ...v,
                      [f.id]: conv.fromDisplay(Number(e.target.value), units),
                    }))
                  }
                />
                <span className="w-8 text-text-secondary">{conv.label(units)}</span>
              </div>
            </label>
          );
        })}
      </div>

      <button className="btn-primary w-full" disabled={status === "running"} onClick={() => run()}>
        {status === "running" ? t("ui.recalculating") : t("mission.calculate")}
      </button>

      {status === "error" && <p className="text-xs text-danger">{err}</p>}

      {result && !result.feasible && (
        <div className="card border-warning/40 p-3 text-sm">
          <p className="font-medium text-warning">{t("mission.no_solution")}</p>
          <p className="mt-1">
            <span className="text-text-secondary">{t("mission.binding_constraint")}: </span>
            {t(`solver.constraint.${result.binding_constraint ?? "unknown"}`)}
          </p>
          {result.suggestion && (
            <div className="mt-2 rounded bg-surface-2 p-2 text-xs">
              <span className="text-text-secondary">{t("mission.suggestion")}: </span>
              <code>
                {String(result.suggestion.field)} → {String(result.suggestion.suggested)}
                {result.suggestion.unit ? ` ${result.suggestion.unit}` : ""}
              </code>
              <button className="btn-primary mt-2 w-full text-xs" onClick={applySuggestion}>
                {t("mission.apply_and_retry")}
              </button>
            </div>
          )}
        </div>
      )}

      {result?.feasible &&
        result.candidates.map((c, i) => (
          <div key={i} className="card p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-semibold">
                {[t("mission.candidate_lightest"), t("mission.candidate_safest"), t("mission.candidate_closest")][i] ??
                  `#${i + 1}`}
              </span>
              <span className="font-mono text-primary">{c.designation}</span>
            </div>
            <p className="mt-1">
              {t("mission.apogee")}: <span className="font-mono">~{c.apogee.toFixed(0)} m</span>{" "}
              <span className="text-text-secondary">
                ({c.apogee_low.toFixed(0)}–{c.apogee_high.toFixed(0)} m,{" "}
                ±{Math.round((result.uncertainty_fraction ?? 0.18) * 100)}%)
              </span>
            </p>
            <p className="mt-1 grid grid-cols-2 gap-x-3 text-xs text-text-secondary">
              <span>D_o {(c.outer_diameter * 1000).toFixed(1)} mm</span>
              <span>core {(c.core_diameter * 1000).toFixed(1)} mm</span>
              <span>L_s {(c.segment_length * 1000).toFixed(1)} mm × {c.segment_count}</span>
              <span>d_t {(c.throat_diameter * 1000).toFixed(1)} mm</span>
              <span>peak {c.peak_pressure_bar.toFixed(1)} bar</span>
              <span>FoS {c.fos.toFixed(2)}</span>
              <span>J_min {c.min_j.toFixed(2)}</span>
              <span>rail {c.rail_exit_velocity.toFixed(0)} m/s</span>
            </p>
            <button className="btn-ghost mt-2 w-full text-xs" onClick={() => openInDesigner(c)}>
              {t("ui.open_design")}
            </button>
            <p className="mt-2 text-[11px] text-text-secondary">{t("info.flight.scope")}</p>
          </div>
        ))}
    </div>
  );
}
