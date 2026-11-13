<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import {
  activeDsId,
  activateDsFirstSession,
  dsList,
  deleteDs,
  isTabOpen,
  openCreateDs,
  openDsTab,
  openDuplicateDs,
  openEditDs,
  ready,
  setActiveDs,
  status,
  testFail,
  testOk,
  testing,
  type DataSource,
} from "../store";

import logoUrl from "../images/logo-DuWjEJcK.png";

defineProps<{ width: number }>();

// 单击：选中（已打开会话则切到第一个会话）；双击：新开一个会话（同一数据源可开多个）
function onClickDs(d: DataSource) {
  if (!activateDsFirstSession(d.id)) setActiveDs(d.id);
}
function onDblClickDs(d: DataSource) {
  openDsTab(d);
}

// ---------- 侧栏右键菜单 ----------
const ctxMenu = reactive({ open: false, x: 0, y: 0, target: null as DataSource | null });
const ctxEl = ref<HTMLElement | null>(null);
let suppressCtx = false;

function openCtxMenu(e: MouseEvent, target: DataSource | null) {
  ctxMenu.open = true;
  ctxMenu.target = target;
  ctxMenu.x = e.clientX;
  ctxMenu.y = e.clientY;
  nextTick(() => {
    const el = ctxEl.value;
    if (!el) return;
    const r = el.getBoundingClientRect();
    ctxMenu.x = Math.min(ctxMenu.x, window.innerWidth - r.width - 8);
    ctxMenu.y = Math.min(ctxMenu.y, window.innerHeight - r.height - 8);
  });
  // 本次触发事件已消费，避免全局 contextmenu 监听立即关闭菜单
  suppressCtx = true;
  setTimeout(() => (suppressCtx = false), 0);
}

function closeCtxMenu() {
  ctxMenu.open = false;
  ctxMenu.target = null;
}

function onGlobalCtxMenu() {
  if (suppressCtx) {
    suppressCtx = false;
    return;
  }
  closeCtxMenu();
}

function ctxCreate() {
  closeCtxMenu();
  openCreateDs();
}

function ctxEdit() {
  const ds = ctxMenu.target;
  closeCtxMenu();
  if (ds) openEditDs(ds);
}

function ctxDuplicate() {
  const ds = ctxMenu.target;
  closeCtxMenu();
  if (ds) openDuplicateDs(ds);
}

function ctxDelete() {
  const ds = ctxMenu.target;
  closeCtxMenu();
  if (ds) deleteDs(ds);
}

onMounted(() => {
  window.addEventListener("contextmenu", onGlobalCtxMenu);
  window.addEventListener("click", closeCtxMenu);
});

onBeforeUnmount(() => {
  window.removeEventListener("contextmenu", onGlobalCtxMenu);
  window.removeEventListener("click", closeCtxMenu);
});
</script>

<template>
  <aside class="sidebar" :style="{ width: width + 'px' }" @contextmenu.prevent="openCtxMenu($event, null)">
    <div class="brand">
      <div class="brand-mark" title="荣科 BRING SPRING">
        <img class="brand-logo" :src="logoUrl" alt="荣科" />
      </div>
      <span class="brand-text">血透<small>实施工具助手</small></span>
    </div>
    <nav class="nav">
      <a
        v-for="d in dsList"
        :key="d.id"
        class="nav-item ds-item"
        :class="{ active: d.id === activeDsId }"
        :title="`${d.database || '未配置'} @ ${d.host || '?'}:${d.port}（双击新开一个导入会话）`"
        @click="onClickDs(d)"
        @dblclick="onDblClickDs(d)"
        @contextmenu.stop.prevent="openCtxMenu($event, d)"
      >
        <span class="nav-icon">⛁</span>
        <span class="nav-name">{{ d.name }}</span>
        <span v-if="isTabOpen(d.id)" class="ds-open-flag" title="已打开工作台"></span>
        <span
          v-if="d.id === activeDsId"
          class="ds-dot"
          :class="{ ready: !!testOk, fail: !!testFail, testing }"
          :title="testOk ? `已连接 · MySQL ${testOk.version}` : testFail || '未测试'"
        ></span>
      </a>
      <p v-if="!dsList.length" class="ds-empty">
        暂无数据源<br />在空白处<b>右键</b>新建
      </p>
    </nav>
    <div class="sidebar-foot">
      <span class="dot" :class="{ ready: ready }"></span>
      <span class="foot-text">{{ status }}</span>
    </div>

    <!-- 侧栏右键菜单 -->
    <div
      v-if="ctxMenu.open"
      ref="ctxEl"
      class="ctx-menu"
      :style="{ left: ctxMenu.x + 'px', top: ctxMenu.y + 'px' }"
    >
      <button class="ctx-item" @click="ctxCreate">＋ 新建数据源</button>
      <template v-if="ctxMenu.target">
        <button class="ctx-item" @click="ctxEdit">✎ 编辑数据源</button>
        <button class="ctx-item" @click="ctxDuplicate">⧉ 复制数据源</button>
        <button class="ctx-item danger" @click="ctxDelete">✕ 删除数据源</button>
      </template>
    </div>
  </aside>
</template>
