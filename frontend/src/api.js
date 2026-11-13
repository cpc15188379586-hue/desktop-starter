const API_BASE = "http://127.0.0.1:18765";
async function request(path, init) {
    const response = await fetch(`${API_BASE}${path}`, init);
    if (!response.ok) {
        const detail = await response.json().catch(() => null);
        throw new Error(detail?.detail ?? `API 请求失败：${response.status}`);
    }
    return response.json();
}
export async function waitForBackend(timeoutMs = 15000) {
    const startedAt = Date.now();
    while (Date.now() - startedAt < timeoutMs) {
        try {
            await request("/api/health");
            return;
        }
        catch {
            // Backend is still starting.
        }
        await new Promise((resolve) => setTimeout(resolve, 250));
    }
    throw new Error("Python 后端启动超时，请检查 sidecar 是否正确构建。");
}
export function getConfig() {
    return request("/api/importer/config");
}
export function saveConfig(cfg) {
    return request("/api/importer/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cfg),
    });
}
export function testConnection(cfg) {
    return request("/api/importer/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cfg),
    });
}
export function getGroups() {
    return request("/api/importer/groups");
}
export function listTemplates() {
    return request("/api/importer/templates");
}
export function inspectTemplate(xlsxPath) {
    return request("/api/importer/inspect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ xlsx_path: xlsxPath }),
    });
}
export function runImport(body) {
    return request("/api/importer/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}
export function getStatus() {
    return request("/api/importer/status");
}
export function clearLog() {
    return request("/api/importer/clear-log", { method: "POST" });
}
