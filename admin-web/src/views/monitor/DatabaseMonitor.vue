<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getDatabaseStatus, type DatabaseStatus } from '@/api/monitor'

const db = ref<DatabaseStatus | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    db.value = await getDatabaseStatus()
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>数据库状态</h1>
      <p>数据库连接、表结构与容量监控</p>
    </div>

    <div class="metric-grid">
      <div class="info-card stat-card-mini">
        <div class="label">连接状态</div>
        <div class="value">
          <el-tag :type="db?.connected ? 'success' : 'danger'" size="large">{{
            db?.connected ? '正常' : '异常'
          }}</el-tag>
        </div>
      </div>
      <div class="info-card stat-card-mini">
        <div class="label">数据库类型</div>
        <div class="value">{{ db?.dialect ?? '-' }}</div>
      </div>
      <div class="info-card stat-card-mini">
        <div class="label">数据表数量</div>
        <div class="value">{{ db?.tables?.length ?? '-' }}</div>
      </div>
      <div class="info-card stat-card-mini">
        <div class="label">总容量</div>
        <div class="value">{{ db?.totalSizeMb ?? '-' }} MB</div>
      </div>
    </div>

    <div class="info-card">
      <h3 class="card-title">数据表</h3>
      <el-table v-loading="loading" :data="db?.tables ?? []" stripe style="min-width: 1152px">
        <el-table-column prop="name" label="表名" min-width="220" />
        <el-table-column prop="rows" label="记录数" width="150" />
        <el-table-column label="容量 (MB)" width="150">
          <template #default="{ row }">{{ row.sizeMb.toFixed(3) }}</template>
        </el-table-column>
        <el-table-column label="容量占比" min-width="200">
          <template #default="{ row }">
            <el-progress
              :percentage="db?.totalSizeMb ? Math.round((row.sizeMb / db.totalSizeMb) * 100) : 0"
              :stroke-width="12"
              :color="row.sizeMb > 1 ? '#4c956c' : '#909399'"
            />
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.stat-card-mini {
  .label {
    font-size: 12px;
    color: #909399;
    margin-bottom: 8px;
  }

  .value {
    font-size: 20px;
    font-weight: 700;
    color: #303133;
  }
}
</style>
