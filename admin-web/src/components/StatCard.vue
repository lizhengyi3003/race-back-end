<script setup lang="ts">
defineProps<{
  title: string
  value: number | string
  unit?: string
  icon?: string
  color?: string
  desc?: string
}>()
</script>

<template>
  <div class="stat-card">
    <div class="icon-wrap" :style="{ background: (color || '#2c6e49') + '1a', color: color || '#2c6e49' }">
      <el-icon :size="24"><component :is="icon || 'DataLine'" /></el-icon>
    </div>
    <div class="content">
      <div class="value">
        {{ value }}<span v-if="unit" class="unit">{{ unit }}</span>
      </div>
      <div class="title">{{ title }}</div>
      <div v-if="desc" class="desc">{{ desc }}</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.stat-card {
  background: #fff;
  border-radius: 10px;
  padding: 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s;

  &:hover {
    transform: translateY(-2px);
  }

  .icon-wrap {
    width: 52px;
    height: 52px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .content {
    .value {
      font-size: 24px;
      font-weight: 700;
      color: #303133;
      line-height: 1.2;

      .unit {
        font-size: 13px;
        color: #909399;
        font-weight: 400;
        margin-left: 4px;      }
    }

    .title {
      font-size: 13px;
      color: #909399;
      margin-top: 2px;
    }

    .desc {
      font-size: 11px;
      color: #a8abb2;
      line-height: 1.5;
      margin-top: 4px;
      max-width: 260px;
    }
  }
}
</style>
