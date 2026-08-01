<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getHealth, type HealthStatus } from '@/api/monitor'

const health = ref<HealthStatus | null>(null)
const loading = ref(false)

async function check() {
  loading.value = true
  try {
    health.value = await getHealth()
  } finally {
    loading.value = false
  }
}

onMounted(check)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>健康检查</h1>
      <p>服务 / 数据库 / 模型组件探针</p>
    </div>

    <div class="info-card">
      <div class="toolbar">
        <el-tag
          :type="health?.status === 'healthy' ? 'success' : health?.status === 'degraded' ? 'warning' : 'danger'"
          size="large"
        >
          整体状态：{{ health?.status === 'healthy' ? '健康' : health?.status === 'degraded' ? '部分异常' : '异常' }}
        </el-tag>
        <div style="flex: 1" />
        <el-button type="primary" :loading="loading" @click="check">重新检测</el-button>
      </div>

      <el-row :gutter="16" style="margin-top: 8px">
        <el-col
          v-for="item in [
            { label: '后端服务', value: health?.service, ok: health?.service === 'ok', icon: 'Cpu' },
            { label: '数据库连接', value: health?.database, ok: health?.database === 'ok', icon: 'Coin' },
            {
              label: '信用评分模型',
              value: health?.modelExists ? `已加载 ${health?.modelVersion}` : '未加载',
              ok: health?.modelExists,
              icon: 'TrendCharts',
            },
          ]"
          :key="item.label"
          :span="8"
        >
          <div class="probe-card" :class="{ ok: item.ok, fail: !item.ok }">
            <el-icon :size="34" :color="item.ok ? '#67c23a' : '#f56c6c'">
              <CircleCheckFilled v-if="item.ok" />
              <CircleCloseFilled v-else />
            </el-icon>
            <div>
              <div class="probe-label">{{ item.label }}</div>
              <div class="probe-value">{{ item.value }}</div>
            </div>
          </div>
        </el-col>
      </el-row>

      <el-divider />
      <div class="form-tip">检测时间：{{ health?.timestamp?.replace('T', ' ').slice(0, 19) || '-' }}</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.probe-card {
  background: #f7f9fb;
  border-radius: 10px;
  padding: 22px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid transparent;

  &.ok {
    border-color: #e1f3d8;
  }

  &.fail {
    border-color: #fde2e2;
  }

  .probe-label {
    font-size: 13px;
    color: #909399;
  }

  .probe-value {
    font-size: 16px;
    font-weight: 600;
    color: #303133;
    margin-top: 4px;
  }
}

.form-tip {
  font-size: 12px;
  color: #909399;
}
</style>
