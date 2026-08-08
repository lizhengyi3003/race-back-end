<template>
  <RouteProgress />
  <router-view />
</template>

<script setup lang="ts">
import RouteProgress from '@/components/RouteProgress.vue'
</script>

<style>
html,
body,
#app {
  height: 100%;
  margin: 0;
  padding: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', Arial, sans-serif;
  background: #f0f2f5;
}
</style>
