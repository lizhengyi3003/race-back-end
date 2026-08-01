<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listModelVersions, type ModelVersionItem } from '@/api/model'

const versions = ref<ModelVersionItem[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    versions.value = await listModelVersions()
  } finally {
    loading.value = false
  }
}

function pct(v?: number) {
  return v == null ? '-' : (v * 100).toFixed(1) + '%'
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>模型版本</h1>
      <p>评分卡训练历史与版本管理（最近 50 次）</p>
    </div>

    <div class="info-card">
      <el-table v-loading="loading" :data="versions" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="version" label="版本号" min-width="170">
          <template #default="{ row }">
            <span style="font-weight: 600">{{ row.version }}</span>
            <el-tag v-if="row.status === 'active'" type="success" size="small" style="margin-left: 8px"
              >当前生效</el-tag
            >
          </template>
        </el-table-column>
        <el-table-column prop="nSamples" label="样本量" width="100" />
        <el-table-column prop="nFeatures" label="特征数" width="90" />
        <el-table-column label="AUC" width="100">
          <template #default="{ row }">{{ row.auc?.toFixed(4) ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="KS" width="100">
          <template #default="{ row }">{{ row.ks?.toFixed(4) ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="召回率" width="100">
          <template #default="{ row }">{{ pct(row.recall) }}</template>
        </el-table-column>
        <el-table-column label="精确率" width="100">
          <template #default="{ row }">{{ pct(row.precision) }}</template>
        </el-table-column>
        <el-table-column prop="trainedBy" label="训练人" width="110" />
        <el-table-column prop="createdAt" label="训练时间" width="180">
          <template #default="{ row }">{{ row.createdAt?.replace('T', ' ').slice(0, 19) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>
