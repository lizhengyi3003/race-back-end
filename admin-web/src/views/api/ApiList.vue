<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getApiSpec, type ApiSpecItem } from '@/api/admin'

const router = useRouter()
const spec = ref<ApiSpecItem[]>([])
const loading = ref(false)
const keyword = ref('')
const filterTag = ref('')

const grouped = computed(() => {
  const map = new Map<string, ApiSpecItem[]>()
  const list = spec.value.filter((s) => {
    const matchKw = !keyword.value || s.path.includes(keyword.value) || s.summary.includes(keyword.value)
    const matchTag = !filterTag.value || s.tags.includes(filterTag.value)
    return matchKw && matchTag
  })
  for (const item of list) {
    const tag = item.tags[0] || '其他'
    if (!map.has(tag)) map.set(tag, [])
    map.get(tag)!.push(item)
  }
  return [...map.entries()]
})

const allTags = computed(() => [...new Set(spec.value.map((s) => s.tags[0]).filter(Boolean))])

const methodColor: Record<string, string> = {
  GET: '#67c23a',
  POST: '#409eff',
  PUT: '#e6a23c',
  DELETE: '#f56c6c',
  PATCH: '#9b5de5',
}

function testApi(item: ApiSpecItem) {
  router.push({ path: '/api/tester', query: { path: item.path, method: item.method } })
}

onMounted(async () => {
  loading.value = true
  try {
    spec.value = await getApiSpec()
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>接口列表</h1>
      <p>后端 API 端点一览（来自 OpenAPI 规范，共 {{ spec.length }} 个）</p>
    </div>

    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索路径/说明" clearable style="width: 260px" />
      <el-select v-model="filterTag" placeholder="按模块筛选" clearable style="width: 180px">
        <el-option v-for="t in allTags" :key="t" :label="t" :value="t" />
      </el-select>
    </div>

    <div v-for="[tag, items] in grouped" :key="tag" class="info-card" style="margin-bottom: 16px">
      <h3 class="card-title">{{ tag }}（{{ items.length }}）</h3>
      <el-table v-loading="loading" :data="items" size="small">
        <el-table-column label="方法" width="90">
          <template #default="{ row }">
            <el-tag :color="methodColor[row.method]" style="border: none; color: #fff" size="small">{{
              row.method
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="路径" min-width="280">
          <template #default="{ row }">
            <code style="font-size: 13px; color: #303133">{{ row.path }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="说明" min-width="200" />
        <el-table-column label="鉴权" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.authMode === 'required'" type="warning" size="small">需登录</el-tag>
            <el-tag v-else-if="row.authMode === 'optional'" type="info" size="small">公开可选</el-tag>
            <el-tag v-else type="success" size="small" effect="plain">公开</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="testApi(row)">测试</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
