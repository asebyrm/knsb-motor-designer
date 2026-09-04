import { useTranslation } from "react-i18next";

import type { Catalog } from "../api";
import { clampForUnit, CONV, isNonNegativeUnit } from "../lib/units";
import { FIELDS, type FieldDef } from "../lib/registry";
import { getPath, useStore } from "../store";
import { Accordion, AccordionItem, Info } from "./ui";

const GROUP_ORDER = [
  "propellant",
  "grain",
  "nozzle",
  "case",
  "liner",
  "bulkhead",
  "assembly",
  "environment",
  "calibration",
];

export function FieldRow({
  field,
  catalog,
}: {
  field: FieldDef;
  catalog: Catalog | undefined;
}) {
  const { t } = useTranslation();
  const { design, units, setField } = useStore();
  const raw = getPath(design, field.path);

  const label = t(`param.${field.id}`);
  const conv = CONV[field.unit];
  const unitLabel = conv.label(units);

  let control: React.ReactNode;
  if (field.kind === "bool") {
    const on = Boolean(raw);
    control = (
      <button
        type="button"
        role="switch"
        aria-checked={on}
        aria-label={label}
        onClick={() => setField(field.path, !on)}
        className={
          "rounded-md px-2.5 py-1 text-xs font-semibold transition-colors " +
          (on
            ? "bg-primary text-primary-fg"
            : "border border-border bg-surface text-text-secondary hover:bg-surface-2")
        }
      >
        {on ? t("ui.on") : t("ui.off")}
      </button>
    );
  } else if (field.kind === "select") {
    let options = field.options ?? [];
    if (field.id === "propellant_id") options = (catalog?.propellants ?? []).map((p) => p.id);
    if (field.id === "case_material" || field.id === "bulkhead_material")
      options = (catalog?.case_materials ?? []).map((m) => m.id);
    if (field.id === "liner_material")
      options = (catalog?.liner_materials ?? []).map((m) => m.id);
    control = (
      <select
        className="input"
        value={String(raw ?? "")}
        onChange={(e) => setField(field.path, e.target.value)}
        aria-label={label}
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    );
  } else {
    const displayVal =
      raw == null ? "" : Number(conv.toDisplay(Number(raw), units).toFixed(conv.digits + 2));
    control = (
      <div className="flex items-center gap-1">
        <input
          type="number"
          className="input"
          value={displayVal}
          step={field.step}
          min={isNonNegativeUnit(field.unit) ? 0 : undefined}
          onChange={(e) => {
            if (e.target.value === "") {
              setField(field.path, null);
              return;
            }
            const clamped = clampForUnit(Number(e.target.value), field.unit);
            setField(field.path, conv.fromDisplay(clamped, units));
          }}
          aria-label={label}
        />
        {unitLabel && <span className="w-8 shrink-0 text-xs text-text-secondary">{unitLabel}</span>}
      </div>
    );
  }

  return (
    <label className="grid grid-cols-[1fr_130px] items-center gap-2">
      <span className="flex items-center field-label">
        {label}
        <Info tKey={`info.param.${field.id}`} />
      </span>
      {control}
    </label>
  );
}

export function ParamPanel({
  catalog,
  onAction,
}: {
  catalog: Catalog | undefined;
  onAction: (a: "make_neutral" | "optimum_expansion") => void;
}) {
  const { t } = useTranslation();
  const { mode, design } = useStore();
  const fields = FIELDS.filter((f) => (mode === "basic" ? f.basic : true));
  const byGroup = new Map<string, FieldDef[]>();
  for (const f of fields) {
    if (!byGroup.has(f.group)) byGroup.set(f.group, []);
    byGroup.get(f.group)!.push(f);
  }

  return (
    <Accordion defaultOpen={["propellant", "grain", "nozzle", "case"]}>
      {GROUP_ORDER.filter((g) => byGroup.has(g)).map((g) => (
        <AccordionItem key={g} id={g} title={t(`group.${g}`)}>
          {byGroup.get(g)!.map((f) => {
            const hideErosionDetail =
              g === "nozzle" &&
              (f.id === "erosion_coefficient" || f.id === "erosion_exponent") &&
              !design.nozzle.erosion.enabled;
            if (hideErosionDetail) return null;
            return <FieldRow key={f.id} field={f} catalog={catalog} />;
          })}
          {g === "grain" && design.grain.type === "bates" && (
            <div className="mt-1 flex items-center">
              <button
                className="btn-ghost w-full text-xs"
                onClick={() => onAction("make_neutral")}
              >
                {t("action.make_neutral")}
              </button>
              <Info tKey="info.action.make_neutral" />
            </div>
          )}
          {g === "nozzle" && (
            <div className="mt-1 flex items-center">
              <button
                className="btn-ghost w-full text-xs"
                onClick={() => onAction("optimum_expansion")}
              >
                {t("action.optimum_expansion")}
              </button>
              <Info tKey="info.action.optimum_expansion" />
            </div>
          )}
        </AccordionItem>
      ))}
    </Accordion>
  );
}
