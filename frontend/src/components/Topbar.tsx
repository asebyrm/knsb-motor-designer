import { useTranslation } from "react-i18next";

import { defaultDesign, useStore } from "../store";
import { EXAMPLES } from "../lib/examples";
import { Logo } from "./Logo";
import { TipBar } from "./ui";

export function Topbar({
  onLogin,
  onSave,
  onExport,
  onOpenAdmin,
  view,
  setView,
}: {
  onLogin: () => void;
  onSave: () => void;
  onExport: () => void;
  onOpenAdmin: () => void;
  view: "designer" | "admin";
  setView: (v: "designer" | "admin") => void;
}) {
  const { t, i18n } = useTranslation();
  const { mode, setMode, units, setUnits, theme, setTheme, user, setUser, setDesign } = useStore();

  return (
    <header className="border-b border-border bg-surface">
      <div className="flex flex-wrap items-center gap-3 px-3 py-2">
        <button
          className="flex items-center gap-3 text-text"
          onClick={() => setView("designer")}
        >
          <Logo size={132} />
          <span className="text-xl font-semibold">KNSB Motor Designer</span>
        </button>

        <div className="ml-auto flex flex-wrap items-center gap-1.5 text-sm">
          <div className="flex overflow-hidden rounded-md border border-border">
            {(["basic", "expert"] as const).map((m) => (
              <button
                key={m}
                className={
                  "px-2 py-1 text-xs " +
                  (mode === m ? "bg-primary text-primary-fg" : "text-text-secondary")
                }
                onClick={() => setMode(m)}
              >
                {t(`ui.mode_${m}`)}
              </button>
            ))}
          </div>

          <select
            className="input w-auto text-xs"
            value=""
            onChange={(e) => {
              const ex = EXAMPLES.find((x) => x.key === e.target.value);
              if (ex) setDesign({ ...defaultDesign(), ...ex.design });
              e.currentTarget.value = "";
            }}
          >
            <option value="">{t("ui.examples")}…</option>
            {EXAMPLES.map((ex) => (
              <option key={ex.key} value={ex.key}>
                {t(`example.${ex.key}`)}
              </option>
            ))}
          </select>

          <button
            className="btn-ghost text-xs"
            onClick={() => setUnits(units === "metric" ? "imperial" : "metric")}
            title={t("info.action.toggle_units")}
          >
            {t(units === "metric" ? "ui.units_metric" : "ui.units_imperial")}
          </button>
          <button
            className="btn-ghost text-xs"
            onClick={() => i18n.changeLanguage(i18n.language === "tr" ? "en" : "tr")}
          >
            {i18n.language === "tr" ? "TR" : "EN"}
          </button>
          <button
            className="btn-ghost text-xs"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            {theme === "dark" ? "☾" : "☀"}
          </button>

          <button className="btn-ghost text-xs" onClick={onSave}>
            {t("ui.save")}
          </button>
          <button className="btn-primary text-xs" onClick={onExport}>
            {t("ui.export")}
          </button>

          {/* auth group — set apart from the tool buttons */}
          <span className="mx-1 h-6 w-px bg-border" aria-hidden />
          {user ? (
            <>
              {user.role === "admin" && (
                <button className="btn-ghost text-xs" onClick={onOpenAdmin}>
                  {t("nav.admin")}
                </button>
              )}
              <span className="hidden text-xs text-text-secondary sm:inline">
                {String(user.username)}
              </span>
              <button
                className="btn text-xs border border-primary text-primary hover:bg-primary hover:text-primary-fg"
                onClick={() => setUser(null, null)}
              >
                {t("ui.logout")}
              </button>
            </>
          ) : (
            <button
              className="btn bg-primary px-4 text-xs font-semibold text-primary-fg shadow-sm hover:opacity-90"
              onClick={onLogin}
            >
              {t("ui.login")}
            </button>
          )}
        </div>
      </div>

      {/* contextual help renders here, centred, so a scrolling panel never clips it */}
      <TipBar />

      {view === "admin" && (
        <button
          className="px-3 pb-1 text-left text-xs text-primary"
          onClick={() => setView("designer")}
        >
          ← {t("nav.designer")}
        </button>
      )}
    </header>
  );
}
