<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

/**
 * 顶部路由加载进度条（最顶上细条）：
 * 路由切换开始时出现并推进，加载完成/失败后收起。
 * 让用户在移动端点击菜单后能明确感知「页面正在加载」。
 */
const router = useRouter()
const visible = ref(false)
const width = ref(0)
let timer: number | null = null
let hideTimer: number | null = null

function start() {
  if (hideTimer) {
    window.clearTimeout(hideTimer)
    hideTimer = null
  }
  visible.value = true
  width.value = 10
  if (timer) window.clearInterval(timer)
  timer = window.setInterval(() => {
    width.value = Math.min(92, width.value + Math.random() * 16)
  }, 300)
}

function finish() {
  if (timer) {
    window.clearInterval(timer)
    timer = null
  }
  width.value = 100
  hideTimer = window.setTimeout(() => {
    visible.value = false
    width.value = 0
  }, 300)
}

onMounted(() => {
  router.beforeEach(() => {
    start()
  })
  router.afterEach(() => {
    finish()
  })
  router.onError(() => {
    finish()
  })
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
  if (hideTimer) window.clearTimeout(hideTimer)
})
</script>

<template>
  <div v-if="visible" class="route-progress" :style="{ width: width + '%' }" />
</template>

<style scoped>
.route-progress {
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  background: linear-gradient(90deg, #2c6e49, #4c956c);
  box-shadow: 0 0 6px rgba(44, 110, 73, 0.5);
  z-index: 99999;
  transition: width 0.3s ease;
}
</style>
