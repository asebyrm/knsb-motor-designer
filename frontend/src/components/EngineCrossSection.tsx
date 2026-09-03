import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { CONV } from "../lib/units";
import { useStore } from "../store";
import type { SimResult } from "../types";
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
  path?: string; // editable if set
  unit: keyof typeof CONV;
  value: number; // SI
  derived?: boolean;
  derivedKey?: string;
}

export function EngineCrossSection({ result }: { result: SimResult | undefined }) {
  const { t } = useTranslation();
  const { design, units, setField, webFraction } = useStore();
  const svgRef = useRef<SVGSVGElement>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [layers, setLayers] = useState({
    dimensions: true,
    names: true,
    hatching: true,
    axis: true,
    burnt: true,
  });

  const parts = result?.assembly.parts ?? [];
  const fitCodes = new Set((result?.assembly.fit_warnings ?? []).map((w) => w.code));

  const bounds = useMemo(() => {
    if (!parts.length) return { x0: 0, x1: 100, d: 60 };
    const x0 = Math.min(...parts.map((p) => p.x_start_mm));
    const x1 = Math.max(...parts.map((p) => p.x_end_mm));
    const d = Math.max(...parts.map((p) => p.outer_diameter_mm));
    return { x0, x1, d };
  }, [parts]);

  const W = 720;
  const PAD = 70;
  const drawW = W - 2 * PAD;
  const spanMm = Math.max(bounds.x1 - bounds.x0, 1);
  const scale = drawW / spanMm; // px per mm
  const H = Math.round(bounds.d * scale) + 2 * PAD + 40;
  const axisY = PAD + (bounds.d * scale) / 2;
  const sx = (xmm: number) => PAD + (xmm - bounds.x0) * scale;
  const syUp = (dmm: number) => axisY - (dmm / 2) * scale;
  const syDn = (dmm: number) => axisY + (dmm / 2) * scale;
  const ratio = spanMm / drawW; // real mm per drawn px

  const g = design.grain;
  const noz = design.nozzle;
  const dims: DimRow[] = [
    { id: "grain_od", label: t("param.outer_diameter"), path: "grain.outer_diameter", unit: "length_mm", value: g.outer_diameter },
    { id: "grain_core", label: t("param.core_diameter"), path: "grain.core_diameter", unit: "length_mm", value: g.core_diameter },
    { id: "seg_len", label: t("param.segment_length"), path: "grain.segment_length", unit: "length_mm", value: g.segment_length },
    { id: "throat", label: t("param.throat_diameter"), path: "nozzle.throat_diameter", unit: "length_mm", value: noz.throat_diameter },
    { id: "wall", label: t("param.case_wall_thickness"), path: "case.wall_thickness", unit: "length_mm", value: design.case.wall_thickness },
    { id: "case_id", label: t("param.case_inner_diameter"), path: "case.inner_diameter", unit: "length_mm", value: design.case.inner_diameter },
    { id: "liner_t", label: t("param.liner_thickness"), path: "liner.thickness", unit: "length_mm", value: design.liner?.thickness ?? 0 },
    // derived
    { id: "web", label: t("info.derived.web") ? "web w" : "web", unit: "length_mm", value: webThickness(g), derived: true, derivedKey: "web" },
    { id: "exit_d", label: "D_e", unit: "length_mm", value: noz.throat_diameter * Math.sqrt(noz.expansion_ratio), derived: true, derivedKey: "exit_diameter" },
    { id: "total_len", label: "L_total", unit: "length_mm", value: (Number(result?.summary.total_length_mm ?? 0)) / 1000, derived: true, derivedKey: "total_length" },
    { id: "lstar", label: "L*", unit: "length_mm", value: (result?.assembly.lstar_mm ?? 0) / 1000, derived: true, derivedKey: "lstar" },
  ];

  function commit(row: DimRow, displayValue: string) {
    if (!row.path) return;
    const si = CONV[row.unit].fromDisplay(Number(displayValue), units);
    setField(row.path, si);
    setEditing(null);
  }

  function downloadSvg() {
    if (!svgRef.current) return;
    const blob = new Blob([svgRef.current.outerHTML], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${design.name.replace(/\s+/g, "_")}-drawing.svg`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <span className="text-text-secondary">
          {t("ui.scale")} 1 : {ratio.toFixed(2)}
        </span>
        {(["dimensions", "names", "hatching", "axis", "burnt"] as const).map((k) => (
          <label key={k} className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={layers[k]}
              onChange={(e) => setLayers((s) => ({ ...s, [k]: e.target.checked }))}
            />
            {t(`ui.layer_${k === "names" ? "part_names" : k}`)}
          </label>
        ))}
        <button className="btn-ghost ml-auto text-xs" onClick={downloadSvg}>
          {t("ui.download_drawing")}
        </button>
      </div>

      <div className="relative overflow-x-auto rounded-lg border border-border bg-surface">
        <svg
          ref={svgRef}
          xmlns="http://www.w3.org/2000/svg"
          viewBox={`0 0 ${W} ${H}`}
          className="min-w-[680px]"
          style={{ color: "var(--text)" }}
        >
          {layers.axis && (
            <line
              x1={PAD - 20}
              y1={axisY}
              x2={W - PAD + 20}
              y2={axisY}
              stroke="var(--axis)"
              strokeWidth={0.7}
              strokeDasharray="8 3 2 3"
            />
          )}
          {parts.map((p) => {
            const bad = (PART_FIT_CODES[p.name] ?? []).some((c) => fitCodes.has(c));
            const stroke = bad ? "var(--error)" : "currentColor";
            return (
              <g key={p.name}>
                <rect
                  x={sx(p.x_start_mm)}
                  y={syUp(p.outer_diameter_mm)}
                  width={(p.x_end_mm - p.x_start_mm) * scale}
                  height={p.outer_diameter_mm * scale}
                  fill={layers.hatching ? "url(#hatch)" : "none"}
                  stroke={stroke}
                  strokeWidth={1.2}
                >
                  <title>{partTitle(p)}</title>
                </rect>
                {p.inner_diameter_mm > 0 && (
                  <rect
                    x={sx(p.x_start_mm)}
                    y={syUp(p.inner_diameter_mm)}
                    width={(p.x_end_mm - p.x_start_mm) * scale}
                    height={p.inner_diameter_mm * scale}
                    fill="var(--surface)"
                    stroke={stroke}
                    strokeWidth={0.7}
                    opacity={0.85}
                  />
                )}
                {p.name === "grain" && layers.burnt && webFraction > 0 && (
                  <rect
                    x={sx(p.x_start_mm)}
                    y={syUp(burntInnerMm(g, webFraction))}
                    width={(p.x_end_mm - p.x_start_mm) * scale}
                    height={burntInnerMm(g, webFraction) * scale}
                    fill="var(--burnt-fill)"
                    opacity={0.5}
                  />
                )}
                {layers.names && (
                  <text
                    x={sx((p.x_start_mm + p.x_end_mm) / 2)}
                    y={axisY + 4}
                    textAnchor="middle"
                    fontSize={9}
                    fill="var(--dim-derived)"
                  >
                    {p.name}
                  </text>
                )}
              </g>
            );
          })}
          {layers.dimensions && parts.length > 0 && (
            <>
              <DimLine
                x1={sx(bounds.x0)}
                x2={sx(bounds.x1)}
                y={PAD - 34}
                label={`L_total ${fmt(dims.find((d) => d.id === "total_len")!.value, units)}`}
                derived
              />
              <DimLine
                x1={sx(bounds.x1) + 14}
                x2={sx(bounds.x1) + 14}
                y={syUp(bounds.d)}
                y2={syDn(bounds.d)}
                vertical
                label={`D_max ${fmt(bounds.d / 1000, units)}`}
              />
            </>
          )}
          <defs>
            <pattern id="hatch" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="0" y2="6" stroke="var(--border)" strokeWidth="1" />
            </pattern>
          </defs>
        </svg>
      </div>

      {/* dimension table: input dims editable, derived italic + calculated note */}
      <table className="w-full text-sm">
        <tbody>
          {dims.map((row) => {
            const disp = CONV[row.unit].toDisplay(row.value, units);
            const label = CONV[row.unit].label(units);
            return (
              <tr key={row.id} className="border-b border-border/60">
                <td className="py-1 pr-2">
                  <span
                    className={
                      row.derived ? "italic text-text-secondary" : "text-text"
                    }
                  >
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
                      {disp.toFixed(2)} {label}
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
            <tr
              key={i}
              className={r.part === "TOTAL" ? "border-t border-border font-semibold" : ""}
            >
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
      <line
        x1={x1}
        y1={y}
        x2={vertical ? x1 : x2}
        y2={vertical ? y2 : y}
        strokeDasharray={derived ? "4 3" : undefined}
        strokeWidth={0.6}
      />
      <text x={mx} y={my} textAnchor="middle" stroke="none">
        {label}
      </text>
    </g>
  );
}

function webThickness(g: { type: string; outer_diameter: number; core_diameter: number; segment_length: number }): number {
  if (g.type === "endburner") return g.segment_length;
  const radial = (g.outer_diameter - g.core_diameter) / 2;
  if (g.type === "tubular") return radial;
  return Math.min(radial, g.segment_length / 2);
}

function burntInnerMm(
  g: { type: string; outer_diameter: number; core_diameter: number; segment_length: number },
  frac: number,
): number {
  if (g.type === "endburner") return 0;
  const x = frac * webThickness(g);
  return (g.core_diameter + 2 * x) * 1000;
}

function fmt(si: number, units: "metric" | "imperial"): string {
  const d = CONV.length_mm.toDisplay(si, units);
  return `${d.toFixed(1)} ${CONV.length_mm.label(units)}`;
}
function fmtCell(v: unknown): string {
  return v == null ? "" : typeof v === "number" ? v.toFixed(1) : String(v);
}
function partTitle(p: Part): string {
  return `${p.name} · ${p.material_id} · ${p.mass_g.toFixed(1)} g · Ø${p.outer_diameter_mm.toFixed(1)} mm`;
}
