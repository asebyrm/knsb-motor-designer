/** Shared constants between the full (Technical report) and compact (live preview)
 * engine cross-section drawings, kept out of the component files so fast-refresh
 * only sees components there. */

export const PART_FIT_CODES: Record<string, string[]> = {
  grain: ["WARN_FIT_GRAIN_DIAMETER", "WARN_FIT_GRAIN_LENGTH"],
  nozzle: ["WARN_FIT_THROAT_VS_CASE"],
  liner: ["WARN_FIT_LINER_STACK"],
};

/** Default layer set for the compact, non-editable preview (curves tab). */
export const PREVIEW_LAYERS = {
  dimensions: false,
  part_names: false,
  hatching: true,
  axis: true,
  burnt: true,
};

/** One distinct drawing color per liner material (backend/data/materials/liner_materials.yaml
 * IDs), so the liner band reads as the chosen material rather than a generic grey. */
export const LINER_COLORS: Record<string, string> = {
  kraft_phenolic: "#a97c46",
  cardboard: "#c9a066",
  graphite: "#3a3a3d",
  ceramic_blanket: "#e3dac9",
  sand_epoxy: "#c2a878",
};

export function linerColor(materialId?: string | null): string {
  return (materialId && LINER_COLORS[materialId]) || "var(--surface-2)";
}
