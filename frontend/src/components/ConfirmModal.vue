<script setup lang="ts">
import { answerConfirm, confirmBox } from "../store";
</script>

<template>
  <!-- 应用内确认弹窗 -->
  <div v-if="confirmBox.open" class="modal-mask" @click.self="answerConfirm(false)">
    <div class="modal">
      <h3>{{ confirmBox.title }}</h3>
      <p v-for="(line, i) in confirmBox.message" :key="i" class="modal-line">{{ line }}</p>
      <div class="modal-actions">
        <button class="ghost" @click="answerConfirm(false)">取消</button>
        <button :class="confirmBox.danger ? 'danger' : 'primary'" @click="answerConfirm(true)">
          确定执行
        </button>
      </div>
    </div>
  </div>
</template>
