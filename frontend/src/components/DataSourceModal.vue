<script setup lang="ts">
import { doDsSave, doDsTest, dsForm, dsModal, dsTestFail, dsTestOk, dsTesting } from "../store";
</script>

<template>
  <!-- 数据源配置弹窗 -->
  <div v-if="dsModal.open" class="modal-mask" @click.self="dsModal.open = false">
    <div class="modal wide">
      <h3>{{ dsModal.editingId ? "编辑数据源" : "新建数据源" }}</h3>
      <div class="grid">
        <label>数据源名称<input v-model="dsForm.name" placeholder="如 生产环境" /></label>
        <label>数据库地址<input v-model="dsForm.host" placeholder="如 192.168.1.100" /></label>
        <label>端口<input v-model.number="dsForm.port" type="number" placeholder="3306" /></label>
        <label>用户名<input v-model="dsForm.user" placeholder="root" /></label>
        <label>密码<input v-model="dsForm.password" type="password" placeholder="••••••" /></label>
        <label>数据库名<input v-model="dsForm.database" placeholder="jsbos_hdms_v3x_xxx" /></label>
        <label>租户编码<input v-model="dsForm.tenant" placeholder="如 rkkj" /></label>
      </div>
      <p v-if="dsTestOk" class="success">连接成功，MySQL 版本：{{ dsTestOk }}</p>
      <p v-if="dsTestFail" class="error">{{ dsTestFail }}</p>
      <div class="modal-actions">
        <button class="ghost" :disabled="dsTesting" @click="doDsTest">
          {{ dsTesting ? "连接中…" : "测试连接" }}
        </button>
        <span class="modal-spacer"></span>
        <button class="ghost" @click="dsModal.open = false">取消</button>
        <button class="primary" @click="doDsSave">保存</button>
      </div>
    </div>
  </div>
</template>
