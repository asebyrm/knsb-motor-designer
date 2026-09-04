import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api, type Catalog } from "../api";
import { Charts } from "../components/Charts";
import { EngineCrossSection } from "../components/EngineCrossSection";
import { FormulasPanel } from "../components/FormulasPanel";
import { LiveCrossSections } from "../components/LiveCrossSections";
import { MaterialsPanel } from "../components/MaterialsPanel";
import { MissionPanel } from "../components/MissionPanel";
import { ParamPanel } from "../components/ParamPanel";
import { ResultsPanel } from "../components/ResultsPanel";
import { AccordionItem, Accordion, Tabs } from "../components/ui";
import { useStore } from "../store";
import type { SimResult } from "../types";

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return v;
}

export function Designer({ catalog }: { catalog: Catalog | undefined }) {
  const { t } = useTranslation();
  const { design, setField, webFraction, setWebFraction } = useStore();
  const [tab, setTab] = useState<"curves" | "cross_section" | "materials" | "formulas">("curves");

  const setLastResult = useStore((s) => s.setLastResult);
  const debounced = useDebounced(JSON.stringify(design), 300);
  const sim = useQuery<SimResult>({
    queryKey: ["sim", debounced],
    queryFn: () => api.simulate(design),
    placeholderData: (prev) => prev,
    retry: false,
  });
  useEffect(() => {
    if (sim.data) setLastResult(sim.data);
  }, [sim.data, setLastResult]);

  async function onAction(a: "make_neutral" | "optimum_expansion") {
    if (a === "make_neutral") {
      const r = await api.neutralLength(design.grain.outer_diameter, design.grain.core_diameter);
      setField("grain.segment_length", r.segment_length);
    } else {
      const r = await api.optimumExpansion(design);
      setField("nozzle.expansion_ratio", r.expansion_ratio);
    }
  }

  const result = sim.data;

  return (
    <div className="grid flex-1 grid-cols-1 gap-2 p-2 lg:grid-cols-[300px_1fr_320px]">
      {/* left: parameters + mission */}
      <div className="card overflow-y-auto">
        <ParamPanel catalog={catalog} onAction={onAction} />
        <Accordion>
          <AccordionItem id="mission" title={t("nav.mission")}>
            <MissionPanel />
          </AccordionItem>
        </Accordion>
      </div>

      {/* middle: charts / cross-section */}
      <div className="card flex flex-col overflow-hidden">
        <div className="px-3 pt-2">
          <Tabs
            tabs={[
              { id: "curves", label: t("ui.curves") },
              { id: "cross_section", label: t("ui.technical_report") },
              { id: "materials", label: t("ui.materials_tab") },
              { id: "formulas", label: t("ui.formulas_tab") },
            ]}
            active={tab}
            onChange={(id) => setTab(id as "curves" | "cross_section" | "materials" | "formulas")}
          />
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          {sim.isError && (
            <p className="text-sm text-danger">{String(sim.error)}</p>
          )}
          {tab === "curves" ? (
            <div className="space-y-4">
              {result && <Charts result={result} webFraction={webFraction} />}
              <div>
                <label className="field-label">{t("ui.web_slider")}</label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.02}
                  value={webFraction}
                  onChange={(e) => setWebFraction(Number(e.target.value))}
                  className="w-full"
                />
              </div>
              <LiveCrossSections result={result} />
            </div>
          ) : tab === "cross_section" ? (
            <EngineCrossSection result={result} />
          ) : tab === "materials" ? (
            <MaterialsPanel catalog={catalog} />
          ) : (
            <FormulasPanel />
          )}
        </div>
        {sim.isFetching && (
          <div className="border-t border-border px-3 py-1 text-xs text-text-secondary">
            {t("ui.recalculating")}
          </div>
        )}
      </div>

      {/* right: results */}
      <div className="card overflow-y-auto">
        <ResultsPanel result={result} />
      </div>
    </div>
  );
}
