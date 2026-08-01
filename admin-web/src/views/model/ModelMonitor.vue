<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { getModelMonitor } from '@/api/model'

const monitor = ref<any>(null)
const loading = ref(false)
const trendChartRef = ref<HTMLElement>()
let trendChart: echarts.ECharts | null = null

const hasTrendData = computed(() => monitor.value?.trend?.some((d: any) => d.count > 0) ?? false)

async function load() {
  loading.value = true
  try {
    monitor.value = await getModelMonitor()
    // 等待 DOM 更新（图表容器由 v-show 控制、始终在 DOM 中，此处仍需 nextTick 保证渲染）
    await nextTick()
    renderChart()
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!monitor.value?.trend?.length) return
  if (!trendChartRef.value) return
  if (!trendChart) trendChart = echarts.init(trendChartRef.value)
  const data = monitor.value.trend
  trendChart.setOption(
    {
      tooltip: { trigger: 'axis' },
      // 图例显式水平居中布局，拉开间距，避免两项文字重叠或被挤压
      legend: {
        data: ['评估次数', '平均评分'],
        top: 0,
        left: 'center',
        itemGap: 32,
        itemWidth: 14,
        itemHeight: 14,
        textStyle: { fontSize: 12 },
      },
      grid: { top: 55, right: 50, bottom: 45, left: 55 },
      xAxis: {
        type: 'category',
        data: data.map((d: any) => d.date.slice(5)),
        // interval:'auto' 让 echarts 自动跳过重叠标签（30 个日期全显示会互相重叠），rotate 45° 更清晰
        axisLabel: { interval: 'auto', rotate: 45, fontSize: 10 },
      },
      // 两个 y 轴明确分左右，避免轴名"次数/平均分"在左侧重叠
      yAxis: [
        { type: 'value', name: '次数', position: 'left', minInterval: 1, nameTextStyle: { padding: [0, 0, 0, 0] } },
        {
          type: 'value',
          name: '平均分',
          position: 'right',
          min: 0,
          max: 1000,
          nameTextStyle: { padding: [0, 0, 0, 0] },
        },
      ],
      series: [
        {
          name: '评估次数',
          type: 'bar',
          data: data.map((d: any) => d.count),
          itemStyle: { color: '#4c956c', borderRadius: [4, 4, 0, 0] },
          barWidth: 16,
        },
        {
          name: '平均评分',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          data: data.map((d: any) => (d.count > 0 ? d.avgScore : null)),
          itemStyle: { color: '#e6a23c' },
        },
      ],
    },
    { notMerge: true }
  )
}

function psiLevel(psi?: number) {
  // 样本不足时 PSI 不可靠，不做判定
  if (monitor.value?.actualSamples != null && monitor.value.actualSamples < 30) {
    return { type: 'info' as const, text: `样本不足（${monitor.value.actualSamples} 条）` }
  }
  if (psi == null) return { type: 'info' as const, text: '暂无数据' }
  if (psi > 0.1) return { type: 'danger' as const, text: `${psi}（显著偏移）` }
  if (psi > 0.05) return { type: 'warning' as const, text: `${psi}（轻微偏移）` }
  return { type: 'success' as const, text: `${psi}（稳定）` }
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>模型监控</h1>
      <p>PSI 群体稳定性 · 客群迁移预警 · 模型再校准触发（对齐计划书 3.3.1 监控与迭代机制）</p>
    </div>

    <div v-if="monitor?.available">
      <div class="metric-grid">
        <div class="info-card mini-card">
          <div class="label">当前模型</div>
          <div class="value">{{ monitor.modelVersion }}</div>
        </div>
        <div class="info-card mini-card">
          <div class="label">PSI 群体稳定性</div>
          <div class="value">
            <el-tag :type="psiLevel(monitor.psi).type" size="large">{{ psiLevel(monitor.psi).text }}</el-tag>
          </div>
        </div>
        <div class="info-card mini-card">
          <div class="label">实际客群样本</div>
          <div class="value">{{ monitor.actualSamples }} 条</div>
        </div>
        <div class="info-card mini-card">
          <div class="label">客群平均分</div>
          <div class="value">{{ monitor.actualAvgScore ?? '-' }}</div>
        </div>
        <div class="info-card mini-card">
          <div class="label">实际高风险率</div>
          <div class="value" :style="{ color: monitor.highRiskRate > 30 ? '#f56c6c' : '#67c23a' }">
            {{ monitor.highRiskRate }}%
          </div>
        </div>
      </div>

      <div class="info-card" style="margin-bottom: 16px">
        <h3 class="card-title">监控预警</h3>
        <template v-if="monitor.warnings?.length">
          <el-alert
            v-for="(w, i) in monitor.warnings"
            :key="i"
            :title="w"
            type="warning"
            :closable="false"
            style="margin-bottom: 10px"
          />
          <div class="form-tip">
            提示：当 PSI &gt; 0.1 或客群风险显著上升时，建议在「模型训练与评估」页触发模型再校准。
          </div>
        </template>
        <el-empty v-else description="当前无预警，客群分布稳定" :image-size="80" />
      </div>

      <div class="info-card" style="margin-bottom: 16px">
        <h3 class="card-title">近 30 天实际客群趋势</h3>
        <div v-show="hasTrendData" ref="trendChartRef" style="width: 100%; height: 320px" />
        <el-empty v-if="!hasTrendData" description="暂无评估记录，持续积累数据后将自动展示客群趋势" :image-size="80" />
        <div class="form-tip" style="margin-top: 8px">
          说明：趋势数据来自真实评估记录（当前
          {{ monitor?.actualSamples ?? 0 }} 条）。随着试点使用积累，评分分布与高风险率趋势将逐渐清晰，PSI
          监控也将随之生效。
        </div>
      </div>
    </div>

    <el-empty v-else-if="!loading" :description="monitor?.message || '暂无监控数据'" />
  </div>
</template>

<style scoped lang="scss">
.mini-card {
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

.form-tip {
  font-size: 12px;
  color: #909399;
}
</style>
