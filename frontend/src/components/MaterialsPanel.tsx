import { useTranslation } from "react-i18next";

import type { Catalog } from "../api";
import { getPath, useStore } from "../store";
import { Info } from "./ui";

/**
 * OpenRocket-style material editor (Section 5.6/5.7): every property the
 * structural/thermal analysis actually reads, per selected material, with an
 * inline override for when your own sample differs from the catalog (e.g. your
 * cardboard liner is denser than the reference value). Overrides live on the
 * design itself (`<section>.material_overrides`), not the shared catalog, so they
 * never affect anyone else's design.
 */

const CASE_PROPS = [
  "density", "tensile_strength", "yield_strength", "elastic_modulus",
  "print_direction_factor", "thermal_conductivity", "specific_heat",
  "glass_transition", "max_service_temp",
] as const;
const LINER_PROPS = [
  "density", "ablation_rate", "min_thickness", "thermal_conductivity",
  "specific_heat", "max_interface_temp",
] as const;

interface PropFmt {
  suffix: string;
  toDisplay: (si: number) => number;
  fromDisplay: (d: number) => number;
  digits: number;
}

const PROP_FMT: Record<string, PropFmt> = {
  density: { suffix: "kg/m³", toDisplay: (v) => v, fromDisplay: (v) => v, digits: 0 },
  tensile_strength: { suffix: "MPa", toDisplay: (v) => v / 1e6, fromDisplay: (v) => v * 1e6, digits: 1 },
  yield_strength: { suffix: "MPa", toDisplay: (v) => v / 1e6, fromDisplay: (v) => v * 1e6, digits: 1 },
  elastic_modulus: { suffix: "GPa", toDisplay: (v) => v / 1e9, fromDisplay: (v) => v * 1e9, digits: 2 },
  print_direction_factor: { suffix: "", toDisplay: (v) => v, fromDisplay: (v) => v, digits: 2 },
  thermal_conductivity: { suffix: "W/(m·K)", toDisplay: (v) => v, fromDisplay: (v) => v, digits: 3 },
  specific_heat: { suffix: "J/(kg·K)", toDisplay: (v) => v, fromDisplay: (v) => v, digits: 0 },
  glass_transition: { suffix: "K", toDisplay: (v) => v, fromDisplay: (v) => v, digits: 0 },
  max_service_temp: { suffix: "K", toDisplay: (v) => v, fromDisplay: (v) => v, digits: 0 },
  ablation_rate: { suffix: "mm/s", toDisplay: (v) => v * 1000, fromDisplay: (v) => v / 1000, digits: 3 },
  min_thickness: { suffix: "mm", toDisplay: (v) => v * 1000, fromDisplay: (v) => v / 1000, digits: 2 },
  max_interface_temp: { suffix: "K", toDisplay: (v) => v, fromDisplay: (v) => v, digits: 0 },
};

interface Slot {
  key: string;
  titleKey: string;
  materialId: string | null;
  overridePath: string;
  props: readonly string[];
  catalogList: Catalog["case_materials"] | Catalog["liner_materials"] | undefined;
}

export function MaterialsPanel({ catalog }: { catalog: Catalog | undefined }) {
  const { t } = useTranslation();
  const { design } = useStore();

  const slots: Slot[] = [
    { key: "case", titleKey: "group.case", materialId: design.case.material_id,
      overridePath: "case.material_overrides", props: CASE_PROPS, catalogList: catalog?.case_materials },
    { key: "bulkhead", titleKey: "group.bulkhead", materialId: design.bulkhead.material_id,
      overridePath: "bulkhead.material_overrides", props: CASE_PROPS, catalogList: catalog?.case_materials },
    { key: "nozzle", titleKey: "param.nozzle_material",
      materialId: design.nozzle.material_id ?? design.case.material_id,
      overridePath: "nozzle.material_overrides", props: CASE_PROPS, catalogList: catalog?.case_materials },
  ];
  if (design.liner) {
    slots.splice(2, 0, {
      key: "liner", titleKey: "group.liner", materialId: design.liner.material_id,
      overridePath: "liner.material_overrides", props: LINER_PROPS, catalogList: catalog?.liner_materials,
    });
  }

  return (
    <div className="space-y-4 p-3">
      <p className="text-xs text-text-secondary">{t("ui.materials_hint")}</p>
      {slots.map((slot) => (
        <MaterialCard key={slot.key} slot={slot} />
      ))}
    </div>
  );
}

function MaterialCard({ slot }: { slot: Slot }) {
  const { t } = useTranslation();
  const { design, setField } = useStore();
  const entry = slot.catalogList?.find((m) => m.id === slot.materialId);
  const overrides = (getPath(design, slot.overridePath) as Record<string, number> | undefined) ?? {};

  if (!entry) {
    return (
      <div className="card p-3 text-xs text-text-secondary">
        {t(slot.titleKey)}: {slot.materialId ?? "—"}
      </div>
    );
  }

  function setOverride(prop: string, si: number | null) {
    const next = { ...overrides };
    if (si == null || Number.isNaN(si)) delete next[prop];
    else next[prop] = si;
    setField(slot.overridePath, Object.keys(next).length ? next : null);
  }

  return (
    <div className="card p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-semibold">{t(slot.titleKey)}</span>
        <span className="font-mono text-xs text-text-secondary">{entry.id}</span>
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-left text-text-secondary">
            <th className="py-1 font-normal">{t("ui.materials_property")}</th>
            <th className="py-1 text-right font-normal">{t("ui.materials_catalog_value")}</th>
            <th className="py-1 text-right font-normal">{t("ui.materials_your_value")}</th>
            <th className="py-1" />
          </tr>
        </thead>
        <tbody>
          {slot.props.map((prop) => {
            const fmt = PROP_FMT[prop];
            const catalogSi = entry.properties[prop];
            if (catalogSi == null) return null;
            const overridden = overrides[prop] != null;
            const effectiveSi = overridden ? overrides[prop] : catalogSi;
            return (
              <tr key={prop} className="border-t border-border/60">
                <td className="py-1 pr-2">
                  <span className="flex items-center">
                    {t(`materials.prop.${prop}`)}
                    <Info tKey={`info.materials.prop.${prop}`} />
                  </span>
                </td>
                <td className="py-1 text-right font-mono text-text-secondary">
                  {fmt.toDisplay(catalogSi).toFixed(fmt.digits)} {fmt.suffix}
                </td>
                <td className="py-1 text-right">
                  <input
                    type="number"
                    className={`input w-24 text-right ${overridden ? "border-primary" : ""}`}
                    value={Number(fmt.toDisplay(effectiveSi).toFixed(fmt.digits + 2))}
                    onChange={(e) => {
                      const d = Number(e.target.value);
                      setOverride(prop, Number.isFinite(d) ? fmt.fromDisplay(d) : null);
                    }}
                  />
                  <span className="ml-1 text-text-secondary">{fmt.suffix}</span>
                </td>
                <td className="py-1 pl-1">
                  {overridden && (
                    <button className="btn-ghost px-1.5 py-0.5 text-xs" title={t("ui.materials_reset")}
                      onClick={() => setOverride(prop, null)}>
                      ↺
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
