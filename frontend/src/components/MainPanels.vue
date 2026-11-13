<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import {
  activeDs,
  backendError,
  browseTemplate,
  canRun,
  clearAll,
  dbReady,
  doInspect,
  doRun,
  goToStep,
  groupChecked,
  groupPartial,
  groups,
  inspecting,
  isRunning,
  isStepDone,
  nextStep,
  pickTemplate,
  prevStep,
  sCurrentSheet,
  sDoneSheets,
  sError,
  sProgressPct,
  sRunning,
  sStage,
  sResult,
  sRunError,
  sRunStarted,
  sRunTotal,
  selectAll,
  selected,
  selectedCount,
  setTemplatePath,
  sheetRows,
  sheets,
  step,
  templates,
  testFail,
  toggleGroup,
  toggleSheet,
  totalRows,
  tplError,
  xlsxPath,
} from "../store";

const stepDefs = [
  { n: 1, name: "导入模板" },
  { n: 2, name: "选择导入内容" },
  { n: 3, name: "执行导入" },
];

// ---------- 模板拖拽（Tauri WebView 的 drop 事件不含路径，走 webview 拖放事件） ----------
const dropZone = ref<HTMLElement | null>(null);
const dropHover = ref(false);
let unlistenDrop: (() => void) | null = null;

function isOverZone(pos: { x: number; y: number }): boolean {
  const el = dropZone.value;
  if (!el) return false;
  const r = el.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  const x = pos.x / scale;
  const y = pos.y / scale;
  return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
}

onMounted(async () => {
  try {
    unlistenDrop = await getCurrentWebview().onDragDropEvent((event) => {
      if (event.payload.type === "enter" || event.payload.type === "over") {
        dropHover.value = isOverZone(event.payload.position);
      } else if (event.payload.type === "drop") {
        const hit = isOverZone(event.payload.position);
        dropHover.value = false;
        if (hit) {
          const p = event.payload.paths[0];
          if (p) setTemplatePath(p);
        }
      } else {
        dropHover.value = false;
      }
    });
  } catch (e) {
    console.warn("注册拖放监听失败", e);
  }
});
onBeforeUnmount(() => unlistenDrop?.());
</script>

