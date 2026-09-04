import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { CONV } from "../lib/units";
import { useStore } from "../store";
import type { DesignDoc, SimResult } from "../types";
import { Info } from "./ui";

type Part = SimResult["assembly"]["parts"][number];

const PART_FIT_CODES: Record<string, string[]> = {
  grain: ["WARN_FIT_GRAIN_DIAMETER", "WARN_FIT_GRAIN_LENGTH"],
  nozzle: ["WARN_FIT_THROAT_VS_CASE"],
  liner: ["WARN_FIT_LINER_STACK"],
};

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
  const { t } = useTranslation();
  const { design, units, setField, webFraction } = useStore();
  const svgRef = useRef<SVGSVGElement>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [section, setSection] = useState<"long" | "trans">("long");
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

  function downloadSvg() {
    if (!svgRef.current) return;
    const blob = new Blob([svgRef.current.outerHTML], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${design.name.replace(/\s+/g, "_")}-${section}.svg`;
    a.click();
    URL.revokeObjectURL(url);
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
        <button className="btn-ghost ml-auto text-xs" onClick={downloadSvg}>
          {t("ui.download_drawing")}
        </button>
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

function LongitudinalSVG({
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
  const x0 = Math.min(...parts.map((p) => p.x_start_mm));
  const x1 = Math.max(...parts.map((p) => p.x_end_mm));
  const dMax = Math.max(...parts.map((p) => p.outer_diameter_mm));

  const W = 760;
  const PAD = 74;
  const drawW = W - 2 * PAD;
  const spanMm = Math.max(x1 - x0, 1);
  const scale = drawW / spanMm;
  const H = Math.round(dMax * scale) + 2 * PAD + 30;
  const axisY = PAD + (dMax * scale) / 2;
  const sx = (xmm: number) => PAD + (xmm - x0) * scale;
  const yR = (rmm: number) => axisY - rmm * scale; // radius -> upper y
  const ratio = spanMm / drawW;
  const hatch = layers.hatching ? "url(#hatch)" : "none";
  const g = design.grain;
  const linerT = design.liner?.thickness ?? 0;

  const case_ = parts.find((p) => p.name === "case");
  const liner = parts.find((p) => p.name === "liner");
  const grain = parts.find((p) => p.name === "grain");
  const bh = parts.find((p) => p.name === "bulkhead");
  const nozzle = parts.find((p) => p.name === "nozzle");

  const els: React.ReactNode[] = [];
  const stroke = (n: string) => (badPart(n) ? "var(--error)" : "currentColor");

  // helper: a hatched band between two radii over an x range, mirrored about the axis
  const band = (
    key: string,
    xa: number,
    xb: number,
    rOuter: number,
    rInner: number,
    fill: string,
    partName: string,
  ) => {
    const w = (xb - xa) * scale;
    const s = stroke(partName);
    return [
      <rect key={`${key}-t`} x={sx(xa)} y={yR(rOuter)} width={w} height={(rOuter - rInner) * scale}
        fill={fill} stroke={s} strokeWidth={1}><title>{partName}</title></rect>,
      <rect key={`${key}-b`} x={sx(xa)} y={axisY + rInner * scale} width={w}
        height={(rOuter - rInner) * scale} fill={fill} stroke={s} strokeWidth={1} />,
    ];
  };

  if (layers.axis) {
    els.push(
      <line key="axis" x1={PAD - 22} y1={axisY} x2={W - PAD + 22} y2={axisY}
        stroke="var(--axis)" strokeWidth={0.7} strokeDasharray="10 3 2 3" />,
    );
  }

  if (bh) els.push(...band("bh", bh.x_start_mm, bh.x_end_mm, bh.outer_diameter_mm / 2, 0, hatch, "bulkhead"));

  if (case_) {
    els.push(...band("case", case_.x_start_mm, case_.x_end_mm, case_.outer_diameter_mm / 2,
      case_.inner_diameter_mm / 2, hatch, "case"));
  }
  if (liner && liner.outer_diameter_mm > liner.inner_diameter_mm) {
    els.push(...band("liner", liner.x_start_mm, liner.x_end_mm, liner.outer_diameter_mm / 2,
      liner.inner_diameter_mm / 2, "var(--surface-2)", "liner"));
  }

  // grain: N segments with gaps; burnt bore shown darker
  if (grain) {
    const rGrainOuter = (g.outer_diameter * 1000) / 2;
    const coreNow = (burntCoreDia(g, layers.burnt ? webFraction : 0) * 1000) / 2;
    const coreInit = (g.core_diameter * 1000) / 2;
    const n = g.type === "endburner" ? 1 : Math.max(1, g.segment_count);
    const gapMm = g.type === "bates" ? g.segment_spacing * 1000 : 0;
    const segMm = g.type === "endburner" || g.type === "tubular"
      ? grain.x_end_mm - grain.x_start_mm
      : g.segment_length * 1000;
    for (let i = 0; i < n; i++) {
      const xa = grain.x_start_mm + i * (segMm + gapMm);
      const xb = Math.min(xa + segMm, grain.x_end_mm);
      els.push(...band(`grain-${i}`, xa, xb, rGrainOuter, coreNow, "var(--grain-fill)", "grain"));
      if (layers.burnt && coreNow > coreInit) {
        els.push(...band(`burnt-${i}`, xa, xb, coreNow, coreInit, "var(--burnt-fill)", "grain"));
      }
    }
  }

  // nozzle: wall between the C-D flow contour and the nozzle OD
  if (nozzle) {
    const nz = design.nozzle;
    const rT = (nz.throat_diameter * 1000) / 2;
    const rE = rT * Math.sqrt(nz.expansion_ratio);
    const rChamRaw = (design.case.inner_diameter / 2 - linerT) * 1000;
    const rCham = rChamRaw > rT ? rChamRaw : rT * 3;
    const nozLen = nozzle.x_end_mm - nozzle.x_start_mm;
    let convLen = Math.max(rCham - rT, 0) / Math.tan(deg(nz.convergence_half_angle_deg));
    let divLen = Math.max(rE - rT, 0) / Math.tan(deg(nz.divergence_half_angle_deg));
    let throatLen = nz.throat_length * 1000 || 0.3 * rT;
    // keep the three segments within the part's actual axial length
    const sumLen = convLen + throatLen + divLen || 1;
    const kLen = nozLen / sumLen;
    convLen *= kLen;
    throatLen *= kLen;
    divLen *= kLen;
    const nx = nozzle.x_start_mm;
    const rOD = nozzle.outer_diameter_mm / 2;
    const p1 = nx;
    const p2 = nx + convLen;
    const p3 = p2 + throatLen;
    const p4 = p3 + divLen;
    const s = stroke("nozzle");
    // top wall: outer edge across, then inner contour back
    const top = `M ${sx(p1)} ${yR(rOD)} L ${sx(p4)} ${yR(rOD)} L ${sx(p4)} ${yR(rE)} ` +
      `L ${sx(p3)} ${yR(rT)} L ${sx(p2)} ${yR(rT)} L ${sx(p1)} ${yR(rCham)} Z`;
    const bot = `M ${sx(p1)} ${axisY + rOD * scale} L ${sx(p4)} ${axisY + rOD * scale} ` +
      `L ${sx(p4)} ${axisY + rE * scale} L ${sx(p3)} ${axisY + rT * scale} ` +
      `L ${sx(p2)} ${axisY + rT * scale} L ${sx(p1)} ${axisY + rCham * scale} Z`;
    els.push(
      <path key="noz-t" d={top} fill={hatch} stroke={s} strokeWidth={1}><title>nozzle</title></path>,
      <path key="noz-b" d={bot} fill={hatch} stroke={s} strokeWidth={1} />,
      <line key="noz-cl-t" x1={sx(p1)} y1={yR(rCham)} x2={sx(p2)} y2={yR(rT)}
        stroke={s} strokeWidth={0.6} opacity={0.5} />,
    );
  }

  if (layers.part_names) {
    for (const p of parts) {
      els.push(
        <text key={`name-${p.name}`} x={sx((p.x_start_mm + p.x_end_mm) / 2)} y={axisY + 3.5}
          textAnchor="middle" fontSize={9} fill="var(--dim-derived)">{p.name}</text>,
      );
    }
  }

  if (layers.dimensions) {
    els.push(
      <DimLine key="ltot" x1={sx(x0)} x2={sx(x1)} y={PAD - 40}
        label={`L_total ${(x1 - x0).toFixed(1)} mm`} derived />,
      <DimLine key="dmax" x1={sx(x1) + 16} x2={sx(x1) + 16} y={yR(dMax / 2)} y2={axisY + (dMax / 2) * scale}
        vertical label={`D ${dMax.toFixed(1)} mm`} />,
    );
    if (grain) {
      els.push(
        <DimLine key="gl" x1={sx(grain.x_start_mm)} x2={sx(grain.x_end_mm)}
          y={yR(g.outer_diameter * 500) - 16}
          label={`grain ${(grain.x_end_mm - grain.x_start_mm).toFixed(1)} mm`} />,
      );
    }
  }

  return (
    <svg ref={svgRef} xmlns="http://www.w3.org/2000/svg" viewBox={`0 0 ${W} ${H}`}
      className="min-w-[700px]" style={{ color: "var(--text)" }}>
      <defs>
        <pattern id="hatch" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
          <line x1="0" y1="0" x2="0" y2="6" stroke="var(--border)" strokeWidth="1" />
        </pattern>
      </defs>
      {els}
      <text x={PAD} y={H - 8} fontSize={11} fill="var(--dim-derived)">
        {t("ui.scale")} 1 : {ratio.toFixed(2)} · {t("ui.derived_value")}
      </text>
    </svg>
  );
}

/* ---------------------------------------------------- transverse cross-section */

function TransverseSVG({
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
  const k = (c - 14) / rCaseO; // scale m -> px
  const ring = (r: number, fill: string, s: string, sw = 1) => (
    <circle cx={c} cy={c} r={r * k} fill={fill} stroke={s} strokeWidth={sw} />
  );
  return (
    <svg ref={svgRef} xmlns="http://www.w3.org/2000/svg" viewBox={`0 0 ${S} ${S}`}
      className="mx-auto block max-h-[340px]" style={{ color: "var(--text)" }}>
      {ring(rCaseO, "url(#hatch2)", badPart("case") ? "var(--error)" : "currentColor", 1.3)}
      {ring(rCaseI, "var(--surface)", badPart("case") ? "var(--error)" : "currentColor")}
      {linerT > 0 &&
        ring(rLinerI, "var(--surface-2)", badPart("liner") ? "var(--error)" : "currentColor")}
      {ring(
        rGrainO,
        "var(--grain-fill)",
        badPart("grain") ? "var(--error)" : "currentColor",
        badPart("grain") ? 1.6 : 1,
      )}
      {g.type !== "endburner" && rCore > 0 && ring(rCore, "var(--burnt-fill)", "none")}
      {g.type !== "endburner" && rCore > rCoreInit + 1e-9 && (
        <circle cx={c} cy={c} r={rCoreInit * k} fill="none" stroke="currentColor"
          strokeDasharray="2 2" strokeWidth={0.8} opacity={0.5} />
      )}
      <defs>
        <pattern id="hatch2" width="7" height="7" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
          <line x1="0" y1="0" x2="0" y2="7" stroke="var(--border)" strokeWidth="1" />
        </pattern>
      </defs>
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
