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

      <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-border bg-surface px-3 py-2 text-xs text-text-secondary">
        <span className="flex items-center gap-1.5">
          <Logo size={22} variant="mark" /> KNSB Motor Designer
        </span>
        <span className="flex items-center gap-3">
          <a
            href="https://www.parsroket.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-text"
          >
            by PARS Rocketry Team
          </a>
          <a
            href="https://github.com/asebyrm/knsb-motor-designer"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 hover:text-text"
            aria-label="GitHub"
          >
            <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden>
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
            </svg>
            GitHub
          </a>
        </span>
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
