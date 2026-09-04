import { useRef } from "react";
import { useTranslation } from "react-i18next";

import { LongitudinalSVG, TransverseSVG } from "./EngineCrossSection";
import { PART_FIT_CODES, PREVIEW_LAYERS } from "../lib/drawing";
import { useStore } from "../store";
import type { SimResult } from "../types";

/**
 * Compact, non-editable longitudinal + transverse views shown next to the burn
 * curves, so the web slider animates both projections at once. The fully
 * interactive, dimensioned/editable version with the BOM and downloads lives in
 * the "Technical report" tab (same underlying drawing code, no duplication).
 */
export function LiveCrossSections({ result }: { result: SimResult | undefined }) {
  const { t } = useTranslation();
  const { design, webFraction } = useStore();
  const longRef = useRef<SVGSVGElement>(null);
  const transRef = useRef<SVGSVGElement>(null);

  const parts = result?.assembly.parts ?? [];
  if (!parts.length) return null;

  const fitCodes = new Set((result?.assembly.fit_warnings ?? []).map((w) => w.code));
  const badPart = (name: string) => (PART_FIT_CODES[name] ?? []).some((c) => fitCodes.has(c));

  // instantaneous Kn / p_c / F at this web position, read from the series
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
    <div className="grid gap-3 md:grid-cols-[2fr_1fr]">
      <div>
        <p className="mb-1 field-label">{t("ui.section_longitudinal")}</p>
        <div className="overflow-x-auto rounded-lg border border-border bg-surface">
          <LongitudinalSVG
            svgRef={longRef}
            parts={parts}
            design={design}
            webFraction={webFraction}
            layers={PREVIEW_LAYERS}
            badPart={badPart}
          />
        </div>
      </div>
      <div>
        <p className="mb-1 field-label">{t("ui.section_transverse")}</p>
        <div className="rounded-lg border border-border bg-surface p-1">
          <TransverseSVG svgRef={transRef} design={design} webFraction={webFraction} badPart={badPart} />
        </div>
        <dl className="mt-2 space-y-1 text-sm">
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
    </div>
  );
}
