<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getThresholds, saveThresholds as updateThresholds, type Thresholds } from '@/api/model'
import { listSystemConfigs, updateSystemConfig } from '@/api/admin'

const thresholds = ref<Thresholds>({
  lowRiskThreshold: 700,
  highRiskThreshold: 500,
  baseRate: 3.5,
  riskPremiumFactor: 6.0,
})
const saving = ref(false)

const configs = ref<any[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const [t, c] = await Promise.all([getThresholds(), listSystemConfigs()])
    thresholds.value = t
    configs.value = c
  } finally {
    loading.value = false
  }
}

async function handleSaveThresholds() {
  if (thresholds.value.lowRiskThreshold <= thresholds.value.highRiskThreshold) {
    ElMessage.warning('低风险阈值必须大于高风险阈值')
    return
  }
  saving.value = true
  try {
    const res = await updateThresholds(thresholds.value)
    thresholds.value = res
    ElMessage.success('阈值已保存，评估接口即时生效')
  } finally {
    saving.value = false
  }
}

async function saveConfig(row: any) {
  try {
    await updateSystemConfig(row.key, row.value)
    ElMessage.success('配置已更新')
  } catch {
    // 忽略
  }
}

const CONFIG_DESC: Record<string, string> = {
  low_risk_threshold: '低风险评分阈值（≥ 此分为低风险）',
  high_risk_threshold: '高风险评分阈值（< 此分为高风险）',
  base_rate: '基准贷款利率（%）',
  risk_premium_factor: '风险溢价系数（越高利率上浮越大）',
  api_log_retention_days: 'API 日志保留天数',
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>系统配置</h1>
      <p>评分卡业务阈值与系统参数在线管理</p>
    </div>

    <el-row :gutter="16">
      <el-col :span="12">
        <div class="info-card">
          <h3 class="card-title">评分卡业务阈值</h3>
          <el-form v-loading="loading" label-width="140px">
            <el-form-item label="低风险阈值（分）">
              <el-input-number v-model="thresholds.lowRiskThreshold" :min="600" :max="900" />
              <div class="form-tip">评分 ≥ 该值判定为低风险（绿色）</div>
            </el-form-item>
            <el-form-item label="高风险阈值（分）">
              <el-input-number v-model="thresholds.highRiskThreshold" :min="300" :max="600" />
              <div class="form-tip">评分 &lt; 该值判定为高风险（红色）</div>
            </el-form-item>
            <el-form-item label="基准利率（%）">
              <el-input-number v-model="thresholds.baseRate" :min="0" :max="20" :step="0.1" />
            </el-form-item>
            <el-form-item label="风险溢价系数">
              <el-input-number v-model="thresholds.riskPremiumFactor" :min="0" :max="20" :step="0.5" />
              <div class="form-tip">建议利率 = 基准利率 + (1 - 评分/1000) × 系数</div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSaveThresholds">保存阈值</el-button>
            </el-form-item>
          </el-form>
        </div>
      </el-col>

      <el-col :span="12">
        <div class="info-card">
          <h3 class="card-title">系统参数</h3>
          <el-table v-loading="loading" :data="configs" size="default">
            <el-table-column label="配置项" width="220">
              <template #default="{ row }">
                <div style="font-weight: 600">{{ row.key }}</div>
                <div style="font-size: 12px; color: #909399">{{ CONFIG_DESC[row.key] || row.description }}</div>
              </template>
            </el-table-column>
            <el-table-column label="值">
              <template #default="{ row }">
                <el-input v-model="row.value" @change="saveConfig(row)" />
              </template>
            </el-table-column>
          </el-table>
          <div class="form-tip" style="margin-top: 10px">修改后自动保存；低风险/高风险阈值也可在左侧统一管理</div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.form-tip {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}
</style>
