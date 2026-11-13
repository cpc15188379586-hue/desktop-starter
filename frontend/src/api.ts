const API_BASE = "http://127.0.0.1:18765";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `API 请求失败：${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function waitForBackend(timeoutMs = 15_000) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    try {
      await request<{ status: string }>("/api/health");
      return;
    } catch {
      // Backend is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  throw new Error("Python 后端启动超时，请检查 sidecar 是否正确构建。");
}

// ---------- 基础数据导入 ----------

export interface DBConfig {
  host: string;
  port: number;
  user: string;
  password: string;
  database: string;
  tenant: string;
}

export interface SheetGroup {
  id: string;
  name: string;
  sheets: string[];
}

export interface TemplateFile {
  name: string;
  path: string;
  mtime: string;
}

export interface SheetInfo {
  name: string;
  rows: number;
  table: string;
  in_order: boolean;
  implemented: boolean;
}

export interface ReportItem {
  name: string;
  added: number;
  skipped: number;
  warns: string[];
  errors: string[];
}

export interface ImportResult {
  ok: boolean;
  committed: boolean;
  items: ReportItem[];
  totals: { added: number; skipped: number; warnings: number; errors: number };
}

export interface JobStatus {
  running: boolean;
  stage: string;
  logs: string[];
  result: ImportResult | null;
  error: string | null;
  started: string | null;
  finished: string | null;
}

export function getConfig() {
  return request<DBConfig>("/api/importer/config");
}

export function saveConfig(cfg: DBConfig) {
  return request<{ ok: boolean }>("/api/importer/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
}

export function testConnection(cfg: DBConfig) {
  return request<{ ok: boolean; version?: string; error?: string }>("/api/importer/test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
}

export function getGroups() {
  return request<{ groups: SheetGroup[]; order: string[] }>("/api/importer/groups");
}

export function listTemplates() {
  return request<{ templates: TemplateFile[] }>("/api/importer/templates");
}

export function inspectTemplate(xlsxPath: string) {
  return request<{ sheets: SheetInfo[]; order: string[] }>("/api/importer/inspect", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ xlsx_path: xlsxPath }),
  });
}

export function runImport(body: {
  db: DBConfig;
  xlsx_path: string;
  sheets: string[];
  execute: boolean;
}) {
  return request<{ ok: boolean; message: string }>("/api/importer/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getStatus() {
  return request<JobStatus>("/api/importer/status");
}

export function clearLog() {
  return request<{ ok: boolean }>("/api/importer/clear-log", { method: "POST" });
}
