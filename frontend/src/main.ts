import { createApp } from "vue";
import { invoke } from "@tauri-apps/api/core";
import App from "./App.vue";
import "./style.css";

createApp(App).mount("#app");

// 主窗口渲染完成后，关闭启动画面并显示主窗口
// 启动画面最短显示 2 秒，避免一闪而过
const SPLASH_MIN_DURATION = 2000;

if ("__TAURI_INTERNALS__" in window) {
  const start = Date.now();
  const wait = Math.max(0, SPLASH_MIN_DURATION - (Date.now() - start));
  setTimeout(() => {
    invoke("close_splashscreen").catch((err) => {
      console.error("关闭启动画面失败:", err);
    });
  }, wait);
}
