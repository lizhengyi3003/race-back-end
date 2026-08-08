<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'
import StatCard from '@/components/StatCard.vue'
import { getSystemOverview } from '@/api/admin'
import { getIndustryDistribution, getScoreDistribution, getTrend } from '@/api/risk'
import { getServerStatus, getHealth } from '@/api/monitor'

const overview = ref<any>(null)
const server = ref<any>(null)
const health = ref<any>(null)

const trendChartRef = ref<HTMLElement>()
const scoreChartRef = ref<HTMLElement>()
const industryChartRef = ref<HTMLElement>()

// 图表实例复用：避免每次 dispose+init 导致重绘异常 / 画布重叠
const chartInstances = new Map<string, echarts.ECharts>()
let timer: any = null

function getChart(key: string, el?: HTMLElement): echarts.ECharts | null {
  if (!el) return null
  let chart = chartInstances.get(key)
  if (!chart) {
    chart = echarts.init(el)
    chartInstances.set(key, chart)
  }
  return chart
}

function fmtTime(sec: number): string {
  const d = Math.floor(sec / 86400)
  const h = Math.floor((sec % 86400) / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return d > 0 ? `${d}天${h}小时` : `${h}小时${m}分`
}

function renderTrend(data: any[]) {
  const chart = getChart('trend', trendChartRef.value)
  if (!chart) return
  chart.setOption(
    {
      tooltip: { trigger: 'axis' },
      legend: { data: ['评估次数', '平均评分'], top: 0, itemWidth: 16, itemHeight: 10, textStyle: { fontSize: 12 } },
      grid: { top: 42, right: 44, bottom: 48, left: 52 },
      xAxis: {
        type: 'category',
        data: data.map((d) => d.date.slice(5)),
        axisLabel: { fontSize: 11, color: '#909399', interval: 0, rotate: 30 },
        axisLine: { lineStyle: { color: '#dcdfe6' } },
      },
      yAxis: [
        {
          type: 'value',
          name: '次数',
          minInterval: 1,
          nameTextStyle: { color: '#909399', fontSize: 11 },
          splitLine: { lineStyle: { color: '#f0f2f5' } },
        },
        {
          type: 'value',
          name: '评分',
          min: 0,
          max: 1000,
          nameTextStyle: { color: '#909399', fontSize: 11 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '评估次数',
          type: 'line',
          smooth: true,
          data: data.map((d) => d.count),
          itemStyle: { color: '#2c6e49' },
          lineStyle: { width: 2 },
          symbolSize: 6,
          areaStyle: { opacity: 0.15 },
        },
        {
          // 无记录的日期用 null，避免平均评分线在 0 处与次数线重叠
          name: '平均评分',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          data: data.map((d) => (d.count > 0 ? d.avgScore : null)),
          itemStyle: { color: '#e6a23c' },
          lineStyle: { width: 2 },
          symbolSize: 6,
          connectNulls: false,
        },
      ],
    },
    { notMerge: true }
  )
}

function renderScoreDist(data: any[]) {
  const chart = getChart('score', scoreChartRef.value)
  if (!chart) return
  chart.setOption(
    {
      tooltip: { trigger: 'axis' },
      grid: { top: 20, right: 20, bottom: 30, left: 50 },
      xAxis: { type: 'category', data: data.map((d) => d.range), axisLabel: { fontSize: 11, color: '#909399' } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f0f2f5' } } },
      series: [
        {
          type: 'bar',
          data: data.map((d) => ({
            value: d.count,
            itemStyle: {
              color: d.range.includes('800')
                ? '#67c23a'
                : d.range.includes('700') || d.range.includes('600')
                  ? '#e6a23c'
                  : '#f56c6c',
              borderRadius: [4, 4, 0, 0],
            },
          })),
          barWidth: 30,
        },
      ],
    },
    { notMerge: true }
  )
}

function renderIndustry(data: any[]) {
  const chart = getChart('industry', industryChartRef.value)
  if (!chart) return
  chart.setOption(
    {
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0 },
      series: [
        {
          type: 'pie',
          radius: ['40%', '68%'],
          center: ['50%', '46%'],
          data: data.map((d) => ({ name: d.name, value: d.value })),
          label: { formatter: '{b}\n{d}%' },
          itemStyle: { borderRadius: 6 },
        },
      ],
    },
    { notMerge: true }
  )
}

async function load() {
  // 各接口独立容错：单个接口失败不影响其他数据的刷新
  const [ov, srv, hlt] = await Promise.allSettled([getSystemOverview(), getServerStatus(), getHealth()])
  if (ov.status === 'fulfilled') overview.value = ov.value
  if (srv.status === 'fulfilled') server.value = srv.value
  if (hlt.status === 'fulfilled') health.value = hlt.value

  // 图表数据（单个失败时保留上次渲染）
  try {
    const [industry, scoreDist, trend] = await Promise.all([
      getIndustryDistribution(),
      getScoreDistribution(),
      getTrend(14),
    ])
    renderIndustry(industry)
    renderScoreDist(scoreDist)
    renderTrend(trend)
    chartInstances.forEach((c) => c.resize())
  } catch {
    // 忽略
  }
}

function handleResize() {
  chartInstances.forEach((c) => c.resize())
}

onMounted(() => {
  load()
  timer = setInterval(load, 10000)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  window.removeEventListener('resize', handleResize)
  chartInstances.forEach((c) => c.dispose())
  chartInstances.clear()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>系统概览</h1>
      <p>涉农信贷风控后端 · 全平台运行状态（每 10 秒自动刷新）</p>
    </div>

    <div class="metric-grid">
      <StatCard title="用户数" :value="overview?.users ?? '-'" icon="User" color="#2c6e49" />
      <StatCard title="评估记录" :value="overview?.records ?? '-'" unit="条" icon="Document" color="#4c956c" />
      <StatCard title="模型版本" :value="overview?.models ?? '-'" unit="个" icon="Cpu" color="#4361ee" />
      <StatCard
        title="API 调用（今日）"
        :value="overview?.apiLogsToday ?? '-'"
        unit="次"
        icon="Connection"
        color="#e76f51"
      />
      <StatCard title="CPU 使用率" :value="server ? server.cpu.percent + '%' : '-'" icon="Monitor" color="#e6a23c" />
      <StatCard title="内存使用率" :value="server ? server.memory.percent + '%' : '-'" icon="Coin" color="#9b5de5" />
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">近 14 天评估趋势</h3>
          <div ref="trendChartRef" style="width: 100%; height: 320px" />
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">信用评分分布</h3>
          <div ref="scoreChartRef" style="width: 100%; height: 320px" />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">行业分布</h3>
          <div ref="industryChartRef" style="width: 100%; height: 300px" />
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">服务健康</h3>
          <div class="health-grid">
            <div
              v-for="item in [
                { label: '后端服务', value: health?.service, ok: health?.service === 'ok' },
                { label: '数据库', value: health?.database, ok: health?.database === 'ok' },
                {
                  label: '信用模型',
                  value: health?.modelExists ? `已加载 ${health?.modelVersion}` : '未加载',
                  ok: health?.modelExists,
                },
              ]"
              :key="item.label"
              class="health-item"
            >
              <el-icon :size="20" :color="item.ok ? '#67c23a' : '#f56c6c'">
                <CircleCheckFilled v-if="item.ok" />
                <CircleCloseFilled v-else />
              </el-icon>
              <div>
                <div class="health-label">{{ item.label }}</div>
                <div class="health-value" :style="{ color: item.ok ? '#67c23a' : '#f56c6c' }">{{ item.value }}</div>
              </div>
            </div>
            <div class="health-item">
              <el-icon :size="20" color="#2c6e49"><Timer /></el-icon>
              <div>
                <div class="health-label">运行时长</div>
                <div class="health-value">{{ server ? fmtTime(server.uptimeSeconds) : '-' }}</div>
              </div>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.health-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;

  .health-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 14px;
    background: #f7f9fb;
    border-radius: 8px;

    .health-label {
      font-size: 12px;
      color: #909399;
    }

    .health-value {
      font-size: 15px;
      font-weight: 600;
      color: #303133;
    }
  }
}
</style>
