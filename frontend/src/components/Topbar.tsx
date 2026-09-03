import { useTranslation } from "react-i18next";

import { defaultDesign, useStore } from "../store";
import { EXAMPLES } from "../lib/examples";
import { Logo } from "./Logo";

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
    <header className="flex flex-wrap items-center gap-2 border-b border-border bg-surface px-3 py-2">
      <button className="flex items-center gap-2 text-text" onClick={() => setView("designer")}>
        <Logo size={26} />
        <span className="font-semibold">KNSB Motor Designer</span>
      </button>
      <span className="hidden text-xs text-text-secondary md:inline">{t("ui.app_tagline")}</span>

      <div className="ml-auto flex flex-wrap items-center gap-1.5 text-sm">
        <div className="flex rounded-md border border-border">
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

        {user ? (
          <>
            {user.role === "admin" && (
              <button className="btn-ghost text-xs" onClick={onOpenAdmin}>
                {t("nav.admin")}
              </button>
            )}
            <button className="btn-ghost text-xs" onClick={() => setUser(null, null)}>
              {t("ui.logout")}
            </button>
          </>
        ) : (
          <button className="btn-ghost text-xs" onClick={onLogin}>
            {t("ui.login")}
          </button>
        )}
      </div>
      {view === "admin" && (
        <button className="w-full text-left text-xs text-primary" onClick={() => setView("designer")}>
          ← {t("nav.designer")}
        </button>
      )}
    </header>
  );
}
