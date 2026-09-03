import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "./api";
import { AuthDialog } from "./components/AuthDialog";
import { ExportDialog } from "./components/ExportDialog";
import { Logo } from "./components/Logo";
import { Topbar } from "./components/Topbar";
import { Dialog } from "./components/ui";
import { Admin } from "./pages/Admin";
import { Designer } from "./pages/Designer";
import { bootToken, useStore } from "./store";

const DISCLAIMER_KEY = "knsb.disclaimer.accepted";

export default function App() {
  const { t } = useTranslation();
  const { theme, setUser, user, design, lastResult } = useStore();
  const [view, setView] = useState<"designer" | "admin">("designer");
  const [authOpen, setAuthOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [authReason, setAuthReason] = useState<string | undefined>();
  const [disclaimer, setDisclaimer] = useState(!localStorage.getItem(DISCLAIMER_KEY));

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const token = bootToken();
    if (token) api.me().then((u) => setUser(u, token)).catch(() => setUser(null, null));
  }, [setUser]);

  const catalog = useQuery({ queryKey: ["catalog"], queryFn: api.catalog, staleTime: Infinity });

  async function onSave() {
    if (!user) {
      setAuthReason(t("auth.save_prompt"));
      setAuthOpen(true);
      return;
    }
    await api.saveDesign({ name: design.name, config_json: design, visibility: "private" });
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Topbar
        onLogin={() => {
          setAuthReason(undefined);
          setAuthOpen(true);
        }}
        onSave={onSave}
        onExport={() => setExportOpen(true)}
        onOpenAdmin={() => setView("admin")}
        view={view}
        setView={setView}
      />

      {view === "admin" ? <Admin /> : <Designer catalog={catalog.data} />}

      <footer className="flex items-center justify-between border-t border-border bg-surface px-3 py-2 text-xs text-text-secondary">
        <span className="flex items-center gap-1.5">
          <Logo size={16} variant="mark" /> KNSB Motor Designer
        </span>
        <a
          href="https://github.com/asebyrm"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-text"
        >
          by PARS Rocketry Team
        </a>
      </footer>

      <AuthDialog open={authOpen} onClose={() => setAuthOpen(false)} reason={authReason} />
      <ExportDialog
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        result={lastResult ?? undefined}
      />

      <Dialog
        open={disclaimer}
        onClose={() => {}}
        title={t("ui.disclaimer_title")}
      >
        <p className="text-sm">{t("disclaimer.body")}</p>
        <button
          className="btn-primary mt-3 w-full"
          onClick={() => {
            localStorage.setItem(DISCLAIMER_KEY, "1");
            setDisclaimer(false);
          }}
        >
          {t("ui.disclaimer_accept")}
        </button>
      </Dialog>
    </div>
  );
}
