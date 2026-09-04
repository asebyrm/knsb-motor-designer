import type { DesignDoc, MissionResult, SimResult } from "./types";

const BASE = "/api";

let accessToken: string | null = null;
export function setToken(t: string | null) {
  accessToken = t;
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(opts.headers as Record<string, string>),
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const res = await fetch(BASE + path, { ...opts, headers, credentials: "include" });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, String(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export interface Catalog {
  schema_version: number;
  propellants: Array<{
    id: string; file: string; name_tr: string; name_en: string; composition: string;
    properties: Record<string, number>;
    burn_rate_ranges: Array<{ p_min_mpa: number; p_max_mpa: number; a: number; n: number }>;
  }>;
  grains: string[];
  case_materials: Array<{
    id: string; name_tr: string; name_en: string; notes_key: string;
    properties: Record<string, number>;
  }>;
  liner_materials: Array<{
    id: string; name_tr: string; name_en: string; notes_key: string;
    properties: Record<string, number>;
  }>;
  warning_codes: Array<{ code: string; level: string; i18n_key: string }>;
  all_warning_codes: string[];
  print_methods: string[];
}

export const api = {
  catalog: () => req<Catalog>("/catalog"),
  simulate: (design: DesignDoc, downsample = 500) =>
    req<SimResult>("/simulate", {
      method: "POST",
      body: JSON.stringify({ design, downsample }),
    }),
  startMission: (payload: Record<string, unknown>) =>
    req<{ job_id: string; status: string }>("/mission", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  job: (id: string) =>
    req<{ job_id: string; status: string; result: MissionResult | null; error: string }>(
      `/jobs/${id}`,
    ),
  exportUrl: BASE + "/export",
  async exportFile(design: DesignDoc, fmt: string, locale: string, acceptRisk: boolean) {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    const res = await fetch(BASE + "/export", {
      method: "POST",
      headers,
      credentials: "include",
      body: JSON.stringify({ design, fmt, locale, accept_risk: acceptRisk }),
    });
    if (!res.ok) throw new ApiError(res.status, (await res.json().catch(() => ({}))).detail ?? "");
    const blob = await res.blob();
    const cd = res.headers.get("content-disposition") ?? "";
    const name = /filename="?([^"]+)"?/.exec(cd)?.[1] ?? `motor.${fmt}`;
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    // must be attached to the document for the click to reliably start a
    // download in every browser; detach + revoke only after it has fired.
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
  register: (body: Record<string, unknown>) =>
    req<{ access_token: string; user: Record<string, unknown> }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  login: (body: Record<string, unknown>) =>
    req<{ access_token: string; user: Record<string, unknown> }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  logout: () => req<void>("/auth/logout", { method: "POST" }),
  me: () => req<Record<string, unknown>>("/auth/me"),
  myDesigns: () => req<Array<Record<string, unknown>>>("/designs"),
  saveDesign: (body: Record<string, unknown>) =>
    req<Record<string, unknown>>("/designs", { method: "POST", body: JSON.stringify(body) }),
  adminStats: () => req<Record<string, unknown>>("/admin/stats"),
  adminHealth: () => req<Record<string, unknown>>("/admin/health"),
  adminUsers: () => req<Array<Record<string, unknown>>>("/admin/users"),
  neutralLength: (od: number, d: number) =>
    req<{ segment_length: number }>(
      `/tools/neutral-length?outer_diameter=${od}&core_diameter=${d}`,
    ),
  optimumExpansion: (design: DesignDoc) =>
    req<{ expansion_ratio: number }>("/tools/optimum-expansion", {
      method: "POST",
      body: JSON.stringify(design),
    }),
};
