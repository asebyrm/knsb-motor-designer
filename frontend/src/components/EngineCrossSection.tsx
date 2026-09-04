import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../api";
import { PART_FIT_CODES } from "../lib/drawing";
import { CONV } from "../lib/units";
import { useStore } from "../store";
import type { DesignDoc, SimResult } from "../types";
import { Info } from "./ui";

type Part = SimResult["assembly"]["parts"][number];

interface DimRow {
  id: string;
  label: string;
  path?: string;
  unit: keyof typeof CONV;
  value: number; // SI
  derived?: boolean;
  derivedKey?: string;
}

const deg = (d: number) => (d * Math.PI) / 180;

function webThickness(g: DesignDoc["grain"]): number {
  if (g.type === "endburner") return g.segment_length;
  const radial = (g.outer_diameter - g.core_diameter) / 2;
  if (g.type === "tubular") return radial;
  return Math.min(radial, g.segment_length / 2);
}

function burntCoreDia(g: DesignDoc["grain"], frac: number): number {
  if (g.type === "endburner") return 0;
  return g.core_diameter + 2 * frac * webThickness(g);
}

export function EngineCrossSection({ result }: { result: SimResult | undefined }) {
  const { t, i18n } = useTranslation();
  const { design, units, setField, webFraction } = useStore();
  const svgRef = useRef<SVGSVGElement>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [section, setSection] = useState<"long" | "trans">("long");
  const [pdfBusy, setPdfBusy] = useState(false);
  const [layers, setLayers] = useState({
    dimensions: true,
    part_names: true,
    hatching: true,
    axis: true,
    burnt: true,
  });

  const parts = useMemo(() => result?.assembly.parts ?? [], [result]);
  const fitCodes = new Set((result?.assembly.fit_warnings ?? []).map((w) => w.code));
  const badPart = (name: string) =>
    (PART_FIT_CODES[name] ?? []).some((c) => fitCodes.has(c));

  const g = design.grain;
  const noz = design.nozzle;
  const linerT = design.liner?.thickness ?? 0;

  const dims: DimRow[] = [
    { id: "grain_od", label: t("param.outer_diameter"), path: "grain.outer_diameter", unit: "length_mm", value: g.outer_diameter },
    { id: "grain_core", label: t("param.core_diameter"), path: "grain.core_diameter", unit: "length_mm", value: g.core_diameter },
    { id: "seg_len", label: t("param.segment_length"), path: "grain.segment_length", unit: "length_mm", value: g.segment_length },
    { id: "seg_count", label: t("param.segment_count"), path: "grain.segment_count", unit: "count", value: g.segment_count },
    { id: "throat", label: t("param.throat_diameter"), path: "nozzle.throat_diameter", unit: "length_mm", value: noz.throat_diameter },
    { id: "eps", label: t("param.expansion_ratio"), path: "nozzle.expansion_ratio", unit: "ratio", value: noz.expansion_ratio },
    { id: "div", label: t("param.divergence_half_angle"), path: "nozzle.divergence_half_angle_deg", unit: "angle_deg", value: noz.divergence_half_angle_deg },
    { id: "wall", label: t("param.case_wall_thickness"), path: "case.wall_thickness", unit: "length_mm", value: design.case.wall_thickness },
    { id: "case_id", label: t("param.case_inner_diameter"), path: "case.inner_diameter", unit: "length_mm", value: design.case.inner_diameter },
    { id: "liner_t", label: t("param.liner_thickness"), path: "liner.thickness", unit: "length_mm", value: linerT },
    { id: "bh_t", label: t("param.bulkhead_thickness"), path: "bulkhead.thickness", unit: "length_mm", value: design.bulkhead.thickness },
    // derived
    { id: "web", label: "web w", unit: "length_mm", value: webThickness(g), derived: true, derivedKey: "web" },
    { id: "exit_d", label: "D_e", unit: "length_mm", value: noz.throat_diameter * Math.sqrt(noz.expansion_ratio), derived: true, derivedKey: "exit_diameter" },
    { id: "total_len", label: "L_total", unit: "length_mm", value: Number(result?.summary.total_length_mm ?? 0) / 1000, derived: true, derivedKey: "total_length" },
    { id: "lstar", label: "L*", unit: "length_mm", value: (result?.assembly.lstar_mm ?? 0) / 1000, derived: true, derivedKey: "lstar" },
  ];

  function commit(row: DimRow, displayValue: string) {
    if (!row.path) return;
    const raw = Number(displayValue);
    setField(row.path, row.unit === "count" ? Math.round(raw) : CONV[row.unit].fromDisplay(raw, units));
    setEditing(null);
  }

  async function downloadPdf() {
    setPdfBusy(true);
    try {
      await api.exportFile(design, "pdf", i18n.language === "tr" ? "tr" : "en", false);
    } finally {
      setPdfBusy(false);
    }
  }

  const drawing =
    section === "long" ? (
      <LongitudinalSVG
        svgRef={svgRef}
        parts={parts}
        design={design}
        webFraction={webFraction}
        layers={layers}
        badPart={badPart}
      />
    ) : (
      <TransverseSVG svgRef={svgRef} design={design} webFraction={webFraction} badPart={badPart} />
    );

  return (
    <div className="space-y-3">
      <div>
        <h2 className="text-sm font-semibold">{t("ui.technical_report")}</h2>
        <p className="text-xs text-text-secondary">{t("ui.technical_report_hint")}</p>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-xs">
        <div className="flex overflow-hidden rounded-md border border-border">
          {(["long", "trans"] as const).map((s) => (
            <button
              key={s}
              className={
                "px-2 py-1 " +
                (section === s ? "bg-primary text-primary-fg" : "text-text-secondary")
              }
              onClick={() => setSection(s)}
            >
              {t(s === "long" ? "ui.section_longitudinal" : "ui.section_transverse")}
            </button>
          ))}
        </div>
        {(["dimensions", "part_names", "hatching", "axis", "burnt"] as const).map((k) => (
          <label key={k} className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={layers[k]}
              onChange={(e) => setLayers((s) => ({ ...s, [k]: e.target.checked }))}
            />
            {t(`ui.layer_${k}`)}
          </label>
        ))}
        <span className="ml-auto flex items-center gap-2">
          <button className="btn-primary text-xs" onClick={downloadPdf} disabled={pdfBusy}>
            {pdfBusy ? t("ui.recalculating") : t("ui.download_pdf_report")}
          </button>
        </span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border bg-surface">{drawing}</div>

      <table className="w-full text-sm">
        <tbody>
          {dims.map((row) => {
            const disp =
              row.unit === "count" ? row.value : CONV[row.unit].toDisplay(row.value, units);
            const label = CONV[row.unit].label(units);
            return (
              <tr key={row.id} className="border-b border-border/60">
                <td className="py-1 pr-2">
                  <span className={row.derived ? "italic text-text-secondary" : "text-text"}>
                    {row.label}
                  </span>
                  {row.derived && row.derivedKey && (
                    <Info tKey={`info.derived.${row.derivedKey}`} />
                  )}
                </td>
                <td className="py-1 text-right font-mono">
                  {editing === row.id && row.path ? (
                    <input
                      autoFocus
                      type="number"
                      defaultValue={Number(disp.toFixed(3))}
                      className="input w-24 text-right"
                      onBlur={(e) => commit(row, e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") commit(row, (e.target as HTMLInputElement).value);
                        if (e.key === "Escape") setEditing(null);
                      }}
                    />
                  ) : (
                    <button
                      className={
                        row.path
                          ? "underline decoration-dotted underline-offset-2"
                          : "cursor-default text-text-secondary"
                      }
                      onClick={() => row.path && setEditing(row.id)}
                      title={row.derived ? t("ui.derived_value") : undefined}
                    >
                      {typeof disp === "number" ? disp.toFixed(row.unit === "count" ? 0 : 2) : disp}{" "}
                      {label}
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {result && <Bom result={result} />}
    </div>
  );
}

/* ------------------------------------------------- longitudinal cross-section */

/**
 * Schematic longitudinal section in the style of a textbook "solid rocket engine"
 * diagram: green propellant, dark combustion-chamber cavity, a yellow flame front,
 * a grey converging-diverging nozzle bell and red exhaust arrows, with leader-line
 * labels. Still scaled from the real geometry (part x-positions + nozzle angles) and
 * animated by the web slider.
 */
export function LongitudinalSVG({
  svgRef,
  parts,
  design,
  webFraction,
  layers,
  badPart,
}: {
  svgRef: React.RefObject<SVGSVGElement | null>;
  parts: Part[];
  design: DesignDoc;
  webFraction: number;
  layers: Record<string, boolean>;
  badPart: (n: string) => boolean;
}) {
  const { t } = useTranslation();
  if (!parts.length) {
    return <p className="p-4 text-sm text-text-secondary">{t("ui.loading")}</p>;
  }
  const g = design.grain;
  const nz = design.nozzle;

  const case_ = parts.find((p) => p.name === "case");
  const grain = parts.find((p) => p.name === "grain");
  const bh = parts.find((p) => p.name === "bulkhead");
  const nozzle = parts.find((p) => p.name === "nozzle");
  if (!grain || !nozzle) {
    return <p className="p-4 text-sm text-text-secondary">{t("ui.loading")}</p>;
  }

  // --- geometry (mm) --------------------------------------------------------
  const rCaseO = (case_?.outer_diameter_mm ?? g.outer_diameter * 1000 + 12) / 2;
  const rCaseI = (case_?.inner_diameter_mm ?? g.outer_diameter * 1000 + 2) / 2;
  const rBore0 = (g.core_diameter * 1000) / 2;
  const rBoreNow = (burntCoreDia(g, layers.burnt ? webFraction : 0) * 1000) / 2;
  const rGrainO = (g.outer_diameter * 1000) / 2;

  const rT = (nz.throat_diameter * 1000) / 2;
  const rE = rT * Math.sqrt(nz.expansion_ratio);
  const nozLen = nozzle.x_end_mm - nozzle.x_start_mm;
  let convLen = Math.max(rCaseI - rT, 0) / Math.tan(deg(nz.convergence_half_angle_deg));
  let throatLen = nz.throat_length * 1000 || 0.3 * rT;
  let divLen = Math.max(rE - rT, 0) / Math.tan(deg(nz.divergence_half_angle_deg));
  const kLen = nozLen / (convLen + throatLen + divLen || 1);
  convLen *= kLen;
  throatLen *= kLen;
  divLen *= kLen;

  const x0 = Math.min(...parts.map((p) => p.x_start_mm));
  const x1 = Math.max(...parts.map((p) => p.x_end_mm));
  const dMax = 2 * Math.max(rCaseO, rE);

  // --- canvas -------------------------------------------------------------
  const W = 760;
  const PADX = 96;
  const PADY = 74;
  const drawW = W - 2 * PADX;
  const spanMm = Math.max(x1 - x0, 1);
  const scale = drawW / spanMm;
  const H = Math.round(dMax * scale) + 2 * PADY;
  const axisY = PADY + (dMax * scale) / 2;
  const sx = (xmm: number) => PADX + (xmm - x0) * scale;
  const yUp = (rmm: number) => axisY - rmm * scale;
  const yDn = (rmm: number) => axisY + rmm * scale;
  const ratio = spanMm / drawW;

  const bhX = bh ? bh.x_end_mm : grain.x_start_mm - 6;
  const gx0 = grain.x_start_mm;
  const gx1 = grain.x_end_mm;
  const nx = nozzle.x_start_mm;
  const pConv = nx + convLen;
  const pThroat = pConv + throatLen;
  const pExit = pThroat + divLen;

  const caseStroke = badPart("case") ? "var(--error)" : "currentColor";
  const grainStroke = badPart("grain") ? "var(--error)" : "var(--propellant-stroke)";
  const nozStroke = badPart("nozzle") ? "var(--error)" : "var(--nozzle-metal-stroke)";

  const els: React.ReactNode[] = [];

  // chamber wall outline (rounded forward end) + dashed nose hint
  const chamStartX = case_ ? case_.x_start_mm : bhX;
  els.push(
    <path key="wall"
      d={`M ${sx(nx)} ${yUp(rCaseO)} L ${sx(chamStartX + rCaseO * 0.35)} ${yUp(rCaseO)} ` +
         `Q ${sx(chamStartX)} ${yUp(rCaseO)} ${sx(chamStartX)} ${yUp(rCaseO * 0.5)} ` +
         `L ${sx(chamStartX)} ${yDn(rCaseO * 0.5)} ` +
         `Q ${sx(chamStartX)} ${yDn(rCaseO)} ${sx(chamStartX + rCaseO * 0.35)} ${yDn(rCaseO)} ` +
         `L ${sx(nx)} ${yDn(rCaseO)}`}
      fill="none" stroke={caseStroke} strokeWidth={2} />,
    <path key="nose" d={`M ${sx(chamStartX)} ${yUp(rCaseO * 0.5)} L ${sx(x0 - spanMm * 0.05)} ${yUp(0)} ` +
      `L ${sx(chamStartX)} ${yDn(rCaseO * 0.5)}`}
      fill="none" stroke="var(--dim-derived)" strokeWidth={1} strokeDasharray="5 4" />,
  );

  // bulkhead
  if (bh) {
    els.push(
      <rect key="bh" x={sx(bh.x_start_mm)} y={yUp(rCaseO)} width={(bh.x_end_mm - bh.x_start_mm) * scale}
        height={rCaseO * 2 * scale} fill="var(--nozzle-metal)" stroke={caseStroke} strokeWidth={1.2} />,
    );
  }

  // propellant grain (green) with the burnt zone (grey) and the dark cavity
  const n = g.type === "endburner" ? 1 : Math.max(1, g.segment_count);
  const gapMm = g.type === "bates" ? g.segment_spacing * 1000 : 0;
  const segMm = g.type === "bates" ? g.segment_length * 1000 : gx1 - gx0;
  for (let i = 0; i < n; i++) {
    const xa = gx0 + i * (segMm + gapMm);
    const xb = Math.min(xa + segMm, gx1);
    const rInner = g.type === "endburner" ? 0 : rBoreNow;
    const rInner0 = g.type === "endburner" ? 0 : rBore0;
    const w = (xb - xa) * scale;
    // green propellant remaining
    for (const sign of [-1, 1]) {
      const yA = sign < 0 ? yUp(rGrainO) : yDn(rInner);
      els.push(
        <rect key={`prop-${i}-${sign}`} x={sx(xa)} y={yA} width={w} height={(rGrainO - rInner) * scale}
          fill="var(--propellant)" stroke={grainStroke} strokeWidth={1}>
          <title>{`${t("drawing.propellant")} · ${design.propellant.id}`}</title>
        </rect>,
      );
      // burnt zone between the initial and current bore
      if (layers.burnt && rInner > rInner0 + 0.01) {
        const yB = sign < 0 ? yUp(rInner) : yDn(rInner0);
        els.push(
          <rect key={`burnt-${i}-${sign}`} x={sx(xa)} y={yB} width={w}
            height={(rInner - rInner0) * scale} fill="var(--burnt-zone)" opacity={0.55} />,
        );
      }
    }
  }

  // nozzle metal (grey) — smooth converging-diverging bell drawn as a solid shell
  const wallT = Math.max(rT * 0.7, 4);
  const wallE = Math.max(rE * 0.4, 4);
  const cLen = pThroat - nx; // convergent length
  const dLen = pExit - pThroat; // divergent length
  const bell = (yy: (r: number) => number) =>
    // outer: hug the case OD briefly, curve down to the throat, then flare (bell)
    `M ${sx(nx)} ${yy(rCaseO)} ` +
    `L ${sx(nx + cLen * 0.3)} ${yy(rCaseO * 0.94)} ` +
    `Q ${sx(pThroat - cLen * 0.2)} ${yy(rT + wallT)} ${sx(pThroat)} ${yy(rT + wallT)} ` +
    `C ${sx(pThroat + dLen * 0.3)} ${yy(rT + wallT)} ${sx(pExit - dLen * 0.15)} ${yy(rE + wallE)} ` +
    `${sx(pExit)} ${yy(rE + wallE)} ` +
    // exit lip down to the flow surface
    `L ${sx(pExit)} ${yy(rE)} ` +
    // inner: divergent cone back to the throat, then convergent curve to the chamber bore
    `C ${sx(pExit - dLen * 0.15)} ${yy(rE)} ${sx(pThroat + dLen * 0.3)} ${yy(rT)} ${sx(pThroat)} ${yy(rT)} ` +
    `Q ${sx(nx + cLen * 0.35)} ${yy(rCaseI * 0.9)} ${sx(nx)} ${yy(rCaseI)} Z`;
  els.push(
    <path key="noz-top" d={bell(yUp)} fill="var(--nozzle-metal)" stroke={nozStroke} strokeWidth={1.4}>
      <title>{t("drawing.nozzle")}</title>
    </path>,
    <path key="noz-bot" d={bell(yDn)} fill="var(--nozzle-metal)" stroke={nozStroke} strokeWidth={1.4} />,
  );

  // combustion-chamber cavity (dark) — bore through the grain and the nozzle flow path,
  // drawn ON TOP of the nozzle so the flow channel reads as an opening
  const rCav = rBoreNow || rT;
  els.push(
    <path key="cavity"
      d={`M ${sx(bhX)} ${yUp(rCav)} L ${sx(nx)} ${yUp(rCav)} ` +
         `Q ${sx(nx + cLen * 0.35)} ${yUp(rCav)} ${sx(pThroat)} ${yUp(rT)} ` +
         `C ${sx(pThroat + dLen * 0.3)} ${yUp(rT)} ${sx(pExit - dLen * 0.15)} ${yUp(rE)} ` +
         `${sx(pExit)} ${yUp(rE)} ` +
         `L ${sx(pExit)} ${yDn(rE)} ` +
         `C ${sx(pExit - dLen * 0.15)} ${yDn(rE)} ${sx(pThroat + dLen * 0.3)} ${yDn(rT)} ` +
         `${sx(pThroat)} ${yDn(rT)} ` +
         `Q ${sx(nx + cLen * 0.35)} ${yDn(rCav)} ${sx(nx)} ${yDn(rCav)} L ${sx(bhX)} ${yDn(rCav)} Z`}
      fill="var(--cavity)" />,
  );

  // flame front (yellow) — the burning surfaces
  if (g.type !== "endburner") {
    for (const sign of [-1, 1]) {
      const y = sign < 0 ? yUp(rBoreNow) : yDn(rBoreNow);
      els.push(
        <line key={`flame-core-${sign}`} x1={sx(gx0)} y1={y} x2={sx(gx1)} y2={y}
          stroke="var(--flame)" strokeWidth={2.5} />,
      );
    }
    // segment end faces
    if (g.type === "bates") {
      for (let i = 0; i < n; i++) {
        const xa = gx0 + i * (segMm + gapMm);
        const xb = Math.min(xa + segMm, gx1);
        for (const xf of [xa, xb]) {
          els.push(
            <line key={`flame-face-${i}-${xf}`} x1={sx(xf)} y1={yUp(rBoreNow)} x2={sx(xf)}
              y2={yUp(rGrainO)} stroke="var(--flame)" strokeWidth={2} />,
            <line key={`flame-faceb-${i}-${xf}`} x1={sx(xf)} y1={yDn(rBoreNow)} x2={sx(xf)}
              y2={yDn(rGrainO)} stroke="var(--flame)" strokeWidth={2} />,
          );
        }
      }
    }
  } else {
    // end-burner: a transverse flame face that recedes
    const xf = gx0 + webFraction * (gx1 - gx0);
    els.push(
      <line key="flame-eb" x1={sx(xf)} y1={yUp(rGrainO)} x2={sx(xf)} y2={yDn(rGrainO)}
        stroke="var(--flame)" strokeWidth={3} />,
    );
  }

  // exhaust arrows
  for (const fr of [-0.55, 0, 0.55]) {
    const y = axisY + fr * rE * scale;
    const x = sx(pExit) + 6;
    els.push(
      <g key={`ex-${fr}`} stroke="var(--exhaust)" strokeWidth={2.4} fill="var(--exhaust)">
        <line x1={x} y1={y} x2={x + 34} y2={y} />
        <path d={`M ${x + 34} ${y} l -7 -4 v 8 z`} />
      </g>,
    );
  }

  if (layers.axis) {
    els.push(
      <line key="axis" x1={sx(x0) - 24} y1={axisY} x2={sx(pExit) + 52} y2={axisY}
        stroke="var(--axis)" strokeWidth={0.7} strokeDasharray="10 3 2 3" />,
    );
  }

  // labels with leader lines
  if (layers.part_names) {
    const label = (
      key: string,
      lx: number,
      ly: number,
      tx: number,
      ty: number,
      text: string,
      anchor: "start" | "middle" | "end" = "middle",
    ) => (
      <g key={key} fontSize={11} fill="var(--text)">
        <line x1={lx} y1={ly} x2={tx} y2={ty} stroke="var(--dim-derived)" strokeWidth={0.7} />
        <circle cx={lx} cy={ly} r={1.6} fill="var(--dim-derived)" />
        <text x={tx} y={ty + (ty < axisY ? -3 : 11)} textAnchor={anchor}>{text}</text>
      </g>
    );
    els.push(
      label("l-prop", sx(gx0 + (gx1 - gx0) * 0.15), yUp((rGrainO + rBoreNow) / 2),
        sx(gx0 + (gx1 - gx0) * 0.05), PADY - 14, `${t("drawing.propellant")} (${design.propellant.id})`,
        "start"),
      label("l-flame", sx(gx0 + (gx1 - gx0) * 0.66), yUp(rBoreNow),
        sx(gx1 - (gx1 - gx0) * 0.1), PADY - 32, t("drawing.flame_front")),
      label("l-chamber", sx(gx0 + (gx1 - gx0) * 0.5), yDn(rCav * 0.6),
        sx(gx0 + (gx1 - gx0) * 0.42), H - PADY + 18, t("drawing.chamber")),
      label("l-throat", sx(pThroat), yDn(rT + wallT), sx(pThroat + 8), H - PADY + 34,
        t("drawing.throat")),
      label("l-nozzle", sx(pThroat + (pExit - pThroat) * 0.5), yUp(rE + wallE),
        sx(pThroat + (pExit - pThroat) * 0.5), PADY - 14, t("drawing.nozzle")),
      label("l-exhaust", sx(pExit) + 34, axisY - rE * scale * 0.55, sx(pExit) + 52, PADY - 14,
        t("drawing.exhaust"), "end"),
    );
    if (bh) {
      els.push(label("l-bh", sx((bh.x_start_mm + bh.x_end_mm) / 2), yDn(rCaseO * 0.6),
        sx(x0 - spanMm * 0.03), H - PADY + 34, t("drawing.bulkhead"), "start"));
    }
  }

  if (layers.dimensions) {
    els.push(
      <DimLine key="ltot" x1={sx(x0)} x2={sx(x1)} y={PADY - 46}
        label={`L_total ${(x1 - x0).toFixed(1)} mm`} derived />,
      <DimLine key="dmax" x1={sx(pExit) + 24} x2={sx(pExit) + 24} y={yUp(rCaseO)} y2={yDn(rCaseO)}
        vertical label={`D ${(rCaseO * 2).toFixed(1)} mm`} />,
    );
  }

  return (
    <svg ref={svgRef} xmlns="http://www.w3.org/2000/svg" viewBox={`0 0 ${W} ${H}`}
      className="min-w-[700px]" style={{ color: "var(--text)" }}>
      {els}
      <text x={PADX} y={H - 6} fontSize={11} fill="var(--dim-derived)">
        {t("ui.scale")} 1 : {ratio.toFixed(2)}
      </text>
    </svg>
  );
}

/* ---------------------------------------------------- transverse cross-section */

export function TransverseSVG({
  svgRef,
  design,
  webFraction,
  badPart,
}: {
  svgRef: React.RefObject<SVGSVGElement | null>;
  design: DesignDoc;
  webFraction: number;
  badPart: (n: string) => boolean;
}) {
  const { t } = useTranslation();
  const S = 320;
  const c = S / 2;
  const g = design.grain;
  const rCaseO = (design.case.inner_diameter + 2 * design.case.wall_thickness) / 2;
  const rCaseI = design.case.inner_diameter / 2;
  const linerT = design.liner?.thickness ?? 0;
  const rLinerI = rCaseI - linerT;
  const rGrainO = g.outer_diameter / 2;
  const rCore = burntCoreDia(g, webFraction) / 2;
  const rCoreInit = g.core_diameter / 2;
  const k = (c - 16) / rCaseO; // scale m -> px
  const ring = (r: number, fill: string, s: string, sw = 1, dash?: string) => (
    <circle cx={c} cy={c} r={r * k} fill={fill} stroke={s} strokeWidth={sw} strokeDasharray={dash} />
  );
  const caseS = badPart("case") ? "var(--error)" : "currentColor";
  return (
    <svg ref={svgRef} xmlns="http://www.w3.org/2000/svg" viewBox={`0 0 ${S} ${S}`}
      className="mx-auto block max-h-[360px]" style={{ color: "var(--text)" }}>
      {/* case wall */}
      {ring(rCaseO, "var(--nozzle-metal)", caseS, 1.3)}
      {ring(rCaseI, "var(--surface)", caseS)}
      {/* liner */}
      {linerT > 0 &&
        ring(rLinerI, "var(--surface-2)", badPart("liner") ? "var(--error)" : "currentColor")}
      {/* propellant (green) */}
      {ring(rGrainO, "var(--propellant)",
        badPart("grain") ? "var(--error)" : "var(--propellant-stroke)", badPart("grain") ? 1.8 : 1.2)}
      {/* burnt zone + dark cavity */}
      {g.type !== "endburner" && rCore > rCoreInit + 1e-9 && ring(rCore, "var(--burnt-zone)", "none")}
      {g.type !== "endburner" && rCore > 0 && ring(rCore, "var(--cavity)", "none")}
      {/* flame front at the bore */}
      {g.type !== "endburner" && (
        <circle cx={c} cy={c} r={rCore * k} fill="none" stroke="var(--flame)" strokeWidth={2.5} />
      )}
      {/* initial bore, dashed */}
      {g.type !== "endburner" && rCore > rCoreInit + 1e-9 &&
        ring(rCoreInit, "none", "currentColor", 0.8, "2 2")}
      <text x={c} y={S - 6} textAnchor="middle" fontSize={11} fill="var(--dim-derived)">
        {t("ui.section_transverse")} · D_case {(rCaseO * 2000).toFixed(1)} mm
      </text>
    </svg>
  );
}

/* --------------------------------------------------------------------- BOM */

function Bom({ result }: { result: SimResult }) {
  const { t } = useTranslation();
  const rows = result.assembly.bom;
  function downloadCsv() {
    const header = "part,material,length_mm,outer_diameter_mm,inner_diameter_mm,mass_g,quantity";
    const body = rows
      .map((r) =>
        [r.part, r.material_id, r.length_mm, r.outer_diameter_mm, r.inner_diameter_mm, r.mass_g, r.quantity]
          .map((x) => (x == null ? "" : x))
          .join(","),
      )
      .join("\n");
    const blob = new Blob([`${header}\n${body}\n`], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "bom.csv";
    a.click();
  }
  return (
    <div>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{t("ui.bom")}</h3>
        <button className="btn-ghost text-xs" onClick={downloadCsv}>
          {t("ui.download_bom")}
        </button>
      </div>
      <table className="mt-1 w-full text-xs">
        <thead>
          <tr className="text-left text-text-secondary">
            <th className="py-1">{t("ui.bom_part")}</th>
            <th>{t("ui.bom_material")}</th>
            <th className="text-right">{t("ui.bom_length")}</th>
            <th className="text-right">{t("ui.bom_od")}</th>
            <th className="text-right">{t("ui.bom_id")}</th>
            <th className="text-right">{t("ui.bom_mass")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={r.part === "TOTAL" ? "border-t border-border font-semibold" : ""}>
              <td className="py-1">{String(r.part)}</td>
              <td>{String(r.material_id ?? "")}</td>
              <td className="text-right font-mono">{fmtCell(r.length_mm)}</td>
              <td className="text-right font-mono">{fmtCell(r.outer_diameter_mm)}</td>
              <td className="text-right font-mono">{fmtCell(r.inner_diameter_mm)}</td>
              <td className="text-right font-mono">{fmtCell(r.mass_g)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DimLine({
  x1,
  x2,
  y,
  y2,
  label,
  vertical,
  derived,
}: {
  x1: number;
  x2: number;
  y: number;
  y2?: number;
  label: string;
  vertical?: boolean;
  derived?: boolean;
}) {
  const color = derived ? "var(--dim-derived)" : "var(--dim)";
  const mx = vertical ? x1 : (x1 + x2) / 2;
  const my = vertical ? (y + (y2 ?? y)) / 2 : y - 5;
  return (
    <g stroke={color} fill={color} fontSize={10}>
      <line x1={x1} y1={y} x2={vertical ? x1 : x2} y2={vertical ? y2 : y}
        strokeDasharray={derived ? "4 3" : undefined} strokeWidth={0.6} />
      {!vertical && (
        <>
          <path d={`M${x1},${y} l5,-3 v6 z`} />
          <path d={`M${x2},${y} l-5,-3 v6 z`} />
        </>
      )}
      <text x={mx} y={my} textAnchor="middle" stroke="none">
        {label}
      </text>
    </g>
  );
}

function fmtCell(v: unknown): string {
  return v == null ? "" : typeof v === "number" ? v.toFixed(1) : String(v);
}
