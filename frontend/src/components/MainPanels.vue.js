import { onBeforeUnmount, onMounted, ref } from "vue";
import { getCurrentWebview } from "@tauri-apps/api/webview";
import { activeDs, backendError, browseTemplate, canRun, clearAll, dbReady, doInspect, doRun, goToStep, groupChecked, groupPartial, groups, inspecting, isRunning, isStepDone, nextStep, pickTemplate, prevStep, sCurrentSheet, sDoneSheets, sError, sProgressPct, sRunning, sStage, sResult, sRunError, sRunStarted, sRunTotal, selectAll, selected, selectedCount, setTemplatePath, sheetRows, sheets, step, templates, toggleGroup, toggleSheet, totalRows, tplError, xlsxPath, } from "../store";
const stepDefs = [
    { n: 1, name: "导入模板" },
    { n: 2, name: "选择导入内容" },
    { n: 3, name: "执行导入" },
];
// ---------- 模板拖拽（Tauri WebView 的 drop 事件不含路径，走 webview 拖放事件） ----------
const dropZone = ref(null);
const dropHover = ref(false);
let unlistenDrop = null;
function isOverZone(pos) {
    const el = dropZone.value;
    if (!el)
        return false;
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
            }
            else if (event.payload.type === "drop") {
                const hit = isOverZone(event.payload.position);
                dropHover.value = false;
                if (hit) {
                    const p = event.payload.paths[0];
                    if (p)
                        setTemplatePath(p);
                }
            }
            else {
                dropHover.value = false;
            }
        });
    }
    catch (e) {
        console.warn("注册拖放监听失败", e);
    }
});
onBeforeUnmount(() => unlistenDrop?.());
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "main-panels" },
});
if (__VLS_ctx.backendError) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "error backend-error" },
    });
    (__VLS_ctx.backendError);
    if (__VLS_ctx.backendError.includes('Not Found')) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "hint" },
            ...{ style: {} },
        });
    }
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
    ...{ class: "panel wizard-panel" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.ol, __VLS_intrinsicElements.ol)({
    ...{ class: "stepper" },
});
for (const [s] of __VLS_getVForSourceType((__VLS_ctx.stepDefs))) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.goToStep(s.n);
            } },
        key: (s.n),
        ...{ class: "step-item" },
        ...{ class: ({ current: __VLS_ctx.step === s.n, done: __VLS_ctx.isStepDone(s.n), reachable: __VLS_ctx.step > s.n || __VLS_ctx.isStepDone(s.n) }) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "step-dot" },
    });
    if (__VLS_ctx.isStepDone(s.n) && __VLS_ctx.step !== s.n) {
    }
    else {
        (s.n);
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "step-title" },
    });
    (s.name);
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "step-body" },
});
__VLS_asFunctionalDirective(__VLS_directives.vShow)(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.step === 1) }, null, null);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "panel-head" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (__VLS_ctx.doInspect) },
    ...{ class: "ghost" },
    disabled: (__VLS_ctx.inspecting || !__VLS_ctx.xlsxPath),
});
(__VLS_ctx.inspecting ? "解析中…" : __VLS_ctx.sheets.length ? "重新解析" : "解析模板");
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "hint muted" },
    ...{ style: {} },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
