<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listApiLogs, cleanupApiLogs, type ApiLogItem } from '@/api/admin'

const loading = ref(false)
const logs = ref<ApiLogItem[]>([])
const total = ref(0)
const query = reactive({ page: 1, size: 10, method: '', path: '', status: undefined as number | undefined })

const detailVisible = ref(false)
const detail = ref<ApiLogItem | null>(null)

async function load() {
  loading.value = true
  try {
    const res = await listApiLogs(query)
    logs.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function search() {
  query.page = 1
  load()
}

function statusTag(code: number) {
  return code < 300 ? 'success' : code < 500 ? 'warning' : 'danger'
}

function showDetail(row: ApiLogItem) {
  detail.value = row
  detailVisible.value = true
}

async function cleanup(days?: number) {
  await ElMessageBox.confirm(days ? `确定清理 ${days} 天前的日志吗？` : '确定清理过期日志吗？', '提示', {
    type: 'warning',
  })
  const res = await cleanupApiLogs(days)
  ElMessage.success(`已清理 ${res.deleted} 条`)
  load()
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>接口日志</h1>
      <p>API 调用记录（中间件自动采集，含耗时/状态/请求响应）</p>
    </div>

    <div class="info-card">
      <div class="toolbar">
        <el-select v-model="query.method" placeholder="方法" clearable style="width: 110px">
          <el-option label="GET" value="GET" />
          <el-option label="POST" value="POST" />
          <el-option label="PUT" value="PUT" />
          <el-option label="DELETE" value="DELETE" />
        </el-select>
        <el-input v-model="query.path" placeholder="路径关键字" clearable style="width: 240px" @keyup.enter="search" />
        <el-input-number v-model="query.status" :min="100" :max="599" placeholder="状态码" style="width: 140px" />
        <el-button type="primary" @click="search">查询</el-button>
        <div style="flex: 1" />
        <el-button type="warning" plain @click="cleanup(30)">清理30天前</el-button>
      </div>

      <el-table v-loading="loading" :data="logs" stripe size="default">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column label="方法" width="90">
          <template #default="{ row }">
            <el-tag size="small">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" min-width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.statusCode)" size="small">{{ row.statusCode }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="耗时" width="100">
          <template #default="{ row }">
            <span :style="{ color: row.durationMs > 1000 ? '#f56c6c' : row.durationMs > 300 ? '#e6a23c' : '#67c23a' }"
              >{{ row.durationMs }} ms</span
            >
          </template>
        </el-table-column>
        <el-table-column prop="clientIp" label="IP" width="130" />
        <el-table-column prop="username" label="用户" width="100">
          <template #default="{ row }">{{ row.username || '-' }}</template>
        </el-table-column>
        <el-table-column prop="createdAt" label="时间" width="170">
          <template #default="{ row }">{{ row.createdAt?.replace('T', ' ').slice(0, 19) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.size"
        :total="total"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        style="margin-top: 16px; justify-content: flex-end"
        @change="load"
      />
    </div>

    <el-dialog v-model="detailVisible" title="请求详情" width="640px">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="方法">{{ detail.method }}</el-descriptions-item>
          <el-descriptions-item label="路径">{{ detail.path }}</el-descriptions-item>
          <el-descriptions-item label="状态码">{{ detail.statusCode }}</el-descriptions-item>
          <el-descriptions-item label="耗时">{{ detail.durationMs }} ms</el-descriptions-item>
          <el-descriptions-item label="客户端 IP">{{ detail.clientIp || '-' }}</el-descriptions-item>
          <el-descriptions-item label="用户">{{ detail.username || '匿名' }}</el-descriptions-item>
        </el-descriptions>
        <h4 style="margin: 16px 0 8px">请求体</h4>
        <pre class="code-block">{{ detail.reqBody || '（无）' }}</pre>
        <h4 style="margin: 16px 0 8px">响应预览</h4>
        <pre class="code-block">{{ detail.respPreview || '（无）' }}</pre>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.code-block {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  max-height: 260px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
