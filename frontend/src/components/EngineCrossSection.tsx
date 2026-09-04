import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "../api";
import { linerColor, PART_FIT_CODES } from "../lib/drawing";
import { clampForUnit, CONV, isNonNegativeUnit } from "../lib/units";
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
  if (g.type === "rod_tube")
    return Math.max(g.core_diameter / 2, (g.outer_diameter - g.point_diameter) / 2);
  if (g.type === "star" || g.type === "wagon_wheel") return (g.outer_diameter - g.core_diameter) / 2;
  const radial = (g.outer_diameter - g.core_diameter) / 2;
  if (g.type === "tubular") return radial;
  return Math.min(radial, g.segment_length / 2);
}

function burntCoreDia(g: DesignDoc["grain"], frac: number): number {
  if (g.type === "endburner") return 0;
  return g.core_diameter + 2 * frac * webThickness(g);
}

/** Matches the backend's own default (core/grains/wagon_wheel.py) - the two only
 * ever disagree if a design sets an explicit slot_half_angle_deg, which isn't
 * exposed in the UI, so this schematic-preview approximation always matches. */
function wagonWheelSlotHalfAngleDeg(nPoints: number): number {
  return Math.min(15, (0.35 * 180) / nPoints);
}

/** Points for the star bore polygon (SVG px coords), growing linearly with the
 * burnt web - the same simplified preview model core/grains/star.py's own
 * cross_section_svg uses (the real physics uses an exact polygon offset; this is
 * only ever a schematic drawing). */
function starPolygonPoints(g: DesignDoc["grain"], frac: number, k: number, c: number): string {
  const webNow = frac * webThickness(g);
  const rMax = g.outer_diameter / 2;
  const pts: string[] = [];
  for (let i = 0; i < 2 * g.n_points; i++) {
    const base = i % 2 === 0 ? g.point_diameter / 2 : g.core_diameter / 2;
    const r = Math.min(base + webNow, rMax) * k;
    const theta = (Math.PI * i) / g.n_points;
    pts.push(`${c + r * Math.cos(theta)},${c + r * Math.sin(theta)}`);
  }
  return pts.join(" ");
}

interface WagonWheelSlot {
  hx1: number; hy1: number; hx2: number; hy2: number;
  tx1: number; ty1: number; tx2: number; ty2: number;
}

function wagonWheelSlots(g: DesignDoc["grain"], frac: number, k: number,
  c: number): { hubR: number; slots: WagonWheelSlot[] } {
  const webNow = frac * webThickness(g);
  const rMax = g.outer_diameter / 2;
  const rHub = Math.min(g.core_diameter / 2 + webNow, rMax);
  const rTip = Math.min(g.point_diameter / 2 + webNow, rMax);
  const half = (Math.PI / 180) * wagonWheelSlotHalfAngleDeg(g.n_points);
  const slots: WagonWheelSlot[] = [];
  for (let i = 0; i < g.n_points; i++) {
    const center = (2 * Math.PI * i) / g.n_points;
    slots.push({
      hx1: c + rHub * k * Math.cos(center - half), hy1: c + rHub * k * Math.sin(center - half),
      hx2: c + rHub * k * Math.cos(center + half), hy2: c + rHub * k * Math.sin(center + half),
      tx1: c + rTip * k * Math.cos(center - half), ty1: c + rTip * k * Math.sin(center - half),
      tx2: c + rTip * k * Math.cos(center + half), ty2: c + rTip * k * Math.sin(center + half),
    });
  }
  return { hubR: rHub * k, slots };
}

