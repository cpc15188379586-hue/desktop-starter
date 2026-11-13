import { nextTick, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { activeDsId, activateDsFirstSession, dsList, deleteDs, isTabOpen, openCreateDs, openDsTab, openDuplicateDs, openEditDs, ready, setActiveDs, status, testFail, testOk, testing, } from "../store";
import logoUrl from "../images/logo-DuWjEJcK.png";
const __VLS_props = defineProps();
// 单击：选中（已打开会话则切到第一个会话）；双击：新开一个会话（同一数据源可开多个）
function onClickDs(d) {
    if (!activateDsFirstSession(d.id))
        setActiveDs(d.id);
}
function onDblClickDs(d) {
    openDsTab(d);
}
// ---------- 侧栏右键菜单 ----------
const ctxMenu = reactive({ open: false, x: 0, y: 0, target: null });
const ctxEl = ref(null);
let suppressCtx = false;
function openCtxMenu(e, target) {
    ctxMenu.open = true;
    ctxMenu.target = target;
    ctxMenu.x = e.clientX;
    ctxMenu.y = e.clientY;
    nextTick(() => {
        const el = ctxEl.value;
        if (!el)
            return;
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
    if (ds)
        openEditDs(ds);
}
function ctxDuplicate() {
    const ds = ctxMenu.target;
    closeCtxMenu();
    if (ds)
        openDuplicateDs(ds);
}
function ctxDelete() {
    const ds = ctxMenu.target;
    closeCtxMenu();
    if (ds)
        deleteDs(ds);
}
onMounted(() => {
    window.addEventListener("contextmenu", onGlobalCtxMenu);
    window.addEventListener("click", closeCtxMenu);
});
onBeforeUnmount(() => {
    window.removeEventListener("contextmenu", onGlobalCtxMenu);
    window.removeEventListener("click", closeCtxMenu);
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.aside, __VLS_intrinsicElements.aside)({
    ...{ onContextmenu: (...[$event]) => {
            __VLS_ctx.openCtxMenu($event, null);
        } },
    ...{ class: "sidebar" },
    ...{ style: ({ width: __VLS_ctx.width + 'px' }) },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "brand" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "brand-mark" },
    title: "荣科 BRING SPRING",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.img)({
    ...{ class: "brand-logo" },
    src: (__VLS_ctx.logoUrl),
    alt: "荣科",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "brand-text" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.nav, __VLS_intrinsicElements.nav)({
    ...{ class: "nav" },
});
for (const [d] of __VLS_getVForSourceType((__VLS_ctx.dsList))) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.a, __VLS_intrinsicElements.a)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.onClickDs(d);
            } },
        ...{ onDblclick: (...[$event]) => {
                __VLS_ctx.onDblClickDs(d);
            } },
        ...{ onContextmenu: (...[$event]) => {
                __VLS_ctx.openCtxMenu($event, d);
            } },
        key: (d.id),
        ...{ class: "nav-item ds-item" },
        ...{ class: ({ active: d.id === __VLS_ctx.activeDsId }) },
        title: (`${d.database || '未配置'} @ ${d.host || '?'}:${d.port}（双击新开一个导入会话）`),
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "nav-icon" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "nav-name" },
    });
    (d.name);
    if (__VLS_ctx.isTabOpen(d.id)) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "ds-open-flag" },
            title: "已打开工作台",
        });
    }
    if (d.id === __VLS_ctx.activeDsId) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "ds-dot" },
            ...{ class: ({ ready: !!__VLS_ctx.testOk, fail: !!__VLS_ctx.testFail, testing: __VLS_ctx.testing }) },
            title: (__VLS_ctx.testOk ? `已连接 · MySQL ${__VLS_ctx.testOk.version}` : __VLS_ctx.testFail || '未测试'),
        });
    }
}
if (!__VLS_ctx.dsList.length) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "ds-empty" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.br)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "sidebar-foot" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "dot" },
    ...{ class: ({ ready: __VLS_ctx.ready }) },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "foot-text" },
});
(__VLS_ctx.status);
if (__VLS_ctx.ctxMenu.open) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ref: "ctxEl",
        ...{ class: "ctx-menu" },
        ...{ style: ({ left: __VLS_ctx.ctxMenu.x + 'px', top: __VLS_ctx.ctxMenu.y + 'px' }) },
    });
    /** @type {typeof __VLS_ctx.ctxEl} */ ;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.ctxCreate) },
        ...{ class: "ctx-item" },
    });
    if (__VLS_ctx.ctxMenu.target) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.ctxEdit) },
            ...{ class: "ctx-item" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.ctxDuplicate) },
            ...{ class: "ctx-item" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (__VLS_ctx.ctxDelete) },
            ...{ class: "ctx-item danger" },
        });
    }
}
/** @type {__VLS_StyleScopedClasses['sidebar']} */ ;
/** @type {__VLS_StyleScopedClasses['brand']} */ ;
/** @type {__VLS_StyleScopedClasses['brand-mark']} */ ;
/** @type {__VLS_StyleScopedClasses['brand-logo']} */ ;
/** @type {__VLS_StyleScopedClasses['brand-text']} */ ;
/** @type {__VLS_StyleScopedClasses['nav']} */ ;
/** @type {__VLS_StyleScopedClasses['nav-item']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-item']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['nav-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['nav-name']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-open-flag']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['ready']} */ ;
/** @type {__VLS_StyleScopedClasses['fail']} */ ;
/** @type {__VLS_StyleScopedClasses['testing']} */ ;
/** @type {__VLS_StyleScopedClasses['ds-empty']} */ ;
/** @type {__VLS_StyleScopedClasses['sidebar-foot']} */ ;
/** @type {__VLS_StyleScopedClasses['dot']} */ ;
/** @type {__VLS_StyleScopedClasses['ready']} */ ;
/** @type {__VLS_StyleScopedClasses['foot-text']} */ ;
/** @type {__VLS_StyleScopedClasses['ctx-menu']} */ ;
/** @type {__VLS_StyleScopedClasses['ctx-item']} */ ;
/** @type {__VLS_StyleScopedClasses['ctx-item']} */ ;
/** @type {__VLS_StyleScopedClasses['ctx-item']} */ ;
/** @type {__VLS_StyleScopedClasses['ctx-item']} */ ;
/** @type {__VLS_StyleScopedClasses['danger']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            activeDsId: activeDsId,
            dsList: dsList,
            isTabOpen: isTabOpen,
            ready: ready,
            status: status,
            testFail: testFail,
            testOk: testOk,
            testing: testing,
            logoUrl: logoUrl,
            onClickDs: onClickDs,
            onDblClickDs: onDblClickDs,
            ctxMenu: ctxMenu,
            ctxEl: ctxEl,
            openCtxMenu: openCtxMenu,
            ctxCreate: ctxCreate,
            ctxEdit: ctxEdit,
            ctxDuplicate: ctxDuplicate,
            ctxDelete: ctxDelete,
        };
    },
    __typeProps: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeProps: {},
});
; /* PartiallyEnd: #4569/main.vue */
