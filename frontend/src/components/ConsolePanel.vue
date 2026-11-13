<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { clearConsole, sLogs, sRunning, sStage } from "../store";

defineProps<{ height: number }>();

const logBox = ref<HTMLElement | null>(null);

watch(
  () => sLogs.value.length,
  async () => {
    await nextTick();
    if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight;
  }
);
</script>

<template>
  <!-- 底部控制台：命令行输出（只显示当前会话自己的日志） -->
  <div class="console" :style="{ height: height + 'px' }">
    <div class="console-head">
      <span class="console-title">运行日志</span>
      <span v-if="sRunning" class="badge running">{{ sStage }}…</span>
      <span class="console-spacer"></span>
      <button class="console-btn" @click="clearConsole">清空显示</button>
    </div>
    <div class="console-body" ref="logBox">
      <pre><template v-if="sLogs.length"><span
        v-for="(l, i) in sLogs" :key="i"
        :class="{ sqlline: l.includes('[SQL]'), skipline: l.includes('[跳过]') }"
      >{{ l }}
</span></template><template v-else class="console-empty">// 本会话的运行日志。点击「执行导入」后，这里会实时显示连接、SQL 与每张表的处理结果。
</template></pre>
    </div>
  </div>
</template>
