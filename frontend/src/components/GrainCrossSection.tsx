import { useTranslation } from "react-i18next";

import type { DesignDoc, SimResult } from "../types";

function webThickness(g: DesignDoc["grain"]): number {
  if (g.type === "endburner") return g.segment_length;
  const radial = (g.outer_diameter - g.core_diameter) / 2;
  if (g.type === "tubular") return radial;
  return Math.min(radial, g.segment_length / 2);
}

/** Transverse section that regresses with the web slider (Section 10). */
export function GrainCrossSection({
  design,
  result,
  webFraction,
}: {
  design: DesignDoc;
  result: SimResult | undefined;
  webFraction: number;
}) {
  const { t } = useTranslation();
  const g = design.grain;
  const rOuter = 45;
  const x = webFraction * webThickness(g);
  const coreRatio = g.type === "endburner" ? 0 : (g.core_diameter / 2 + x) / (g.outer_diameter / 2);
  const initialRatio = g.type === "endburner" ? 0 : g.core_diameter / g.outer_diameter;
  const coreR = Math.min(coreRatio * rOuter, rOuter);
  const burntR = (initialRatio / 2) * (2 * rOuter);

  // instantaneous values at this web position, read from the series
  let kn = 0;
  let pc = 0;
  let f = 0;
  if (result?.series?.web_mm) {
    const webMax = Math.max(...result.series.web_mm);
    const target = webFraction * webMax;
    const idx = result.series.web_mm.findIndex((w) => w >= target);
    const i = idx >= 0 ? idx : result.series.web_mm.length - 1;
    kn = result.series.kn?.[i] ?? 0;
    pc = result.series.chamber_pressure_bar?.[i] ?? 0;
    f = result.series.thrust_n?.[i] ?? 0;
  }

  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 100 100" className="h-48 w-48" role="img" aria-label={t("ui.cross_section")}>
        <g stroke="currentColor" strokeWidth={0.8}>
          <circle cx={50} cy={50} r={rOuter} fill="var(--grain-fill)" />
          {coreR > 0 && <circle cx={50} cy={50} r={coreR} fill="var(--burnt-fill)" />}
          {burntR > 0 && (
            <circle
              cx={50}
              cy={50}
              r={burntR / 2}
              fill="none"
              strokeDasharray="1.5 1.5"
              opacity={0.5}
            />
          )}
        </g>
      </svg>
      <dl className="space-y-1 text-sm">
        <div className="flex justify-between gap-6">
          <dt className="text-text-secondary">Kn</dt>
          <dd className="font-mono">{kn.toFixed(1)}</dd>
        </div>
        <div className="flex justify-between gap-6">
          <dt className="text-text-secondary">p_c</dt>
          <dd className="font-mono">{pc.toFixed(1)} bar</dd>
        </div>
        <div className="flex justify-between gap-6">
          <dt className="text-text-secondary">F</dt>
          <dd className="font-mono">{f.toFixed(0)} N</dd>
        </div>
      </dl>
    </div>
  );
}
