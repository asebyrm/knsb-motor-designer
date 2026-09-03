import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api } from "../api";

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="card p-3">
      <div className="text-xs text-text-secondary">{label}</div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  );
}

export function Admin() {
  const { t } = useTranslation();
  const stats = useQuery({
    queryKey: ["admin-stats"],
    queryFn: api.adminStats,
    refetchInterval: 30000,
  });
  const health = useQuery({
    queryKey: ["admin-health"],
    queryFn: api.adminHealth,
    refetchInterval: 30000,
  });
  const users = useQuery({ queryKey: ["admin-users"], queryFn: api.adminUsers });

  const s = (stats.data ?? {}) as Record<string, number | Record<string, number>>;
  const h = (health.data ?? {}) as Record<string, unknown>;
  const alert = Boolean(h.alert_banner);

  return (
    <div className="space-y-4 p-4">
      <h1 className="text-lg font-semibold">{t("admin.title")}</h1>
      {alert && (
        <div className="rounded bg-danger px-3 py-2 text-sm text-white">
          {t("admin.alert_disk")}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label={t("admin.active_users")} value={String(s.active_users_5m ?? 0)} />
        <Stat label={t("admin.total_users")} value={String(s.total_users ?? 0)} />
        <Stat label={t("admin.sims_today")} value={String(s.simulations_today ?? 0)} />
        <Stat label={t("admin.sims_week")} value={String(s.simulations_week ?? 0)} />
        <Stat label={t("admin.total_designs")} value={String(s.total_designs ?? 0)} />
        <Stat label={t("admin.public_designs")} value={String(s.public_designs ?? 0)} />
        <Stat
          label={t("admin.job_queue")}
          value={JSON.stringify(s.mission_jobs_memory ?? {})}
        />
        <Stat label={t("admin.exports_24h")} value={JSON.stringify(s.exports_24h ?? {})} />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="card p-3">
          <h2 className="mb-2 text-sm font-semibold">{t("admin.process")}</h2>
          <pre className="overflow-x-auto text-xs">{JSON.stringify(h.process ?? {}, null, 2)}</pre>
          <h2 className="mb-1 mt-3 text-sm font-semibold">{t("admin.pools")}</h2>
          <pre className="overflow-x-auto text-xs">{JSON.stringify(h.pools ?? {}, null, 2)}</pre>
          <h2 className="mb-1 mt-3 text-sm font-semibold">{t("admin.disk")}</h2>
          <pre className="overflow-x-auto text-xs">{JSON.stringify(h.disk ?? {}, null, 2)}</pre>
        </div>
        <div className="card p-3">
          <h2 className="mb-2 text-sm font-semibold">{t("admin.users")}</h2>
          <table className="w-full text-xs">
            <tbody>
              {(users.data ?? []).map((u) => (
                <tr key={String(u.id)} className="border-b border-border/60">
                  <td className="py-1">{String(u.username)}</td>
                  <td>{String(u.role)}</td>
                  <td>{u.is_active ? "active" : "suspended"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