(__VLS_ctx.activeDs?.name || "未选择");
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ onClick: (__VLS_ctx.browseTemplate) },
    ref: "dropZone",
    ...{ class: "dropzone" },
    ...{ class: ({ hover: __VLS_ctx.dropHover, active: !!__VLS_ctx.xlsxPath }) },
});
/** @type {typeof __VLS_ctx.dropZone} */ ;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "drop-icon" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "drop-text" },
});
if (__VLS_ctx.dropHover) {
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
}
if (__VLS_ctx.xlsxPath) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "drop-file" },
    });
    (__VLS_ctx.xlsxPath);
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "drop-hint muted" },
    });
}
if (__VLS_ctx.templates.length) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "tpl-list" },
    });
    for (const [t] of __VLS_getVForSourceType((__VLS_ctx.templates))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
            ...{ onClick: (...[$event]) => {
                    if (!(__VLS_ctx.templates.length))
                        return;
                    __VLS_ctx.pickTemplate(t);
                } },
            key: (t.path),
            ...{ class: "tpl" },
            ...{ class: ({ active: t.path === __VLS_ctx.xlsxPath }) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "tpl-name" },
        });
        (t.name);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "muted" },
        });
        (t.mtime);
    }
}
if (__VLS_ctx.tplError) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "error" },
    });
    (__VLS_ctx.tplError);
}
if (__VLS_ctx.sheets.length) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "hint muted" },
    });
    (__VLS_ctx.sheets.length);
    (__VLS_ctx.totalRows);
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "step-body" },
});
__VLS_asFunctionalDirective(__VLS_directives.vShow)(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.step === 2) }, null, null);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "panel-head" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "panel-actions" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (__VLS_ctx.selectAll) },
    ...{ class: "ghost" },
    disabled: (__VLS_ctx.sRunning),
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (__VLS_ctx.clearAll) },
    ...{ class: "ghost" },
    disabled: (__VLS_ctx.sRunning),
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "group-wrap" },
});
for (const [g] of __VLS_getVForSourceType((__VLS_ctx.groups))) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        key: (g.id),
        ...{ class: "group" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({
        ...{ onClick: (...[$event]) => {
                __VLS_ctx.toggleGroup(g);
            } },
        ...{ class: "group-title" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "checkbox" },
        ...{ class: ({ on: __VLS_ctx.groupChecked(g), half: __VLS_ctx.groupPartial(g) }) },
    });
    (g.name);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "sheet-list" },
    });
    for (const [s] of __VLS_getVForSourceType((g.sheets))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({
            ...{ onClick: (...[$event]) => {
                    __VLS_ctx.toggleSheet(s);
                } },
            key: (s),
            ...{ class: "sheet" },
            ...{ class: ({ off: __VLS_ctx.sRunning }) },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "checkbox" },
            ...{ class: ({ on: __VLS_ctx.selected.has(s) }) },
        });
        (s);
        if (__VLS_ctx.sheetRows(s) !== null) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({
                ...{ class: "muted" },
            });
            (__VLS_ctx.sheetRows(s));
        }
    }
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "hint muted" },
});
(__VLS_ctx.selectedCount);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "step-body" },
});
__VLS_asFunctionalDirective(__VLS_directives.vShow)(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.step === 3) }, null, null);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "panel-head" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({});
if (__VLS_ctx.sRunning) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "badge running" },
    });
    (__VLS_ctx.sStage);
}
else if (__VLS_ctx.sResult) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "badge" },
        ...{ class: (__VLS_ctx.sResult.ok ? 'ok' : 'fail') },
    });
    (__VLS_ctx.sResult.ok ? "成功" : "有失败项");
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "actions" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.doRun(false, false);
        } },
    ...{ class: "primary" },
    disabled: (!__VLS_ctx.canRun),
    title: (__VLS_ctx.isRunning && !__VLS_ctx.sRunning ? '其他会话正在导入，请等待其完成' : ''),
});
(__VLS_ctx.sRunning ? "导入中…" : "演练导入选中（不落库）");
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.doRun(true, false);
        } },
    ...{ class: "primary" },
    disabled: (!__VLS_ctx.canRun),
    title: (__VLS_ctx.isRunning && !__VLS_ctx.sRunning ? '其他会话正在导入，请等待其完成' : ''),
});
(__VLS_ctx.sRunning ? "导入中…" : "正式导入选中");
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.doRun(true, true);
        } },
    ...{ class: "accent" },
    disabled: (!__VLS_ctx.dbReady || !__VLS_ctx.xlsxPath || __VLS_ctx.isRunning),
    title: (__VLS_ctx.isRunning && !__VLS_ctx.sRunning ? '其他会话正在导入，请等待其完成' : ''),
});
(__VLS_ctx.sRunning ? "导入中…" : "一键导入全部");
if (__VLS_ctx.sRunStarted) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "run-live" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "progress-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "pbar" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "pfill" },
        ...{ class: ({ indet: __VLS_ctx.sRunning && __VLS_ctx.sProgressPct === 0 }) },
        ...{ style: ({ width: (__VLS_ctx.sRunning && __VLS_ctx.sProgressPct === 0 ? 100 : __VLS_ctx.sProgressPct) + '%' }) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "progress-text" },
    });
    if (__VLS_ctx.sRunning) {
        (__VLS_ctx.sProgressPct ? `${__VLS_ctx.sDoneSheets}/${__VLS_ctx.sRunTotal}` : "准备中");
        if (__VLS_ctx.sCurrentSheet) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
            (__VLS_ctx.sCurrentSheet);
        }
        else if (!__VLS_ctx.sProgressPct) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
            (__VLS_ctx.sStage);
        }
    }
    else {
        (__VLS_ctx.sDoneSheets);
        (__VLS_ctx.sRunTotal);
    }
}
if (__VLS_ctx.sRunError) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "error" },
    });
    (__VLS_ctx.sRunError);
}
if (__VLS_ctx.sError) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "error" },
    });
    (__VLS_ctx.sError);
}
if (__VLS_ctx.sResult) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "report" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.table, __VLS_intrinsicElements.table)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.thead, __VLS_intrinsicElements.thead)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.tr, __VLS_intrinsicElements.tr)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.th, __VLS_intrinsicElements.th)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.tbody, __VLS_intrinsicElements.tbody)({});
    for (const [it] of __VLS_getVForSourceType((__VLS_ctx.sResult.items))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.tr, __VLS_intrinsicElements.tr)({
            key: (it.name),
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
        (it.name);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
        (it.added);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
        (it.skipped);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({
            ...{ class: ({ warn: it.warns.length }) },
        });
        (it.warns.length);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({
            ...{ class: ({ bad: it.errors.length }) },
        });
        (it.errors.length);
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.tr, __VLS_intrinsicElements.tr)({
        ...{ class: "total-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
    (__VLS_ctx.sResult.totals.added);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
    (__VLS_ctx.sResult.totals.skipped);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
    (__VLS_ctx.sResult.totals.warnings);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.td, __VLS_intrinsicElements.td)({});
    (__VLS_ctx.sResult.totals.errors);
    if (__VLS_ctx.sResult.totals.warnings) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "detail" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
        for (const [w, i] of __VLS_getVForSourceType((__VLS_ctx.sResult.items.flatMap((x) => x.warns)))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
                key: ('w' + i),
            });
            (w);
        }
    }
    if (__VLS_ctx.sResult.totals.errors) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "detail" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
        for (const [e, i] of __VLS_getVForSourceType((__VLS_ctx.sResult.items.flatMap((x) => x.errors)))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
                key: ('e' + i),
                ...{ class: "error" },
            });
            (e);
        }
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "hint muted" },
    });
    (__VLS_ctx.sResult.committed
        ? "本次导入已提交写库；重复执行会自动跳过已存在数据。"
        : "本次为演练或失败回滚，数据库未改动。");
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "wizard-nav" },
});
if (__VLS_ctx.step > 1) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.prevStep) },
        ...{ class: "ghost" },
    });
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "wizard-spacer" },
});
if (__VLS_ctx.step < 3) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
        ...{ onClick: (__VLS_ctx.nextStep) },
        ...{ class: "primary" },
        disabled: (!__VLS_ctx.isStepDone(__VLS_ctx.step)),
    });
    (__VLS_ctx.stepDefs[__VLS_ctx.step].name);
}
/** @type {__VLS_StyleScopedClasses['main-panels']} */ ;
/** @type {__VLS_StyleScopedClasses['error']} */ ;
/** @type {__VLS_StyleScopedClasses['backend-error']} */ ;
/** @type {__VLS_StyleScopedClasses['hint']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['wizard-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['stepper']} */ ;
/** @type {__VLS_StyleScopedClasses['step-item']} */ ;
/** @type {__VLS_StyleScopedClasses['current']} */ ;
/** @type {__VLS_StyleScopedClasses['done']} */ ;
/** @type {__VLS_StyleScopedClasses['reachable']} */ ;
/** @type {__VLS_StyleScopedClasses['step-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['step-title']} */ ;
/** @type {__VLS_StyleScopedClasses['step-body']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['ghost']} */ ;
/** @type {__VLS_StyleScopedClasses['hint']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['dropzone']} */ ;
/** @type {__VLS_StyleScopedClasses['hover']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['drop-icon']} */ ;
/** @type {__VLS_StyleScopedClasses['drop-text']} */ ;
/** @type {__VLS_StyleScopedClasses['drop-file']} */ ;
/** @type {__VLS_StyleScopedClasses['drop-hint']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['tpl-list']} */ ;
/** @type {__VLS_StyleScopedClasses['tpl']} */ ;
/** @type {__VLS_StyleScopedClasses['active']} */ ;
/** @type {__VLS_StyleScopedClasses['tpl-name']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['error']} */ ;
/** @type {__VLS_StyleScopedClasses['hint']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['step-body']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['ghost']} */ ;
/** @type {__VLS_StyleScopedClasses['ghost']} */ ;
/** @type {__VLS_StyleScopedClasses['group-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['group']} */ ;
/** @type {__VLS_StyleScopedClasses['group-title']} */ ;
/** @type {__VLS_StyleScopedClasses['checkbox']} */ ;
/** @type {__VLS_StyleScopedClasses['on']} */ ;
/** @type {__VLS_StyleScopedClasses['half']} */ ;
/** @type {__VLS_StyleScopedClasses['sheet-list']} */ ;
/** @type {__VLS_StyleScopedClasses['sheet']} */ ;
/** @type {__VLS_StyleScopedClasses['off']} */ ;
/** @type {__VLS_StyleScopedClasses['checkbox']} */ ;
/** @type {__VLS_StyleScopedClasses['on']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['hint']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['step-body']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-head']} */ ;
/** @type {__VLS_StyleScopedClasses['badge']} */ ;
/** @type {__VLS_StyleScopedClasses['running']} */ ;
/** @type {__VLS_StyleScopedClasses['badge']} */ ;
/** @type {__VLS_StyleScopedClasses['actions']} */ ;
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
/** @type {__VLS_StyleScopedClasses['accent']} */ ;
/** @type {__VLS_StyleScopedClasses['run-live']} */ ;
/** @type {__VLS_StyleScopedClasses['progress-row']} */ ;
/** @type {__VLS_StyleScopedClasses['pbar']} */ ;
/** @type {__VLS_StyleScopedClasses['pfill']} */ ;
/** @type {__VLS_StyleScopedClasses['indet']} */ ;
/** @type {__VLS_StyleScopedClasses['progress-text']} */ ;
/** @type {__VLS_StyleScopedClasses['error']} */ ;
/** @type {__VLS_StyleScopedClasses['error']} */ ;
/** @type {__VLS_StyleScopedClasses['report']} */ ;
/** @type {__VLS_StyleScopedClasses['warn']} */ ;
/** @type {__VLS_StyleScopedClasses['bad']} */ ;
/** @type {__VLS_StyleScopedClasses['total-row']} */ ;
/** @type {__VLS_StyleScopedClasses['detail']} */ ;
/** @type {__VLS_StyleScopedClasses['detail']} */ ;
/** @type {__VLS_StyleScopedClasses['error']} */ ;
/** @type {__VLS_StyleScopedClasses['hint']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['wizard-nav']} */ ;
/** @type {__VLS_StyleScopedClasses['ghost']} */ ;
/** @type {__VLS_StyleScopedClasses['wizard-spacer']} */ ;
/** @type {__VLS_StyleScopedClasses['primary']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            activeDs: activeDs,
            backendError: backendError,
            browseTemplate: browseTemplate,
            canRun: canRun,
            clearAll: clearAll,
            dbReady: dbReady,
            doInspect: doInspect,
            doRun: doRun,
            goToStep: goToStep,
            groupChecked: groupChecked,
            groupPartial: groupPartial,
            groups: groups,
            inspecting: inspecting,
            isRunning: isRunning,
            isStepDone: isStepDone,
            nextStep: nextStep,
            pickTemplate: pickTemplate,
            prevStep: prevStep,
            sCurrentSheet: sCurrentSheet,
            sDoneSheets: sDoneSheets,
            sError: sError,
            sProgressPct: sProgressPct,
            sRunning: sRunning,
            sStage: sStage,
            sResult: sResult,
            sRunError: sRunError,
            sRunStarted: sRunStarted,
            sRunTotal: sRunTotal,
            selectAll: selectAll,
            selected: selected,
            selectedCount: selectedCount,
            sheetRows: sheetRows,
            sheets: sheets,
            step: step,
            templates: templates,
            toggleGroup: toggleGroup,
            toggleSheet: toggleSheet,
            totalRows: totalRows,
            tplError: tplError,
            xlsxPath: xlsxPath,
            stepDefs: stepDefs,
            dropZone: dropZone,
            dropHover: dropHover,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
