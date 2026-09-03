import { useState } from "react";
import { useTranslation } from "react-i18next";

import { api } from "../api";
import { useStore } from "../store";
import { Dialog } from "./ui";

export function AuthDialog({
  open,
  onClose,
  reason,
}: {
  open: boolean;
  onClose: () => void;
  reason?: string;
}) {
  const { t } = useTranslation();
  const { setUser, design } = useStore();
  const [tab, setTab] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", username: "", password: "", ident: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setBusy(true);
    setErr("");
    try {
      const res =
        tab === "login"
          ? await api.login({ email_or_username: form.ident, password: form.password })
          : await api.register({
              email: form.email,
              username: form.username,
              password: form.password,
              locale: document.documentElement.lang || "en",
            });
      setUser(res.user, res.access_token);
      // carry the anonymous localStorage design onto the account
      try {
        await api.saveDesign({ name: design.name, config_json: design, visibility: "private" });
      } catch {
        /* non-fatal */
      }
      onClose();
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title={t(`ui.${tab}`)}>
      {reason && <p className="mb-2 text-xs text-text-secondary">{reason}</p>}
      <div className="space-y-2">
        {tab === "register" && (
          <>
            <input
              className="input"
              placeholder={t("auth.email")}
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
            />
            <input
              className="input"
              placeholder={t("auth.username")}
              value={form.username}
              onChange={(e) => setForm({ ...form, username: e.target.value })}
            />
          </>
        )}
        {tab === "login" && (
          <input
            className="input"
            placeholder={t("auth.email_or_username")}
            value={form.ident}
            onChange={(e) => setForm({ ...form, ident: e.target.value })}
          />
        )}
        <input
          className="input"
          type="password"
          placeholder={t("auth.password")}
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
        <p className="text-[11px] text-text-secondary">{t("auth.password_hint")}</p>
        {err && <p className="text-xs text-danger">{err}</p>}
        <button className="btn-primary w-full" disabled={busy} onClick={submit}>
          {t(`ui.${tab}`)}
        </button>
        <button
          className="w-full text-xs text-primary"
          onClick={() => setTab(tab === "login" ? "register" : "login")}
        >
          {tab === "login" ? t("auth.need_account") : t("auth.have_account")}
        </button>
      </div>
    </Dialog>
  );
}