<template>
  <div class="main-panels">
    <p v-if="backendError" class="error backend-error">
      {{ backendError }}
      <span v-if="backendError.includes('Not Found')" class="hint" style="display:block">
        未找到 Python 后端程序（sidecar）。请在 backend 目录执行 `python build.py` 重新构建，
        并把 dist/python-backend 复制为 src-tauri/binaries/python-backend-&lt;当前平台标识&gt; 后重启应用。
      </span>
    </p>

    <!-- ========== 步骤条 ========== -->
    <section class="panel wizard-panel">
      <ol class="stepper">
        <li
          v-for="s in stepDefs"
          :key="s.n"
          class="step-item"
          :class="{ current: step === s.n, done: isStepDone(s.n), reachable: step > s.n || isStepDone(s.n) }"
          @click="goToStep(s.n)"
        >
          <span class="step-dot">
            <template v-if="isStepDone(s.n) && step !== s.n">✓</template>
            <template v-else>{{ s.n }}</template>
          </span>
          <span class="step-title">{{ s.name }}</span>
        </li>
      </ol>

      <!-- ========== 步骤 1：导入模板 ========== -->
      <div v-show="step === 1" class="step-body">
        <div class="panel-head">
          <h2>① 导入模板（Excel）</h2>
          <button class="ghost" :disabled="inspecting || !xlsxPath" @click="doInspect">
            {{ inspecting ? "解析中…" : sheets.length ? "重新解析" : "解析模板" }}
          </button>
        </div>
        <p class="hint muted" style="margin-top:0">
          当前数据源：<b>{{ activeDs?.name || "未选择" }}</b>（沿用左侧菜单选中的数据源，可随时在左侧切换）。
        </p>

        <!-- 拖拽区：支持拖拽 Excel 文件，点击弹窗选择文件 -->
        <div
          ref="dropZone"
          class="dropzone"
          :class="{ hover: dropHover, active: !!xlsxPath }"
          @click="browseTemplate"
        >
          <div class="drop-icon">⇪</div>
          <div class="drop-text">
            <template v-if="dropHover">松开鼠标，选择此文件</template>
            <template v-else>将 Excel 模板拖拽到此处，或 <b>点击选择文件</b></template>
          </div>
          <div v-if="xlsxPath" class="drop-file">{{ xlsxPath }}</div>
          <div v-else class="drop-hint muted">支持 .xlsx / .xlsm / .xls，如《基础数据准备-导入模板-日期.xlsx》</div>
        </div>

        <div v-if="templates.length" class="tpl-list">
          <button
            v-for="t in templates"
            :key="t.path"
            class="tpl"
            :class="{ active: t.path === xlsxPath }"
            @click="pickTemplate(t)"
          >
            <span class="tpl-name">{{ t.name }}</span>
            <span class="muted">{{ t.mtime }}</span>
          </button>
        </div>
        <p v-if="tplError" class="error">{{ tplError }}</p>
        <p v-if="sheets.length" class="hint muted">
          已解析 {{ sheets.length }} 个工作表，共 {{ totalRows }} 行数据。
        </p>
      </div>

      <!-- ========== 步骤 2：选择导入内容 ========== -->
      <div v-show="step === 2" class="step-body">
        <div class="panel-head">
          <h2>② 选择导入内容</h2>
          <div class="panel-actions">
            <button class="ghost" :disabled="sRunning" @click="selectAll">全选</button>
            <button class="ghost" :disabled="sRunning" @click="clearAll">清空</button>
          </div>
        </div>
        <div class="group-wrap">
          <div v-for="g in groups" :key="g.id" class="group">
            <label class="group-title" @click.prevent="toggleGroup(g)">
              <span class="checkbox" :class="{ on: groupChecked(g), half: groupPartial(g) }"></span>
              {{ g.name }}
            </label>
            <div class="sheet-list">
              <label
                v-for="s in g.sheets"
                :key="s"
                class="sheet"
                :class="{ off: sRunning }"
                @click.prevent="toggleSheet(s)"
              >
                <span class="checkbox" :class="{ on: selected.has(s) }"></span>
                {{ s }}
                <small v-if="sheetRows(s) !== null" class="muted">{{ sheetRows(s) }} 行</small>
              </label>
            </div>
          </div>
        </div>
        <p class="hint muted">
          已选 {{ selectedCount }} 项。各表之间有先后依赖（字典 → 治疗室/区域 → 床位 → 透析机 → 患者 → 方案/排班），
          不确定时建议直接「一键导入全部」。所有表均自动判重，重复导入不会产生脏数据。
        </p>
      </div>

      <!-- ========== 步骤 3：执行导入 ========== -->
      <div v-show="step === 3" class="step-body">
        <div class="panel-head">
          <h2>③ 执行导入</h2>
          <span v-if="sRunning" class="badge running">{{ sStage }}…</span>
          <span v-else-if="sResult" class="badge" :class="sResult.ok ? 'ok' : 'fail'">
            {{ sResult.ok ? "成功" : "有失败项" }}
          </span>
        </div>
        <div class="actions">
          <button class="primary" :disabled="!canRun"
                  :title="isRunning && !sRunning ? '其他会话正在导入，请等待其完成' : ''" @click="doRun(false, false)">
            {{ sRunning ? "导入中…" : "演练导入选中（不落库）" }}
          </button>
          <button class="primary" :disabled="!canRun"
                  :title="isRunning && !sRunning ? '其他会话正在导入，请等待其完成' : ''" @click="doRun(true, false)">
            {{ sRunning ? "导入中…" : "正式导入选中" }}
          </button>
          <button class="accent" :disabled="!dbReady || !xlsxPath || isRunning"
                  :title="isRunning && !sRunning ? '其他会话正在导入，请等待其完成' : ''" @click="doRun(true, true)">
            {{ sRunning ? "导入中…" : "一键导入全部" }}
          </button>
        </div>

        <!-- 执行进度（本会话自己的） -->
        <div v-if="sRunStarted" class="run-live">
          <div class="progress-row">
            <div class="pbar">
              <div class="pfill" :class="{ indet: sRunning && sProgressPct === 0 }"
                   :style="{ width: (sRunning && sProgressPct === 0 ? 100 : sProgressPct) + '%' }"></div>
            </div>
            <span class="progress-text">
              <template v-if="sRunning">
                {{ sProgressPct ? `${sDoneSheets}/${sRunTotal}` : "准备中" }}
                <b v-if="sCurrentSheet">· 正在导入：{{ sCurrentSheet }}</b>
                <b v-else-if="!sProgressPct">· {{ sStage }}</b>
              </template>
              <template v-else>完成 {{ sDoneSheets }}/{{ sRunTotal }}，详见下方运行日志</template>
            </span>
          </div>
        </div>
        <p v-if="sRunError" class="error">{{ sRunError }}</p>
        <p v-if="sError" class="error">{{ sError }}</p>

        <!-- 结果报告（本会话自己的） -->
        <div v-if="sResult" class="report">
          <table>
            <thead>
              <tr><th>数据表</th><th>新增</th><th>跳过</th><th>警告</th><th>错误</th></tr>
            </thead>
            <tbody>
              <tr v-for="it in sResult.items" :key="it.name">
                <td>{{ it.name }}</td>
                <td>{{ it.added }}</td>
                <td>{{ it.skipped }}</td>
                <td :class="{ warn: it.warns.length }">{{ it.warns.length }}</td>
                <td :class="{ bad: it.errors.length }">{{ it.errors.length }}</td>
              </tr>
              <tr class="total-row">
                <td>合计</td>
                <td>{{ sResult.totals.added }}</td>
                <td>{{ sResult.totals.skipped }}</td>
                <td>{{ sResult.totals.warnings }}</td>
                <td>{{ sResult.totals.errors }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="sResult.totals.warnings" class="detail">
            <h3>警告明细</h3>
            <p v-for="(w, i) in sResult.items.flatMap((x) => x.warns)" :key="'w' + i">{{ w }}</p>
          </div>
          <div v-if="sResult.totals.errors" class="detail">
            <h3>错误明细</h3>
            <p v-for="(e, i) in sResult.items.flatMap((x) => x.errors)" :key="'e' + i" class="error">{{ e }}</p>
          </div>
          <p class="hint muted">
            {{ sResult.committed
              ? "本次导入已提交写库；重复执行会自动跳过已存在数据。"
              : "本次为演练或失败回滚，数据库未改动。" }}
          </p>
        </div>
      </div>

      <!-- ========== 上一步 / 下一步 ========== -->
      <div class="wizard-nav">
        <button v-if="step > 1" class="ghost" @click="prevStep">上一步</button>
        <span class="wizard-spacer"></span>
        <button v-if="step < 3" class="primary" :disabled="!isStepDone(step)" @click="nextStep">
          下一步：{{ stepDefs[step].name }}
        </button>
      </div>
    </section>
  </div>
</template>