export function EngineCrossSection({ result }: { result: SimResult | undefined }) {
  const { t, i18n } = useTranslation();
  const { design, units, setField } = useStore();
  const [editing, setEditing] = useState<string | null>(null);
  const [pdfBusy, setPdfBusy] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  const g = design.grain;
  const noz = design.nozzle;
  const linerT = design.liner?.thickness ?? 0;
  const fitCodes = new Set((result?.assembly.fit_warnings ?? []).map((w) => w.code));
  const badPart = (name: string) => (PART_FIT_CODES[name] ?? []).some((c) => fitCodes.has(c));

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
    const raw = clampForUnit(Number(displayValue), row.unit);
    setField(row.path, row.unit === "count" ? Math.round(raw) : CONV[row.unit].fromDisplay(raw, units));
    setEditing(null);
  }

  async function downloadPdf() {
    setPdfBusy(true);
    setPdfError(null);
    try {
      await api.exportFile(design, "pdf", i18n.language === "tr" ? "tr" : "en", true);
    } catch (e) {
      setPdfError(e instanceof ApiError ? e.message || String(e.status) : String(e));
    } finally {
      setPdfBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">{t("ui.technical_report")}</h2>
          <p className="text-xs text-text-secondary">{t("ui.technical_report_hint")}</p>
        </div>
        <div className="text-right">
          <button className="btn-primary text-xs" onClick={downloadPdf} disabled={pdfBusy}>
            {pdfBusy ? t("ui.recalculating") : t("ui.download_pdf_report")}
          </button>
          {pdfError && <p className="mt-1 max-w-xs text-xs text-danger">{pdfError}</p>}
        </div>
      </div>

      <div>
        <h3 className="mb-1 text-sm font-semibold">{t("ui.nozzle_drawing")}</h3>
        <div className="overflow-x-auto rounded-lg border border-border bg-surface p-2">
          <NozzleTechnicalSVG design={design} badPart={badPart} />
        </div>
      </div>

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
                      min={isNonNegativeUnit(row.unit) ? 0 : undefined}
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
  const rGrainO = (g.outer_diameter * 1000) / 2;
  // rod_tube's "core_diameter" is the rod's own (shrinking) OD, not a growing bore
  // like every other type - the actual open flow area is the tube's (growing) bore,
  // whose initial diameter is point_diameter. Handled separately below.
  const isRodTube = g.type === "rod_tube";
  const rBore0 = isRodTube ? (g.point_diameter * 1000) / 2 : (g.core_diameter * 1000) / 2;
  const rBoreNow = isRodTube
    ? Math.min(rBore0 + (layers.burnt ? webFraction : 0) * webThickness(g) * 1000, rGrainO)
    : (burntCoreDia(g, layers.burnt ? webFraction : 0) * 1000) / 2;
  const rRod0 = isRodTube ? (g.core_diameter * 1000) / 2 : 0;
  const rRodNow = isRodTube
    ? Math.max(rRod0 - (layers.burnt ? webFraction : 0) * webThickness(g) * 1000, 0)
    : 0;

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

  // case wall (solid black band between the case OD and ID)
  if (rCaseO > rCaseI + 0.01) {
    const caseW = (nx - chamStartX) * scale;
    els.push(
      <rect key="case-wall-top" x={sx(chamStartX)} y={yUp(rCaseO)} width={caseW}
        height={(rCaseO - rCaseI) * scale} fill="var(--case-color)" />,
      <rect key="case-wall-bot" x={sx(chamStartX)} y={yDn(rCaseI)} width={caseW}
        height={(rCaseO - rCaseI) * scale} fill="var(--case-color)" />,
    );
  }

  // bulkhead
  if (bh) {
    els.push(
      <rect key="bh" x={sx(bh.x_start_mm)} y={yUp(rCaseO)} width={(bh.x_end_mm - bh.x_start_mm) * scale}
        height={rCaseO * 2 * scale} fill="var(--case-color)" stroke={caseStroke} strokeWidth={1.2} />,
    );
  }

  // liner — the band between the case bore and the grain OD (skipped where too thin to
  // see). rLinerI never goes below the true grain OD, so a snug (even zero-clearance)
  // fit still shows the liner at its full nominal thickness with no gap; it only
  // shrinks below nominal for genuine interference (grain OD past that boundary).
  const linerTmm = (design.liner?.thickness ?? 0) * 1000;
  const rGrainODraw = rGrainO;
  if (linerTmm > 0.01) {
    const rLinerO = rCaseI;
    const rLinerI = Math.max(rCaseI - linerTmm, rGrainO);
    const lc = linerColor(design.liner?.material_id);
    for (const sign of [-1, 1]) {
      const yA = sign < 0 ? yUp(rLinerO) : yDn(rLinerI);
      els.push(
        <rect key={`liner-${sign}`} x={sx(gx0)} y={yA} width={(gx1 - gx0) * scale}
          height={(rLinerO - rLinerI) * scale} fill={lc}
          stroke={badPart("liner") ? "var(--error)" : "var(--nozzle-metal-stroke)"} strokeWidth={0.6}>
          <title>{`${t("drawing.liner")} · ${design.liner?.material_id ?? ""}`}</title>
        </rect>,
      );
    }
  }

  // propellant grain (green) with the burnt zone (grey) and the dark cavity.
  // Each segment's un-burned axial extent [xaNow, xbNow] is computed once here and
  // reused by the flame-front lines below, so both stay in sync.
  const n = g.type === "endburner" ? 1 : Math.max(1, g.segment_count);
  const gapMm = g.type === "endburner" ? 0 : g.segment_spacing * 1000;
  const segMm = g.type === "endburner" ? gx1 - gx0 : g.segment_length * 1000;
  // BATES burns from both exposed end faces as well as the core (tubular and
  // endburner ends are inhibited), symmetrically - the burned web equals the
  // radial growth already computed for the bore.
  const burnedWebMm = g.type === "bates" ? Math.max(rBoreNow - rBore0, 0) : 0;
  const segments = Array.from({ length: n }, (_, i) => {
    const xa = gx0 + i * (segMm + gapMm);
    const xb = Math.min(xa + segMm, gx1);
    const mid = (xa + xb) / 2;
    return { xaNow: Math.min(xa + burnedWebMm, mid), xbNow: Math.max(xb - burnedWebMm, mid) };
  });
  segments.forEach(({ xaNow, xbNow }, i) => {
    if (xbNow <= xaNow + 1e-6) return; // this segment has burnt through axially
    const rInner = g.type === "endburner" ? 0 : rBoreNow;
    const rInner0 = g.type === "endburner" ? 0 : rBore0;
    const w = (xbNow - xaNow) * scale;
    // green propellant remaining
    for (const sign of [-1, 1]) {
      const yA = sign < 0 ? yUp(rGrainODraw) : yDn(rInner);
      els.push(
        <rect key={`prop-${i}-${sign}`} x={sx(xaNow)} y={yA} width={w}
          height={(rGrainODraw - rInner) * scale}
          fill="var(--propellant)" stroke={grainStroke} strokeWidth={1}>
          <title>{`${t("drawing.propellant")} · ${design.propellant.id}`}</title>
        </rect>,
      );
      // burnt zone between the initial and current bore
      if (layers.burnt && rInner > rInner0 + 0.01) {
        const yB = sign < 0 ? yUp(rInner) : yDn(rInner0);
        els.push(
          <rect key={`burnt-${i}-${sign}`} x={sx(xaNow)} y={yB} width={w}
            height={(rInner - rInner0) * scale} fill="var(--burnt-zone)" opacity={0.55} />,
        );
      }
    }
    // rod_tube: the free rod remaining in the middle of the tube's open bore
    if (isRodTube && rRodNow > 0) {
      for (const sign of [-1, 1]) {
        els.push(
          <rect key={`rod-${i}-${sign}`} x={sx(xaNow)}
            y={sign < 0 ? yUp(rRodNow) : axisY} width={w} height={rRodNow * scale}
            fill="var(--propellant)" stroke={grainStroke} strokeWidth={1}>
            <title>{`${t("drawing.propellant")} · ${design.propellant.id} (rod)`}</title>
          </rect>,
        );
      }
      if (layers.burnt && rRodNow < rRod0 - 0.01) {
        for (const sign of [-1, 1]) {
          els.push(
            <rect key={`rod-burnt-${i}-${sign}`} x={sx(xaNow)}
              y={sign < 0 ? yUp(rRod0) : yDn(rRodNow)} width={w}
              height={(rRod0 - rRodNow) * scale} fill="var(--burnt-zone)" opacity={0.55} />,
          );
        }
      }
    }
  });

  // nozzle metal (grey) — smooth converging-diverging bell drawn as a solid shell
  const wallT = Math.max(rT * 0.7, 4);
  const wallE = Math.max(rE * 0.4, 4);
  const cLen = pConv - nx; // convergent length
  const dLen = pExit - pThroat; // divergent length
  // "conic" divergent walls are straight lines at the given half-angle; "bell"
  // walls are drawn as the same smooth curve as the convergent side (Section 5.3 -
  // an approximated, shortened Rao-style contour, not a straight cone)
  const isBell = nz.contour_type === "bell";
  const divOuter = (yy: (r: number) => number) =>
    isBell
      ? `C ${sx(pThroat + dLen * 0.3)} ${yy(rT + wallT)} ${sx(pExit - dLen * 0.15)} ${yy(rE + wallE)} ` +
        `${sx(pExit)} ${yy(rE + wallE)} `
      : `L ${sx(pExit)} ${yy(rE + wallE)} `;
  const divInner = (yy: (r: number) => number) =>
    isBell
      ? `C ${sx(pExit - dLen * 0.15)} ${yy(rE)} ${sx(pThroat + dLen * 0.3)} ${yy(rT)} ${sx(pThroat)} ${yy(rT)} `
      : `L ${sx(pThroat)} ${yy(rT)} `;
  const bell = (yy: (r: number) => number) =>
    // outer: hug the case OD briefly, curve down to the throat, then flare
    `M ${sx(nx)} ${yy(rCaseO)} ` +
    `L ${sx(nx + cLen * 0.3)} ${yy(rCaseO * 0.94)} ` +
    `Q ${sx(pConv - cLen * 0.2)} ${yy(rT + wallT)} ${sx(pConv)} ${yy(rT + wallT)} ` +
    // straight throat land - its length is the throat_length parameter, drawn to scale
    `L ${sx(pThroat)} ${yy(rT + wallT)} ` +
    `${divOuter(yy)}` +
    // exit lip down to the flow surface
    `L ${sx(pExit)} ${yy(rE)} ` +
    // inner: divergent section back to the throat land, straight through it, then
    // convergent curve back to the chamber bore
    `${divInner(yy)}` +
    `L ${sx(pConv)} ${yy(rT)} ` +
    `Q ${sx(nx + cLen * 0.35)} ${yy(rCaseI * 0.9)} ${sx(nx)} ${yy(rCaseI)} Z`;
  els.push(
    // drawn as part of the case (Section 10.1) - same solid-black treatment,
    // regardless of which material is actually selected for it
    <path key="noz-top" d={bell(yUp)} fill="var(--case-color)" stroke={nozStroke} strokeWidth={1.4}>
      <title>{t("drawing.nozzle")}</title>
    </path>,
    <path key="noz-bot" d={bell(yDn)} fill="var(--case-color)" stroke={nozStroke} strokeWidth={1.4} />,
  );

  // nozzle flow-passage cavity (dark) — carves the flow channel out of the solid
  // nozzle bell fill. The chamber bore itself is left unfilled (background shows
  // through) so the solid-black case wall reads as a clean, unambiguous outline
  // instead of blending into an equally dark chamber interior.
  const rCav = rBoreNow || rT;
  // the nozzle wall path above already only fills the metal itself (outer profile
  // down to the flow surface), so the flow passage is left unfilled here too, the
  // same as the chamber - background shows through instead of a separate cavity
  // fill, keeping the two visually consistent.

  // flame front (yellow) — the burning surfaces, drawn per segment so it stops at
  // each segment's actual (possibly burnt-through) extent rather than bridging gaps
  if (g.type !== "endburner") {
    segments.forEach(({ xaNow, xbNow }, i) => {
      if (xbNow <= xaNow + 1e-6) return; // burnt through, no surface left
      for (const sign of [-1, 1]) {
        const y = sign < 0 ? yUp(rBoreNow) : yDn(rBoreNow);
        els.push(
          <line key={`flame-core-${i}-${sign}`} x1={sx(xaNow)} y1={y} x2={sx(xbNow)} y2={y}
            stroke="var(--flame)" strokeWidth={2.5} />,
        );
      }
      // rod_tube: the rod's own outer surface burns too
      if (isRodTube && rRodNow > 0) {
        for (const sign of [-1, 1]) {
          const y = sign < 0 ? yUp(rRodNow) : yDn(rRodNow);
          els.push(
            <line key={`flame-rod-${i}-${sign}`} x1={sx(xaNow)} y1={y} x2={sx(xbNow)} y2={y}
              stroke="var(--flame)" strokeWidth={2} />,
          );
        }
      }
      // segment end faces — only BATES burns from the ends; the faces visibly
      // retreat inward together with the propellant rect above
      if (g.type === "bates") {
        for (const xf of [xaNow, xbNow]) {
          els.push(
            <line key={`flame-face-${i}-${xf === xaNow ? "a" : "b"}-top`} x1={sx(xf)} y1={yUp(rBoreNow)}
              x2={sx(xf)} y2={yUp(rGrainODraw)} stroke="var(--flame)" strokeWidth={2} />,
            <line key={`flame-face-${i}-${xf === xaNow ? "a" : "b"}-bot`} x1={sx(xf)} y1={yDn(rBoreNow)}
              x2={sx(xf)} y2={yDn(rGrainODraw)} stroke="var(--flame)" strokeWidth={2} />,
          );
        }
      }
    });
  } else {
    // end-burner: a transverse flame face that recedes
    const xf = gx0 + webFraction * (gx1 - gx0);
    els.push(
      <line key="flame-eb" x1={sx(xf)} y1={yUp(rGrainODraw)} x2={sx(xf)} y2={yDn(rGrainODraw)}
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
      <DimLine key="lthroat" x1={sx(pConv)} x2={sx(pThroat)} y={yDn(rT + wallT) + 16}
        label={`L_t ${(pThroat - pConv).toFixed(1)} mm`} derived />,
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
  // liner is drawn independently of the grain (two nested circles closing off its
  // own band, see below), so it stays visible at its full nominal thickness
  // regardless of how tight the true clearance to the grain is - no artificial
  // grain shrink needed here any more.
  const rGrainODraw = rGrainO;
  const ring = (r: number, fill: string, s: string, sw = 1, dash?: string) => (
    <circle cx={c} cy={c} r={r * k} fill={fill} stroke={s} strokeWidth={sw} strokeDasharray={dash} />
  );
  const caseS = badPart("case") ? "var(--error)" : "currentColor";
  const flameS = badPart("grain") ? "var(--error)" : "var(--flame)";

  const shaped = g.type === "star" || g.type === "wagon_wheel" || g.type === "rod_tube";
  let bore: React.ReactNode = null;
  if (g.type !== "endburner" && !shaped) {
    bore = (
      <>
        {/* burnt zone [rCoreInit, rCore) then the true (always-open) cavity
            [0, rCoreInit) drawn smaller on top - same nested-circle rule as the
            liner above: a circle's own color shows above its own radius, not
            below it, so cavity must use the *smaller* radius here */}
        {rCore > rCoreInit + 1e-9 && ring(rCore, "var(--burnt-zone)", "none")}
        {rCore > 0 && ring(rCoreInit, "var(--surface)", "none")}
        <circle cx={c} cy={c} r={rCore * k} fill="none" stroke={flameS} strokeWidth={2.5} />
        {rCore > rCoreInit + 1e-9 && ring(rCoreInit, "none", "var(--dim-derived)", 1, "2 2")}
      </>
    );
  } else if (g.type === "star") {
    bore = (
      <>
        <polygon points={starPolygonPoints(g, webFraction, k, c)} fill="var(--surface)"
          stroke={flameS} strokeWidth={2} />
        <polygon points={starPolygonPoints(g, 0, k, c)} fill="none"
          stroke="var(--dim-derived)" strokeWidth={1} strokeDasharray="2 2" />
      </>
    );
  } else if (g.type === "wagon_wheel") {
    const { hubR, slots } = wagonWheelSlots(g, webFraction, k, c);
    const { hubR: hubR0, slots: slots0 } = wagonWheelSlots(g, 0, k, c);
    bore = (
      <>
        <circle cx={c} cy={c} r={hubR} fill="var(--surface)" stroke={flameS} strokeWidth={2} />
        {slots.map((s, i) => (
          <polygon key={i} fill="var(--surface)" stroke={flameS} strokeWidth={2}
            points={`${s.hx1},${s.hy1} ${s.tx1},${s.ty1} ${s.tx2},${s.ty2} ${s.hx2},${s.hy2}`} />
        ))}
        <circle cx={c} cy={c} r={hubR0} fill="none" stroke="var(--dim-derived)" strokeWidth={1}
          strokeDasharray="2 2" />
        {slots0.map((s, i) => (
          <polygon key={`i0-${i}`} fill="none" stroke="var(--dim-derived)" strokeWidth={1}
            strokeDasharray="2 2"
            points={`${s.hx1},${s.hy1} ${s.tx1},${s.ty1} ${s.tx2},${s.ty2} ${s.hx2},${s.hy2}`} />
        ))}
      </>
    );
  } else if (g.type === "rod_tube") {
    const webNow = webFraction * webThickness(g);
    const rRod = Math.max(g.core_diameter / 2 - webNow, 0);
    const rTubeI = Math.min(g.point_diameter / 2 + webNow, rGrainO);
    bore = (
      <>
        {ring(rTubeI, "var(--surface)", "none")}
        {rRod > 0 && ring(rRod, "var(--propellant)", flameS, 1.5)}
        <circle cx={c} cy={c} r={rTubeI * k} fill="none" stroke={flameS} strokeWidth={2.5} />
        {ring(g.point_diameter / 2, "none", "var(--dim-derived)", 1, "2 2")}
        {ring(g.core_diameter / 2, "none", "var(--dim-derived)", 1, "2 2")}
      </>
    );
  }

  return (
    <svg ref={svgRef} xmlns="http://www.w3.org/2000/svg" viewBox={`0 0 ${S} ${S}`}
      className="mx-auto block max-h-[360px]" style={{ color: "var(--text)" }}>
      {/* case wall */}
      {ring(rCaseO, "var(--case-color)", caseS, 1.3)}
      {/* liner sits directly against the case, so it (not empty background) is
          what the case bore reveals; a second, smaller circle then reveals empty
          background again at the liner's own inner edge - the two together are
          what makes the visible liner band exactly [rLinerI, rCaseI), not
          [grain edge, rLinerI) like a single circle here would (nested filled
          circles show a color from their own radius up to whatever smaller
          circle is drawn after them, not down to it) */}
      {ring(rCaseI, linerT > 0 ? linerColor(design.liner?.material_id) : "var(--surface)", caseS)}
      {linerT > 0 &&
        ring(rLinerI, "var(--surface)", badPart("liner") ? "var(--error)" : "currentColor")}
      {/* propellant (green) */}
      {ring(rGrainODraw, "var(--propellant)",
        badPart("grain") ? "var(--error)" : "var(--propellant-stroke)", badPart("grain") ? 1.8 : 1.2)}
      {bore}
      <text x={c} y={S - 6} textAnchor="middle" fontSize={11} fill="var(--dim-derived)">
        {t("ui.section_transverse")} · D_case {(rCaseO * 2000).toFixed(1)} mm
      </text>
    </svg>
  );
}

/* ------------------------------------------------------- nozzle technical drawing */

/**
 * A standalone, dimensioned nozzle drawing for the Teknik rapor tab (Section 10.1
 * extension) - drawn as part of the case (solid black), independent of the whole-
 * engine views above so it can use its own, larger scale.
 */
export function NozzleTechnicalSVG({
  svgRef,
  design,
  badPart,
}: {
  svgRef?: React.RefObject<SVGSVGElement | null>;
  design: DesignDoc;
  badPart: (n: string) => boolean;
}) {
  const { t } = useTranslation();
  const nz = design.nozzle;
  const rT = (nz.throat_diameter * 1000) / 2;
  const rE = rT * Math.sqrt(nz.expansion_ratio);
  const rChamber = (design.case.inner_diameter * 1000) / 2;

  const convLen = Math.max(rChamber - rT, 0) / Math.tan(deg(nz.convergence_half_angle_deg));
  const throatLen = nz.throat_length * 1000 || 0.3 * rT;
  const divLen = Math.max(rE - rT, 0) / Math.tan(deg(nz.divergence_half_angle_deg));
  const totalLen = Math.max(convLen + throatLen + divLen, 1);
  // the body is machined from round stock - a plain cylinder on the outside,
  // wide enough to contain the flow contour's widest point (the chamber bore or
  // the exit, whichever is larger) with a wall margin, bored out to the actual
  // gas-dynamic shape on the inside
  const rOuter = Math.max(rChamber, rE) + Math.max(rT * 0.5, 5);

  const W = 680;
  const PADX = 100;
  const PADY = 92;
  const scale = (W - 2 * PADX) / totalLen;
  const dMax = 2 * rOuter;
  const H = Math.round(dMax * scale) + 2 * PADY;
  const axisY = PADY + (dMax * scale) / 2;
  const sx = (xmm: number) => PADX + xmm * scale;
  const yUp = (r: number) => axisY - r * scale;
  const yDn = (r: number) => axisY + r * scale;

  const pConv = convLen;
  const pThroat = pConv + throatLen;
  const pExit = pThroat + divLen;
  const isBell = nz.contour_type === "bell";
  const nozStroke = badPart("nozzle") ? "var(--error)" : "var(--nozzle-metal-stroke)";

  // each half (top/bottom) is its own closed wedge tracing the outer profile out
  // to the exit and the inner (flow) profile back - never a solid filled bell -
  // so the flow passage is naturally unfilled (background shows through) instead
  // of needing a separate cavity shape drawn over it. The convergent inner
  // section is a straight cone at convergence_half_angle (that is what the
  // parameter means), not a curve.
  const divInner = (yy: (r: number) => number) =>
    isBell
      ? `C ${sx(pExit - divLen * 0.15)} ${yy(rE)} ${sx(pThroat + divLen * 0.3)} ${yy(rT)} ${sx(pThroat)} ${yy(rT)} `
      : `L ${sx(pThroat)} ${yy(rT)} `;
  const bell = (yy: (r: number) => number) =>
    `M ${sx(0)} ${yy(rOuter)} ` +
    `L ${sx(pExit)} ${yy(rOuter)} ` +
    `L ${sx(pExit)} ${yy(rE)} ` +
    `${divInner(yy)}` +
    `L ${sx(pConv)} ${yy(rT)} ` +
    `L ${sx(0)} ${yy(rChamber)} Z`;
  const material = nz.material_id ?? design.case.material_id;

  return (
    <div className="space-y-2">
      <svg ref={svgRef} xmlns="http://www.w3.org/2000/svg" viewBox={`0 0 ${W} ${H}`}
        className="min-w-[600px]" style={{ color: "var(--text)" }}>
        <path d={bell(yUp)} fill="var(--case-color)" stroke={nozStroke} strokeWidth={1.4}>
          <title>{`${t("drawing.nozzle")} · ${material}`}</title>
        </path>
        <path d={bell(yDn)} fill="var(--case-color)" stroke={nozStroke} strokeWidth={1.4} />
        <line x1={sx(-20)} y1={axisY} x2={sx(pExit) + 40} y2={axisY} stroke="var(--axis)"
          strokeWidth={0.7} strokeDasharray="10 3 2 3" />

        {/* dimensions */}
        <DimLine x1={sx(0) - 85} x2={sx(0) - 85} y={yUp(rOuter)} y2={yDn(rOuter)}
          vertical label={`d_o ${(rOuter * 2).toFixed(1)} mm`} />
        <DimLine x1={sx(pConv) + 22} x2={sx(pConv) + 22} y={yUp(rT)} y2={yDn(rT)}
          vertical label={`d_t ${(rT * 2).toFixed(1)} mm`} />
        <DimLine x1={sx(pExit) + 22} x2={sx(pExit) + 22} y={yUp(rE)} y2={yDn(rE)}
          vertical label={`d_e ${(rE * 2).toFixed(1)} mm`} />
        <DimLine x1={sx(0)} x2={sx(pConv)} y={PADY - 44} label={`L_c ${convLen.toFixed(1)} mm`} derived />
        <DimLine x1={sx(pConv)} x2={sx(pThroat)} y={PADY - 44} label={`L_t ${throatLen.toFixed(1)} mm`}
          derived />
        <DimLine x1={sx(pThroat)} x2={sx(pExit)} y={PADY - 44} label={`L_d ${divLen.toFixed(1)} mm`}
          derived />
        <DimLine x1={sx(0)} x2={sx(pExit)} y={H - PADY + 30} label={`L_total ${totalLen.toFixed(1)} mm`} />

        <text x={sx(pConv / 2)} y={yUp(rOuter) - 10} textAnchor="middle" fontSize={11}
          fill="var(--dim-derived)">
          {t("param.convergence_half_angle")} {nz.convergence_half_angle_deg.toFixed(0)}°
        </text>
        <text x={sx(pThroat + divLen / 2)} y={yUp(rOuter) - 10} textAnchor="middle" fontSize={11}
          fill="var(--dim-derived)">
          {t("param.divergence_half_angle")} {nz.divergence_half_angle_deg.toFixed(0)}° · {isBell ? "Bell" : "Conic"}
        </text>
        <text x={sx(pExit) + 26} y={PADY - 20} fontSize={11} fill="var(--dim-derived)">
          ε = {nz.expansion_ratio.toFixed(2)}
        </text>
      </svg>
      <p className="text-xs text-text-secondary">
        {t("drawing.nozzle")} · {material}
      </p>
    </div>
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
  // vertical labels are left-aligned, starting clear of the line, rather than
  // centred on it - centring would put half the text to the *left* of x1, which
  // for a dimension line running right off a part's edge means half the label
  // sits back over that part's own fill
  const mx = vertical ? x1 + 4 : (x1 + x2) / 2;
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
      <text x={mx} y={my} textAnchor={vertical ? "start" : "middle"} stroke="none">
        {label}
      </text>
    </g>
  );
}

function fmtCell(v: unknown): string {
  return v == null ? "" : typeof v === "number" ? v.toFixed(1) : String(v);
}
