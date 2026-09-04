import { useTranslation } from "react-i18next";

import { fmtMetricValue } from "../lib/units";
import { METRICS } from "../lib/registry";
import { useStore } from "../store";
import type { SimResult, WarningItem } from "../types";
import { Info, LevelDot } from "./ui";

const SUMMARY_KEY: Record<string, string> = {
  total_impulse: "total_impulse",
  average_thrust: "average_thrust",
  peak_thrust: "peak_thrust",
  burn_time: "burn_time",
  peak_pressure: "peak_pressure_no_erosion_bar",
  meop: "meop_bar",
  specific_impulse: "specific_impulse",
  propellant_mass: "propellant_mass",
  total_mass: "motor_mass_kg",
  mass_ratio: "mass_ratio",
  designation: "designation",
  fos: "fos",
  min_j: "min_j",
  lstar: "lstar_mm",
  thrust_to_weight: "thrust_to_weight",
  motor_mass: "motor_mass_kg",
  inert_mass: "inert_mass_kg",
  total_length: "total_length_mm",
  cg_initial: "cg_initial_mm",
  cg_burnout: "cg_burnout_mm",
  kn: "kn",
};

const PRIMARY = ["total_impulse", "average_thrust", "peak_pressure", "meop", "burn_time",
  "specific_impulse", "designation", "fos", "min_j"];

export function ResultsPanel({ result }: { result: SimResult | undefined }) {
  const { t } = useTranslation();
  const { units } = useStore();
  const lng = t("ui.run") ? (document.documentElement.lang || "en") : "en";

  if (!result) return <div className="p-3 text-sm text-text-secondary">{t("ui.loading")}</div>;
  const s = result.summary;

  const shown = METRICS.filter((m) => SUMMARY_KEY[m] in s);
  const primary = shown.filter((m) => PRIMARY.includes(m));
  const secondary = shown.filter((m) => !PRIMARY.includes(m));

  const meopExceeded =
    Number(s.peak_pressure_no_erosion_bar) > Number(s.meop_bar ?? Infinity);

  const row = (m: string) => {
    const raw = s[SUMMARY_KEY[m]];
    const val =
      m === "designation"
        ? String(raw ?? "")
        : m === "total_length" || m === "cg_initial" || m === "cg_burnout"
          ? fmtMetricValue(m, Number(raw) / 1000, units, lng)
          : m === "lstar"
            ? `${Number(raw).toFixed(0)} mm`
            : m === "total_mass" || m === "motor_mass" || m === "inert_mass"
              ? fmtMetricValue(m, Number(raw), units, lng)
              : fmtMetricValue(m, Number(raw), units, lng);
    const flagged = (m === "peak_pressure" || m === "meop") && meopExceeded;
    return (
      <div key={m} className="flex items-center justify-between gap-2 py-1 text-sm">
        <span className="flex items-center text-text-secondary">
          {t(`metric.${m}`)}
          <Info tKey={`info.metric.${m}`} />
        </span>
        <span className={`font-mono ${flagged ? "font-semibold text-danger" : ""}`}>
          {val}
          {m === "peak_pressure" && meopExceeded && " ⚠"}
        </span>
      </div>
    );
  };

  return (
    <div className="space-y-3 p-3">
      <div className="rounded-md bg-surface-2 p-2">{primary.map(row)}</div>
      <details className="text-sm">
        <summary className="cursor-pointer text-text-secondary">{t("ui.results")} +</summary>
        <div className="mt-1">{secondary.map(row)}</div>
      </details>
      <WarningsList warnings={result.warnings} exportLocked={result.export_locked} />
    </div>
  );
}

export function WarningsList({
  warnings,
  exportLocked,
}: {
  warnings: WarningItem[];
  exportLocked: boolean;
}) {
  const { t } = useTranslation();
  return (
    <div>
      <div className="mb-1 flex items-center gap-2 text-sm font-semibold">
        {t("ui.warnings")}
        {exportLocked && (
          <span className="rounded bg-danger/15 px-1.5 py-0.5 text-xs text-danger">
            {t("ui.export_locked")}
          </span>
        )}
      </div>
      {warnings.length === 0 ? (
        <p className="text-sm text-text-secondary">{t("ui.no_warnings")}</p>
      ) : (
        <ul className="space-y-1.5">
          {warnings.map((w, i) => (
            <li key={`${w.code}-${i}`} className="flex items-start gap-2 text-xs">
              <span className="mt-0.5">
                <LevelDot level={w.level} />
              </span>
              <span>
                <span className="font-medium">{codeShort(w.code)}</span>{" "}
                <span className="text-text-secondary">
                  {t(`info.warning.${w.code}`)}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function codeShort(code: string): string {
  return code.replace(/^WARN_/, "").replace(/_/g, " ").toLowerCase();
}
