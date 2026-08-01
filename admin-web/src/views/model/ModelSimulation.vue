<script setup lang="ts">
import { onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { runSimulation } from '@/api/model'

const loading = ref(false)
const result = ref<any>(null)
const barChartRef = ref<HTMLElement>()
let barChart: echarts.ECharts | null = null

async function load() {
  loading.value = true
  try {
    result.value = await runSimulation(2000)
    renderChart()
  } catch (e: any) {
    ElMessage.error(e.message || '仿真失败')
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!result.value?.scenarios?.length) return
  if (!barChartRef.value) return
  if (!barChart) barChart = echarts.init(barChartRef.value)
  const names = result.value.scenarios.map((s: any) => s.name)
  const baseline = result.value.scenarios.map((s: any) => s.baseline.avgScore)
  const after = result.value.scenarios.map((s: any) => s.after.avgScore)
  barChart.setOption(
    {
      tooltip: { trigger: 'axis' },
      legend: {
        data: ['基线平均分', '场景冲击后平均分'],
        top: 0,
        itemWidth: 18,
        itemHeight: 10,
        textStyle: { fontSize: 12 },
      },
      grid: { top: 52, right: 24, bottom: 32, left: 56 },
      xAxis: { type: 'category', data: names, axisLabel: { fontSize: 12 } },
      yAxis: { type: 'value', name: '平均分', min: 0, max: 1000, nameTextStyle: { fontSize: 12 } },
      series: [
        {
          name: '基线平均分',
          type: 'bar',
          data: baseline,
          itemStyle: { color: '#4c956c', borderRadius: [4, 4, 0, 0] },
          barWidth: 26,
        },
        {
          name: '场景冲击后平均分',
          type: 'bar',
          data: after,
          itemStyle: { color: '#e76f51', borderRadius: [4, 4, 0, 0] },
          barWidth: 26,
        },
      ],
    },
    { notMerge: true }
  )
}

function fmtDelta(v: number): string {
  return (v > 0 ? '+' : '') + v
}

function rankTag(name: string): 'danger' | 'warning' | 'info' {
  if (name === '突发灾情' || name === '干旱减产') return 'danger'
  return 'warning'
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>业务仿真验证</h1>
      <p>极端场景模拟（干旱减产 / 粮价下跌 / 补贴退坡 / 突发灾情）— 验证模型在非正常年份下的可靠性</p>
    </div>

    <div class="info-card" style="margin-bottom: 16px">
      <div class="toolbar">
        <el-tag v-if="result" type="primary"
          >{{ result.nSamples }} 个样本 · 当前模型 {{ result.modelVersion || result.thresholds ? '' : '' }}</el-tag
        >
        <div style="flex: 1" />
        <el-button type="primary" :loading="loading" @click="load">重新仿真</el-button>
      </div>
      <div class="form-tip">
        仿真逻辑：对样本施加各极端场景的业务冲击（如干旱减产 →
        理赔次数/占比上升、收入下滑），重新评分后对比客群风险变化。
      </div>
    </div>

    <div class="info-card" style="margin-bottom: 16px">
      <h3 class="card-title">场景冲击前后平均分对比</h3>
      <div ref="barChartRef" style="width: 100%; height: 320px" />
    </div>

    <el-row v-if="result?.scenarios" :gutter="16">
      <el-col v-for="s in result.scenarios" :key="s.name" :span="12" style="margin-bottom: 16px">
        <div class="info-card scenario-card">
          <div class="scenario-header">
            <el-icon :size="22" :color="s.color"><component :is="s.icon || 'Warning'" /></el-icon>
            <div>
              <h3 style="margin: 0">{{ s.name }}</h3>
              <div class="form-tip" style="margin-top: 4px">{{ s.desc }}</div>
            </div>
            <el-tag :type="rankTag(s.name)" size="small" style="margin-left: auto"
              >高风险率 Δ{{ fmtDelta(s.highRiskDelta) }}pp</el-tag
            >
          </div>

          <el-descriptions :column="3" border size="small" style="margin-top: 14px">
            <el-descriptions-item label="平均分">
              {{ s.baseline.avgScore }} → <span style="color: #e76f51; font-weight: 600">{{ s.after.avgScore }}</span>
              <span class="delta">({{ fmtDelta(s.avgScoreDelta) }})</span>
            </el-descriptions-item>
            <el-descriptions-item label="高风险率">
              {{ s.baseline.highRiskRate }}% →
              <span style="color: #e76f51; font-weight: 600">{{ s.after.highRiskRate }}%</span>
            </el-descriptions-item>
            <el-descriptions-item label="升高风险">
              <span style="font-weight: 600">{{ s.migrateToHigh }}</span> / {{ s.nSamples }} 户
            </el-descriptions-item>
          </el-descriptions>

          <div class="risk-progress">
            <div class="risk-progress-head">
              <span class="risk-progress-label">场景后高风险占比</span>
              <span
                class="risk-progress-value"
                :style="{
                  color: s.after.highRiskRate > 60 ? '#f56c6c' : s.after.highRiskRate > 30 ? '#e6a23c' : '#67c23a',
                }"
              >
                {{ s.after.highRiskRate }}%
              </span>
            </div>
            <el-progress
              :percentage="Math.round(s.after.highRiskRate)"
              :stroke-width="10"
              :show-text="false"
              :color="s.after.highRiskRate > 60 ? '#f56c6c' : s.after.highRiskRate > 30 ? '#e6a23c' : '#67c23a'"
            />
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.form-tip {
  font-size: 12px;
  color: #909399;
}

.scenario-card {
  .scenario-header {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .delta {
    font-size: 12px;
    color: #909399;
  }

  .risk-progress {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid #f0f2f5;

    .risk-progress-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }

    .risk-progress-label {
      font-size: 12px;
      color: #909399;
    }

    .risk-progress-value {
      font-size: 13px;
      font-weight: 600;
    }
  }
}
</style>
