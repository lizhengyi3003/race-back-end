<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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
    ElMessage.success(`「${row.key}」已更新`)
  } catch {
    // 忽略
  }
}

// 配置项说明（key → 说明）
const CONFIG_DESC: Record<string, string> = {
  low_risk_threshold: '低风险评分阈值：评分 ≥ 此分判定为低风险',
  high_risk_threshold: '高风险评分阈值：评分 < 此分判定为高风险',
  base_rate: '基准贷款利率（%），建议利率下限',
  risk_premium_factor: '风险溢价系数：风险越高利率上浮越大',
  api_log_retention_days: 'API 调用日志保留天数（超期自动清理）',
}

// 配置项分组
const CONFIG_GROUP: Record<string, string> = {
  low_risk_threshold: '风险评估',
  high_risk_threshold: '风险评估',
  base_rate: '风险评估',
  risk_premium_factor: '风险评估',
  api_log_retention_days: '系统运维',
}

// 风险等级区间说明
const levelHint = computed(() => {
  const { lowRiskThreshold: lo, highRiskThreshold: hi } = thresholds.value
  return `低风险 ≥ ${lo} 分 ｜ 中等风险 ${hi} ~ ${lo} 分 ｜ 高风险 < ${hi} 分`
})

// 建议利率公式
const rateHint = computed(
  () =>
    `建议利率 = 基准利率 ${thresholds.value.baseRate}% + (1 - 评分/1000) × 风险溢价系数 ${thresholds.value.riskPremiumFactor}`
)

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>系统配置</h1>
      <p>风险评估阈值、利率参数与系统运行参数在线管理（保存后即时生效）</p>
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">风险评估阈值与利率</h3>
          <el-form v-loading="loading" label-width="150px">
            <el-form-item label="低风险阈值（分）">
              <el-input-number v-model="thresholds.lowRiskThreshold" :min="600" :max="900" />
              <div class="form-tip">评分 ≥ 该值判定为低风险（绿色），可直接授信</div>
            </el-form-item>
            <el-form-item label="高风险阈值（分）">
              <el-input-number v-model="thresholds.highRiskThreshold" :min="300" :max="600" />
              <div class="form-tip">评分 &lt; 该值判定为高风险（红色），建议暂缓/拒贷</div>
            </el-form-item>
            <el-form-item label="基准利率（%）">
              <el-input-number v-model="thresholds.baseRate" :min="0" :max="20" :step="0.1" />
            </el-form-item>
            <el-form-item label="风险溢价系数">
              <el-input-number v-model="thresholds.riskPremiumFactor" :min="0" :max="20" :step="0.5" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="handleSaveThresholds">保存阈值</el-button>
              <el-button @click="load">重置</el-button>
            </el-form-item>
          </el-form>
          <el-alert type="info" :closable="false" style="margin-top: 4px">
            <div class="form-tip">{{ levelHint }}</div>
            <div class="form-tip" style="margin-top: 4px">{{ rateHint }}</div>
          </el-alert>
        </div>
      </el-col>

      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">系统参数</h3>
          <el-table v-loading="loading" :data="configs" size="default">
            <el-table-column label="配置项" min-width="200">
              <template #default="{ row }">
                <div style="font-weight: 600">
                  {{ row.key }}
                  <el-tag size="small" effect="plain" style="margin-left: 6px">{{
                    CONFIG_GROUP[row.key] || '其他'
                  }}</el-tag>
                </div>
                <div style="font-size: 12px; color: #909399; margin-top: 2px">
                  {{ CONFIG_DESC[row.key] || row.description || '—' }}
                </div>
              </template>
            </el-table-column>
            <el-table-column label="值" width="170">
              <template #default="{ row }">
                <el-input v-model="row.value" @change="saveConfig(row)" />
              </template>
            </el-table-column>
            <el-table-column label="更新时间" width="110">
              <template #default="{ row }">
                <span style="font-size: 12px; color: #909399">
                  {{ row.updatedAt ? String(row.updatedAt).slice(0, 16) : '—' }}
                </span>
              </template>
            </el-table-column>
          </el-table>
          <div class="form-tip" style="margin-top: 10px">修改后自动保存；风险评估阈值与利率建议统一在左侧管理</div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.form-tip {
  font-size: 12px;
  color: #606266;
  line-height: 1.6;
}
</style>
