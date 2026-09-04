import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "../api";
import { useStore } from "../store";
import type { SimResult } from "../types";
import { Dialog } from "./ui";

const FORMATS = ["eng", "rse", "csv", "json", "pdf", "svg", "nozzle_csv"] as const;

export function ExportDialog({
  open,
  onClose,
  result,
}: {
  open: boolean;
  onClose: () => void;
  result: SimResult | undefined;
}) {
  const { t, i18n } = useTranslation();
  const { design } = useStore();
  const [accept, setAccept] = useState(false);
  const [err, setErr] = useState("");
  const locked = Boolean(result?.export_locked);

  async function doExport(fmt: string) {
    setErr("");
    try {
      await api.exportFile(design, fmt, i18n.language === "tr" ? "tr" : "en", accept);
    } catch (e) {
      if (e instanceof ApiError && e.status === 423) setErr(t("ui.export_locked_why"));
      else setErr(String(e));
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title={t("ui.export")}>
      {locked && (
        <div className="mb-3 rounded bg-danger/10 p-2 text-xs text-danger">
          <p className="font-medium">{t("ui.export_locked")}</p>
          <p>{t("ui.export_locked_why")}</p>
          <label className="mt-1 flex items-center gap-1">
            <input type="checkbox" checked={accept} onChange={(e) => setAccept(e.target.checked)} />
            {t("ui.accept_risk")}
          </label>
        </div>
      )}
      <div className="space-y-1.5">
        {FORMATS.map((f) => {
          const safetyFmt = f === "eng" || f === "rse";
          const disabled = locked && safetyFmt && !accept;
          return (
            <div key={f} className="flex items-center justify-between gap-3 rounded border
                                     border-border p-2">
              <div className="min-w-0">
                <p className="font-mono text-sm font-semibold">.{f}</p>
                <p className="text-xs text-text-secondary">{t(`ui.export_desc.${f}`)}</p>
              </div>
              <button
                className="btn-ghost shrink-0 text-xs"
                disabled={disabled}
                onClick={() => doExport(f)}
                title={disabled ? t("ui.export_locked_why") : undefined}
              >
                {t("ui.download")}
              </button>
            </div>
          );
        })}
      </div>
      {err && <p className="mt-2 text-xs text-danger">{err}</p>}
    </Dialog>
  );
}
