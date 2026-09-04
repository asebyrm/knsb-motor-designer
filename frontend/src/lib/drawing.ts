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
