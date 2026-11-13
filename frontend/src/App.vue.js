import { onBeforeUnmount, onMounted, ref } from "vue";
import { activeTabId, closeDsTab, initBackend, openTabIds, setActiveTab, shutdownBackend, tabTitles } from "./store";
import SidebarDataSources from "./components/SidebarDataSources.vue";
import MainPanels from "./components/MainPanels.vue";
import ConsolePanel from "./components/ConsolePanel.vue";
import DataSourceModal from "./components/DataSourceModal.vue";
import ConfirmModal from "./components/ConfirmModal.vue";
// ---------- 面板拖拽（侧栏宽度 / 控制台高度，记忆到本地） ----------
const sidebarWidth = ref(Number(localStorage.getItem("hdms.sidebarWidth")) || 210);
const consoleHeight = ref(Number(localStorage.getItem("hdms.consoleHeight")) || 280);
let drag = null;
function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
}
function startDrag(type, e) {
    e.preventDefault();
    drag = { type, x: e.clientX, y: e.clientY, w: sidebarWidth.value, h: consoleHeight.value };
    document.body.style.userSelect = "none";
    window.addEventListener("mousemove", onDrag);
    window.addEventListener("mouseup", endDrag);
}
function onDrag(e) {
    if (!drag)
        return;
    if (drag.type === "sidebar") {
        sidebarWidth.value = clamp(drag.w + (e.clientX - drag.x), 160, 360);
    }
    else {
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
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "app" },
});
/** @type {[typeof SidebarDataSources, ]} */ ;
// @ts-ignore
const __VLS_0 = __VLS_asFunctionalComponent(SidebarDataSources, new SidebarDataSources({
    width: (__VLS_ctx.sidebarWidth),
}));
const __VLS_1 = __VLS_0({
    width: (__VLS_ctx.sidebarWidth),
}, ...__VLS_functionalComponentArgsRest(__VLS_0));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ onMousedown: (...[$event]) => {
            __VLS_ctx.startDrag('sidebar', $event);
        } },
    ...{ class: "resizer sidebar-resizer" },
    title: "拖拽调整菜单宽度",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "right" },
});
if (__VLS_ctx.openTabIds.length) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "tabbar" },
    });
    for (const [id] of __VLS_getVForSourceType((__VLS_ctx.openTabIds))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.openTabIds.length))
                        return;
                    __VLS_ctx.setActiveTab(id);
                } },
            key: (id),
            ...{ class: "tab" },
            ...{ class: ({ active: id === __VLS_ctx.activeTabId }) },
            title: (__VLS_ctx.tabTitles[id] || id),
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "tab-label" },
        });
        (__VLS_ctx.tabTitles[id] || id);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.openTabIds.length))
                        return;
                    __VLS_ctx.closeDsTab(id);
                } },
            ...{ class: "tab-close" },
            title: "关闭此会话",
        });
    }
}
if (!__VLS_ctx.openTabIds.length) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "tab-empty" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "tab-empty-icon" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "muted" },
    });
}
else {
    for (const [id] of __VLS_getVForSourceType((__VLS_ctx.openTabIds))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            key: (id),
            ...{ class: "tab-page" },
        });
        __VLS_asFunctionalDirective(__VLS_directives.vShow)(null, { ...__VLS_directiveBindingRestFields, value: (id === __VLS_ctx.activeTabId) }, null, null);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "main-scroll" },
        });
        /** @type {[typeof MainPanels, ]} */ ;
        // @ts-ignore
        const __VLS_3 = __VLS_asFunctionalComponent(MainPanels, new MainPanels({}));
        const __VLS_4 = __VLS_3({}, ...__VLS_functionalComponentArgsRest(__VLS_3));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ onMousedown: (...[$event]) => {
                    if (!!(!__VLS_ctx.openTabIds.length))
                        return;
                    __VLS_ctx.startDrag('console', $event);
                } },
            ...{ class: "resizer console-resizer" },
            title: "拖拽调整日志区高度",
        });
        /** @type {[typeof ConsolePanel, ]} */ ;
        // @ts-ignore
        const __VLS_6 = __VLS_asFunctionalComponent(ConsolePanel, new ConsolePanel({
            height: (__VLS_ctx.consoleHeight),
        }));
        const __VLS_7 = __VLS_6({
            height: (__VLS_ctx.consoleHeight),
        }, ...__VLS_functionalComponentArgsRest(__VLS_6));
    }
}
/** @type {[typeof DataSourceModal, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(DataSourceModal, new DataSourceModal({}));
const __VLS_10 = __VLS_9({}, ...__VLS_functionalComponentArgsRest(__VLS_9));
/** @type {[typeof ConfirmModal, ]} */ ;
// @ts-ignore
const __VLS_12 = __VLS_asFunctionalComponent(ConfirmModal, new ConfirmModal({}));
const __VLS_13 = __VLS_12({}, ...__VLS_functionalComponentArgsRest(__VLS_12));
/** @type {__VLS_StyleScopedClasses['app']} */ ;
/** @type {__VLS_StyleScopedClasses['resizer']} */ ;
/** @type {__VLS_StyleScopedClasses['sidebar-resizer']} */ ;
/** @type {__VLS_StyleScopedClasses['right']} */ ;
/** @type {__VLS_StyleScopedClasses['tabbar']} */ ;
/** @type {__VLS_StyleScopedClasses['tab']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-label']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-close']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-empty']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-empty-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-page']} */ ;
/** @type {__VLS_StyleScopedClasses['main-scroll']} */ ;
/** @type {__VLS_StyleScopedClasses['resizer']} */ ;
/** @type {__VLS_StyleScopedClasses['console-resizer']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            activeTabId: activeTabId,
            closeDsTab: closeDsTab,
            openTabIds: openTabIds,
            setActiveTab: setActiveTab,
            tabTitles: tabTitles,
            SidebarDataSources: SidebarDataSources,
            MainPanels: MainPanels,
            ConsolePanel: ConsolePanel,
            DataSourceModal: DataSourceModal,
            ConfirmModal: ConfirmModal,
            sidebarWidth: sidebarWidth,
            consoleHeight: consoleHeight,
            startDrag: startDrag,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
