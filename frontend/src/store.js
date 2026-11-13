import { computed, reactive, ref } from "vue";
import { open } from "@tauri-apps/plugin-dialog";
import { Command } from "@tauri-apps/plugin-shell";
import { clearLog, getGroups, getConfig, getStatus, inspectTemplate, listTemplates, runImport, saveConfig, testConnection, waitForBackend, } from "./api";
// ---------- 后端状态 ----------
export const status = ref("正在启动桌面后端…");
export const backendError = ref("");
export const ready = computed(() => status.value === "后端已就绪");
let child = null;
const DS_KEY = "hdms.dataSources";
const DS_ACTIVE_KEY = "hdms.activeDataSource";
function blankDb() {
    return { host: "", port: 3306, user: "", password: "", database: "", tenant: "" };
}
function toDb(d) {
    return {
        host: d.host,
        port: d.port,
        user: d.user,
        password: d.password,
        database: d.database,
        tenant: d.tenant,
    };
}
function newDsId() {
    return "ds_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 6);
}
function loadDsList() {
    try {
        const arr = JSON.parse(localStorage.getItem(DS_KEY) || "[]");
        return Array.isArray(arr) ? arr : [];
    }
    catch {
        return [];
    }
}
export const dsList = ref(loadDsList());
export const activeDsId = ref(localStorage.getItem(DS_ACTIVE_KEY) || "");
function persistDs() {
    localStorage.setItem(DS_KEY, JSON.stringify(dsList.value));
    localStorage.setItem(DS_ACTIVE_KEY, activeDsId.value);
}
export const activeDs = computed(() => dsList.value.find((d) => d.id === activeDsId.value) ?? null);
/** 导入流程使用的连接配置 = 当前选中的数据源 */
export const db = computed(() => (activeDs.value ? toDb(activeDs.value) : blankDb()));
export const testing = ref(false);
export const testOk = ref(null);
export const testFail = ref("");
/** 测试「当前数据源」的连接 */
export async function testActive() {
    if (!activeDs.value) {
        testOk.value = null;
        testFail.value = "";
        return;
    }
    testing.value = true;
    testOk.value = null;
    testFail.value = "";
    try {
        const r = await testConnection({ ...db.value });
        if (r.ok)
            testOk.value = { version: r.version ?? "" };
        else
            testFail.value = r.error ?? "连接失败";
    }
    catch (e) {
        testFail.value = String(e);
    }
    finally {
        testing.value = false;
    }
}
export async function setActiveDs(id) {
    if (activeDsId.value === id)
        return;
    activeDsId.value = id;
    persistDs();
    // 切换后同步到后端并自动测试连接
    const ds = activeDs.value;
    if (ds)
        await saveConfig(toDb(ds)).catch(() => null);
    await testActive();
}
// ---------- 数据源配置弹窗（表单同原「数据库连接」面板） ----------
export const dsModal = reactive({ open: false, editingId: null });
export const dsForm = reactive({ id: "", name: "", ...blankDb() });
export const dsTesting = ref(false);
export const dsTestOk = ref("");
export const dsTestFail = ref("");
export function openCreateDs() {
    Object.assign(dsForm, { id: "", name: "", ...blankDb() });
    dsModal.editingId = null;
    dsTestOk.value = "";
    dsTestFail.value = "";
    dsModal.open = true;
}
export function openEditDs(ds) {
    Object.assign(dsForm, JSON.parse(JSON.stringify(ds)));
    dsModal.editingId = ds.id;
    dsTestOk.value = "";
    dsTestFail.value = "";
    dsModal.open = true;
}
/** 复制数据源：带入新建弹窗，稍作修改即可保存为新的数据源 */
export function openDuplicateDs(ds) {
    Object.assign(dsForm, JSON.parse(JSON.stringify(ds)), {
        id: "",
        name: (ds.name || "") + " 副本",
    });
    dsModal.editingId = null; // 作为「新建」保存，不影响原数据源
    dsTestOk.value = "";
    dsTestFail.value = "";
    dsModal.open = true;
}
export async function doDsTest() {
    dsTesting.value = true;
    dsTestOk.value = "";
    dsTestFail.value = "";
    try {
        const r = await testConnection(toDb(dsForm));
        if (r.ok)
            dsTestOk.value = r.version ?? "";
        else
            dsTestFail.value = r.error ?? "连接失败";
    }
    catch (e) {
        dsTestFail.value = String(e);
    }
    finally {
        dsTesting.value = false;
    }
}
export async function doDsSave() {
    const name = dsForm.name.trim() || dsForm.database || "未命名数据源";
    if (dsModal.editingId) {
        const ds = dsList.value.find((d) => d.id === dsModal.editingId);
        if (ds)
            Object.assign(ds, { ...toDb(dsForm), name });
        persistDs();
        // 编辑的是当前使用中的数据源 → 同步到后端
        if (ds && ds.id === activeDsId.value) {
            testOk.value = null;
            await saveConfig(toDb(ds)).catch(() => null);
            await testActive();
        }
    }
    else {
        const ds = { id: newDsId(), name, ...toDb(dsForm) };
        dsList.value.push(ds);
        activeDsId.value = ds.id; // 新建后设为当前使用
        persistDs();
        await saveConfig(toDb(ds)).catch(() => null);
        await testActive();
    }
    dsModal.open = false;
}
export async function deleteDs(ds) {
    const ok = await askConfirm("删除数据源", [`确定删除数据源「${ds.name}」吗？`, "仅删除本机保存的连接记录，不会改动数据库。"], true);
    if (!ok)
        return;
    dsList.value = dsList.value.filter((d) => d.id !== ds.id);
    if (activeDsId.value === ds.id) {
        activeDsId.value = dsList.value[0]?.id ?? "";
        if (activeDsId.value) {
            await saveConfig(toDb(dsList.value[0])).catch(() => null);
            await testActive();
        }
        else {
            testOk.value = null;
            testFail.value = "";
        }
    }
    persistDs();
}
// ---------- 模板 ----------
export const templates = ref([]);
export const inspecting = ref(false);
// ---------- 分组与选择 ----------
export const groups = ref([]);
// ---------- 任务（后端全局状态；单一后端同时只跑一个导入任务） ----------
const job = reactive({
    running: false,
    stage: "",
    logs: [],
    result: null,
    error: null,
    started: null,
    finished: null,
});
/** 是否有导入任务在运行（全局，用于禁用执行入口） */
export const isRunning = computed(() => job.running);
let pollTimer = null;
// ---------- 运行过程可视化（按会话隔离） ----------
export const tplError = ref("");
/** 正在运行（或最近一次运行）归属的会话 id：日志只写入该会话 */
let activeRunSessionId = null;
export async function clearConsole() {
    // 彻底清空：后端日志一起清掉，之后只显示新输出
    try {
        await clearLog();
    }
    catch {
        // 后端不可用时也先清本地显示
    }
    const s = sessions[activeTabId.value];
    if (s)
        s.logs = [];
}
export const totalRows = computed(() => sheets.value.reduce((s, x) => s + x.rows, 0));
export const selectedCount = computed(() => selected.value.size);
export const dbReady = computed(() => !!(db.value.host && db.value.user && db.value.database && testOk.value));
export const canRun = computed(() => dbReady.value && !!xlsxPath.value && selectedCount.value > 0 && !job.running);
export async function initBackend() {
    try {
        const command = Command.sidecar("binaries/python-backend", ["--port", "18765"]);
        command.stdout.on("data", (line) => console.info("[python]", line));
        command.stderr.on("data", (line) => console.error("[python]", line));
        child = await command.spawn();
        status.value = "Python 后端进程已启动，正在等待 API…";
        await waitForBackend();
        status.value = "后端已就绪";
        const [cfg, g, tpl, st] = await Promise.all([
            getConfig(),
            getGroups(),
            listTemplates(),
            getStatus(),
        ]);
        // 迁移：旧版本连接配置存在后端，首次使用数据源管理时转为「默认数据源」
        if (dsList.value.length === 0) {
            const ds = { id: newDsId(), name: "默认数据源", ...toDb(cfg ?? blankDb()) };
            dsList.value = [ds];
            activeDsId.value = ds.id;
            persistDs();
        }
        if (!activeDs.value) {
            activeDsId.value = dsList.value[0]?.id ?? "";
            persistDs();
        }
        await testActive();
        groups.value = g.groups;
        templates.value = tpl.templates;
        if (st.running) {
            // 上次任务还没跑完：恢复进度并继续轮询（日志归属第一个被打开的会话）
            Object.assign(job, st);
            startPolling();
        }
        else {
            // 每次启动都是全新控制台：清掉后端里上次会话的历史日志
            job.logs = [];
            if (st.result)
                job.result = st.result; // 只保留结果报告，控制台清空
            await clearLog().catch(() => null);
        }
    }
    catch (e) {
        backendError.value = String(e);
        status.value = "后端启动失败";
    }
}
export async function shutdownBackend() {
    stopPolling();
    try {
        await child?.kill();
    }
    catch (e) {
        console.warn("结束 Python sidecar 失败", e);
    }
}
// ---------- 模板 ----------
export async function doInspect() {
    if (!xlsxPath.value)
        return;
    inspecting.value = true;
    tplError.value = "";
    try {
        const r = await inspectTemplate(xlsxPath.value);
        sheets.value = r.sheets;
    }
    catch (e) {
        sheets.value = [];
        tplError.value = String(e);
    }
    finally {
        inspecting.value = false;
    }
}
export function pickTemplate(t) {
    xlsxPath.value = t.path;
    doInspect();
}
/** 通过系统文件选择弹窗选择模板文件（点击拖拽区触发） */
export async function browseTemplate() {
    try {
        const p = await open({
            multiple: false,
            directory: false,
            title: "选择导入模板（Excel）",
            filters: [{ name: "Excel 模板", extensions: ["xlsx", "xlsm", "xls"] }],
        });
        if (typeof p === "string" && p)
            setTemplatePath(p);
    }
    catch (e) {
        tplError.value = String(e);
    }
}
/** 设置模板路径并自动解析（拖拽 / 弹窗选择 / 手动粘贴共用） */
export function setTemplatePath(path) {
    if (!path)
        return;
    xlsxPath.value = path;
    tplError.value = "";
    doInspect();
}
const sessions = reactive({});
function newSession(dsId) {
    return {
        id: "sess_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 6),
        dsId,
        xlsxPath: "",
        sheets: [],
        selected: new Set(),
        step: 1,
        running: false,
        stage: "",
        logs: [],
        result: null,
        error: null,
        runStarted: false,
        runTotal: 0,
        lastRunSheets: [],
        runError: "",
    };
}
function ensureSession(id) {
    let s = sessions[id];
    if (!s) {
        s = newSession("");
        sessions[id] = s;
    }
    return s;
}
export const openTabIds = ref([]);
export const activeTabId = ref("");
// 以下导出自动绑定「当前激活 tab」的会话，组件无需感知 tab 切换
export const xlsxPath = computed({
    get: () => (sessions[activeTabId.value] ?? newSession("")).xlsxPath,
    set: (v) => { ensureSession(activeTabId.value).xlsxPath = v; },
});
export const sheets = computed({
    get: () => (sessions[activeTabId.value] ?? newSession("")).sheets,
    set: (v) => { ensureSession(activeTabId.value).sheets = v; },
});
export const selected = computed({
    get: () => (sessions[activeTabId.value] ?? newSession("")).selected,
    set: (v) => { ensureSession(activeTabId.value).selected = v; },
});
export const step = computed({
    get: () => (sessions[activeTabId.value] ?? newSession("")).step,
    set: (v) => { ensureSession(activeTabId.value).step = v; },
});
/** 当前激活会话所属的数据源 */
export const activeTabSession = computed(() => sessions[activeTabId.value] ?? null);
/** 某数据源是否已打开会话（用于侧栏标记） */
export function isTabOpen(dsId) {
    return openTabIds.value.some((tid) => sessions[tid]?.dsId === dsId);
}
// ---------- 会话级运行视图（日志/进度/结果按会话隔离） ----------
export const sLogs = computed(() => sessions[activeTabId.value]?.logs ?? []);
export const sStage = computed(() => sessions[activeTabId.value]?.stage ?? "");
export const sRunStarted = computed(() => sessions[activeTabId.value]?.runStarted ?? false);
export const sRunTotal = computed(() => sessions[activeTabId.value]?.runTotal ?? 0);
export const sRunError = computed(() => sessions[activeTabId.value]?.runError ?? "");
export const sResult = computed(() => sessions[activeTabId.value]?.result ?? null);
export const sError = computed(() => sessions[activeTabId.value]?.error ?? null);
export const sRunning = computed(() => sessions[activeTabId.value]?.running ?? false);
/** 从日志行统计已完成的项（每张表完成时引擎输出 ✓/✗ 行）。 */
function doneFromLogs(logs) {
    const names = new Set();
    for (const line of logs) {
        const m = line.match(/[✓✗]\s*(.+?)(（|$)/);
        if (m)
            names.add(m[1].trim());
    }
    return names;
}
export const sDoneSheets = computed(() => doneFromLogs(sLogs.value).size);
export const sProgressPct = computed(() => sRunTotal.value ? Math.min(100, Math.round((sDoneSheets.value / sRunTotal.value) * 100)) : 0);
export const sCurrentSheet = computed(() => {
    const s = sessions[activeTabId.value];
    if (!s?.running)
        return "";
    const done = doneFromLogs(s.logs);
    return s.lastRunSheets.find((n) => !done.has(n)) ?? "";
});
/** tab 标题：数据源名；同一数据源多个会话时带序号 */
export const tabTitles = computed(() => {
    const total = new Map();
    for (const tid of openTabIds.value) {
        const s = sessions[tid];
        if (s)
            total.set(s.dsId, (total.get(s.dsId) ?? 0) + 1);
    }
    const seen = new Map();
    const map = {};
    for (const tid of openTabIds.value) {
        const s = sessions[tid];
        if (!s)
            continue;
        const base = dsList.value.find((d) => d.id === s.dsId)?.name ?? s.dsId;
        const n = (seen.get(s.dsId) ?? 0) + 1;
        seen.set(s.dsId, n);
        map[tid] = (total.get(s.dsId) ?? 1) > 1 ? `${base} · 会话${n}` : base;
    }
    return map;
});
/** 双击侧栏数据源：总是新开一个会话 tab */
export function openDsTab(ds) {
    const s = newSession(ds.id);
    sessions[s.id] = s;
    openTabIds.value.push(s.id);
    activeTabId.value = s.id;
    // 同步激活对应数据源（沿用侧栏的单选逻辑）
    if (activeDsId.value !== ds.id)
        setActiveDs(ds.id);
    // 导入项默认全选；模板不自动带入历史记录，保持空白由用户自行选择
    if (s.selected.size === 0 && groups.value.length) {
        s.selected = new Set(groups.value.flatMap((g) => g.sheets));
    }
    // 启动恢复的未完任务还没有归属者：归到这个新开的会话
    if (job.running && !activeRunSessionId)
        activeRunSessionId = s.id;
}
/** 切换 tab：同步激活其所属数据源 */
export function setActiveTab(id) {
    const s = sessions[id];
    if (!s)
        return;
    activeTabId.value = id;
    if (activeDsId.value !== s.dsId)
        setActiveDs(s.dsId);
}
/** 激活某数据源的第一个已打开会话（侧栏单击时用），返回是否存在 */
export function activateDsFirstSession(dsId) {
    const id = openTabIds.value.find((tid) => sessions[tid]?.dsId === dsId);
    if (!id)
        return false;
    setActiveTab(id);
    return true;
}
export function closeDsTab(id) {
    const idx = openTabIds.value.indexOf(id);
    if (idx >= 0)
        openTabIds.value.splice(idx, 1);
    delete sessions[id];
    if (activeTabId.value === id) {
        const nextId = openTabIds.value[Math.min(idx, openTabIds.value.length - 1)] ?? "";
        if (nextId)
            setActiveTab(nextId);
        else
            activeTabId.value = "";
    }
}
// ---------- 向导步骤（数据源沿用左侧选中的，不单独成步） ----------
export function isStepDone(n) {
    if (n === 1)
        return !!xlsxPath.value && sheets.value.length > 0;
    if (n === 2)
        return selectedCount.value > 0;
    return false;
}
/** 是否允许跳转到第 n 步（其前面的步骤必须全部完成） */
export function canGoto(n) {
    for (let i = 1; i < n; i++)
        if (!isStepDone(i))
            return false;
    return true;
}
export function goToStep(n) {
    if (n >= 1 && n <= 3 && canGoto(n))
        step.value = n;
}
export function nextStep() {
    goToStep(step.value + 1);
}
export function prevStep() {
    goToStep(step.value - 1);
}
// ---------- 选择 ----------
export function toggleSheet(name) {
    const next = new Set(selected.value);
    if (next.has(name))
        next.delete(name);
    else
        next.add(name);
    selected.value = next;
}
export function toggleGroup(g) {
    const next = new Set(selected.value);
    const allIn = g.sheets.every((s) => next.has(s));
    for (const s of g.sheets) {
        if (allIn)
            next.delete(s);
        else
            next.add(s);
    }
    selected.value = next;
}
export function selectAll() {
    selected.value = new Set(groups.value.flatMap((g) => g.sheets));
}
export function clearAll() {
    selected.value = new Set();
}
export function groupChecked(g) {
    return g.sheets.every((s) => selected.value.has(s));
}
export function groupPartial(g) {
    const some = g.sheets.some((s) => selected.value.has(s));
    return some && !groupChecked(g);
}
export function sheetRows(name) {
    const s = sheets.value.find((x) => x.name === name);
    return s ? s.rows : null;
}
// ---------- 导入 ----------
function startPolling() {
    stopPolling();
    pollTimer = window.setInterval(async () => {
        try {
            const st = await getStatus();
            Object.assign(job, st);
            // 日志/进度/结果只归属发起该次运行的会话
            const owner = activeRunSessionId ? sessions[activeRunSessionId] : null;
            if (owner) {
                owner.logs = st.logs ?? [];
                owner.running = st.running;
                owner.stage = st.stage ?? "";
                if (!st.running) {
                    owner.result = st.result;
                    owner.error = st.error;
                }
            }
            if (!st.running) {
                stopPolling();
                activeRunSessionId = null;
            }
        }
        catch {
            // 轮询失败暂不处理
        }
    }, 600);
}
function stopPolling() {
    if (pollTimer !== null) {
        window.clearInterval(pollTimer);
        pollTimer = null;
    }
}
// ---------- 应用内确认弹窗（Tauri WebView 不支持原生 confirm/alert） ----------
export const confirmBox = reactive({ open: false, title: "", message: [], danger: false, resolve: null });
export function askConfirm(title, message, danger = false) {
    return new Promise((resolve) => {
        confirmBox.open = true;
        confirmBox.title = title;
        confirmBox.message = message;
        confirmBox.danger = danger;
        confirmBox.resolve = resolve;
    });
}
export function answerConfirm(v) {
    confirmBox.open = false;
    confirmBox.resolve?.(v);
    confirmBox.resolve = null;
}
export async function doRun(execute, all) {
    const sheetsToRun = all ? groups.value.flatMap((g) => g.sheets) : [...selected.value];
    if (sheetsToRun.length === 0)
        return;
    const label = execute ? "正式导入" : "演练导入";
    const scope = all ? "全部 20 项数据" : `选中的 ${sheetsToRun.length} 项`;
    const modeTip = execute
        ? "将直接写入数据库并提交事务（重复数据自动跳过，不会重复插入）。"
        : "演练模式：执行全部 SQL 后回滚，不落库，用于先验证数据。";
    const ok = await askConfirm(`${label} · ${scope}`, [
        `目标库：${db.value.database} @ ${db.value.host}:${db.value.port}`,
        `租户：${db.value.tenant || "（未填，用默认）"}`,
        "",
        modeTip,
    ], execute);
    if (!ok)
        return;
    // 本次运行归属当前会话：日志、进度、结果都只写入该会话
    const session = ensureSession(activeTabId.value);
    activeRunSessionId = session.id;
    session.runError = "";
    session.runStarted = true;
    session.runTotal = sheetsToRun.length;
    session.lastRunSheets = sheetsToRun;
    session.logs = [];
    session.result = null;
    session.error = null;
    // 乐观置为执行中，界面立刻有反馈；随后轮询会接管真实状态
    session.running = true;
    session.stage = "启动任务";
    startPolling();
    try {
        await runImport({
            db: { ...db.value },
            xlsx_path: xlsxPath.value,
            sheets: sheetsToRun,
            execute,
        });
    }
    catch (e) {
        session.runError = String(e);
        stopPolling();
        const st = await getStatus().catch(() => null);
        if (st) {
            Object.assign(job, st);
            session.logs = st.logs ?? [];
            session.running = st.running;
            session.stage = st.stage ?? "";
            session.result = st.result;
            session.error = st.error;
        }
    }
}
