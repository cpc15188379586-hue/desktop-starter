import { nextTick, ref, watch } from "vue";
import { clearConsole, sLogs, sRunning, sStage } from "../store";
const __VLS_props = defineProps();
const logBox = ref(null);
watch(() => sLogs.value.length, async () => {
    await nextTick();
    if (logBox.value)
        logBox.value.scrollTop = logBox.value.scrollHeight;
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "console" },
    ...{ style: ({ height: __VLS_ctx.height + 'px' }) },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "console-head" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "console-title" },
});
if (__VLS_ctx.sRunning) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "badge running" },
    });
    (__VLS_ctx.sStage);
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "console-spacer" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (__VLS_ctx.clearConsole) },
    ...{ class: "console-btn" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "console-body" },
    ref: "logBox",
});
/** @type {typeof __VLS_ctx.logBox} */ ;
__VLS_asFunctionalElement(__VLS_intrinsicElements.pre, __VLS_intrinsicElements.pre)({});
if (__VLS_ctx.sLogs.length) {
    for (const [l, i] of __VLS_getVForSourceType((__VLS_ctx.sLogs))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            key: (i),
            ...{ class: ({ sqlline: l.includes('[SQL]'), skipline: l.includes('[跳过]') }) },
        });
        (l);
    }
}
else {
}
/** @type {__VLS_StyleScopedClasses['console']} */ ;
/** @type {__VLS_StyleScopedClasses['console-head']} */ ;
/** @type {__VLS_StyleScopedClasses['console-title']} */ ;
/** @type {__VLS_StyleScopedClasses['badge']} */ ;
/** @type {__VLS_StyleScopedClasses['running']} */ ;
/** @type {__VLS_StyleScopedClasses['console-spacer']} */ ;
/** @type {__VLS_StyleScopedClasses['console-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['console-body']} */ ;
/** @type {__VLS_StyleScopedClasses['sqlline']} */ ;
/** @type {__VLS_StyleScopedClasses['skipline']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            clearConsole: clearConsole,
            sLogs: sLogs,
            sRunning: sRunning,
            sStage: sStage,
            logBox: logBox,
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
