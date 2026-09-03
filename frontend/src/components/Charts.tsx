import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { SimResult } from "../types";

const SERIES: { id: string; key: keyof SimResult["series"]; dash?: string }[] = [
  { id: "chamber_pressure", key: "chamber_pressure_bar" },
  { id: "thrust", key: "thrust_n", dash: "6 3" },
  { id: "kn", key: "kn", dash: "2 2" },
  { id: "burn_rate", key: "burn_rate_mm_s", dash: "4 2" },
  { id: "mass_flow", key: "mass_flow_kg_s", dash: "1 3" },
  { id: "impulse", key: "cumulative_impulse_ns", dash: "8 2 2 2" },
  { id: "burn_area", key: "burn_area_mm2", dash: "5 5" },
];

export function Charts({ result, webFraction }: { result: SimResult; webFraction: number }) {
  const { t } = useTranslation();
  const [active, setActive] = useState("chamber_pressure");
  const s = result.series;
  const cur = SERIES.find((x) => x.id === active)!;
  const data = (s.time_s ?? []).map((tt, i) => ({ t: tt, v: (s[cur.key] as number[])[i] }));
  const tb = Number(result.summary.burn_time ?? 0);
  const webMax = Math.max(...(s.web_mm ?? [0]));
  // map web fraction to a time via the web_mm array
  let markerT: number | null = null;
  if (webFraction > 0 && s.web_mm) {
    const target = webFraction * webMax;
    const idx = s.web_mm.findIndex((w) => w >= target);
    if (idx >= 0) markerT = s.time_s[idx];
  }

  return (
    <div>
      <div className="flex flex-wrap gap-1 pb-2">
        {SERIES.map((x) => (
          <button
            key={x.id}
            className={
              "rounded px-2 py-0.5 text-xs " +
              (active === x.id ? "bg-primary text-primary-fg" : "bg-surface-2 text-text-secondary")
            }
            onClick={() => setActive(x.id)}
          >
            {t(`chart.${x.id}`)}
          </button>
        ))}
      </div>
      <div className="h-64 w-full">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 6, right: 12, bottom: 4, left: 0 }}>
            <CartesianGrid stroke="var(--border)" strokeDasharray="2 3" />
            <XAxis
              dataKey="t"
              tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
              stroke="var(--border)"
              label={{ value: t("chart.time") + " (s)", position: "insideBottom", fontSize: 10 }}
            />
            <YAxis
              tick={{ fontSize: 10, fill: "var(--text-secondary)" }}
              stroke="var(--border)"
              width={48}
            />
            <Tooltip
              contentStyle={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                fontSize: 12,
              }}
              labelFormatter={(l) => `${t("chart.time")}: ${Number(l).toFixed(3)} s`}
              formatter={(v) => [Number(v).toFixed(2), t(`chart.${cur.id}`)] as [string, string]}
            />
            <Line
              type="monotone"
              dataKey="v"
              stroke="var(--primary)"
              strokeWidth={1.6}
              strokeDasharray={cur.dash}
              dot={false}
              isAnimationActive={false}
            />
            {tb > 0 && <ReferenceLine x={tb} stroke="var(--text-secondary)" strokeDasharray="3 3" />}
            {markerT != null && (
              <ReferenceLine x={markerT} stroke="var(--warning)" strokeWidth={1.5} />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
