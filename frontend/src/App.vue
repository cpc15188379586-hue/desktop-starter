<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { activeTabId, closeDsTab, initBackend, openTabIds, setActiveTab, shutdownBackend, tabTitles } from "./store";
import SidebarDataSources from "./components/SidebarDataSources.vue";
import MainPanels from "./components/MainPanels.vue";
import ConsolePanel from "./components/ConsolePanel.vue";
import DataSourceModal from "./components/DataSourceModal.vue";
import ConfirmModal from "./components/ConfirmModal.vue";

// ---------- 面板拖拽（侧栏宽度 / 控制台高度，记忆到本地） ----------
const sidebarWidth = ref(Number(localStorage.getItem("hdms.sidebarWidth")) || 210);
const consoleHeight = ref(Number(localStorage.getItem("hdms.consoleHeight")) || 280);
let drag: { type: "sidebar" | "console"; x: number; y: number; w: number; h: number } | null = null;

function clamp(v: number, lo: number, hi: number) {
  return Math.max(lo, Math.min(hi, v));
}

function startDrag(type: "sidebar" | "console", e: MouseEvent) {
  e.preventDefault();
  drag = { type, x: e.clientX, y: e.clientY, w: sidebarWidth.value, h: consoleHeight.value };
  document.body.style.userSelect = "none";
  window.addEventListener("mousemove", onDrag);
  window.addEventListener("mouseup", endDrag);
}

function onDrag(e: MouseEvent) {
  if (!drag) return;
  if (drag.type === "sidebar") {
    sidebarWidth.value = clamp(drag.w + (e.clientX - drag.x), 160, 360);
  } else {
    consoleHeight.value = clamp(drag.h + (drag.y - e.clientY), 120, window.innerHeight - 280);
  }
}

function endDrag() {
  drag = null;
  document.body.style.userSelect = "";
  window.removeEventListener("mousemove", onDrag);
  window.removeEventListener("mouseup", endDrag);
  localStorage.setItem("hdms.sidebarWidth", String(sidebarWidth.value));
  localStorage.setItem("hdms.consoleHeight", String(consoleHeight.value));
}

// ---------- 工作台标签页 ----------

onMounted(() => {
  initBackend();
});

onBeforeUnmount(() => {
  endDrag();
  shutdownBackend();
});
</script>

<template>
  <div class="app">
    <!-- 左侧：数据源管理菜单 -->
    <SidebarDataSources :width="sidebarWidth" />
    <div class="resizer sidebar-resizer" title="拖拽调整菜单宽度" @mousedown="startDrag('sidebar', $event)"></div>

    <!-- 右侧：工作台 tabBar + 每个数据源一套（向导 + 控制台） -->
    <div class="right">
      <!-- 顶部 tabBar：双击左侧数据源新开会话（同一数据源可开多个），可切换 / 关闭 -->
      <div v-if="openTabIds.length" class="tabbar">
        <div
          v-for="id in openTabIds"
          :key="id"
          class="tab"
          :class="{ active: id === activeTabId }"
          :title="tabTitles[id] || id"
          @click="setActiveTab(id)"
        >
          <span class="tab-label">{{ tabTitles[id] || id }}</span>
          <span class="tab-close" title="关闭此会话" @click.stop="closeDsTab(id)">×</span>
        </div>
      </div>

      <!-- 尚未打开任何会话 -->
      <div v-if="!openTabIds.length" class="tab-empty">
        <div class="tab-empty-icon">⛁</div>
        <p>在左侧<b>双击</b>某个数据源，打开一个导入会话</p>
        <p class="muted">同一数据源可以开多个会话，每个会话独立：导入向导 + 运行日志。</p>
      </div>

      <!-- 每个 tab：上方向导内容 + 下方配套的输出控制台（v-show 保留各自状态与滚动位置） -->
      <template v-else>
        <div
          v-for="id in openTabIds"
          :key="id"
          v-show="id === activeTabId"
          class="tab-page"
        >
          <div class="main-scroll">
            <MainPanels />
          </div>

          <!-- 拖拽手柄：调整该 tab 控制台高度 -->
          <div class="resizer console-resizer" title="拖拽调整日志区高度" @mousedown="startDrag('console', $event)"></div>

          <!-- 该 tab 的输出控制台 -->
          <ConsolePanel :height="consoleHeight" />
        </div>
      </template>
    </div>

    <!-- 弹窗 -->
    <DataSourceModal />
    <ConfirmModal />
  </div>
</template>
