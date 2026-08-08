<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import * as echarts from 'echarts'
import StatCard from '@/components/StatCard.vue'
import { getServerStatus, type ServerStatus } from '@/api/monitor'

const server = ref<ServerStatus | null>(null)
const loading = ref(false)

const cpuChartRef = ref<HTMLElement>()
const memChartRef = ref<HTMLElement>()
let cpuChart: echarts.ECharts | null = null
let memChart: echarts.ECharts | null = null

const cpuHistory: { time: string; value: number }[] = []
const memHistory: { time: string; value: number }[] = []
let timer: any = null

function fmtUptime(sec: number): string {
  const d = Math.floor(sec / 86400)
  const h = Math.floor((sec % 86400) / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = Math.floor(sec % 60)
  return `${d}天 ${h}时 ${m}分 ${s}秒`
}

function renderLine(
  chart: echarts.ECharts | null,
  data: { time: string; value: number }[],
  name: string,
  color: string,
  max: number,
  unit: string
) {
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 30, right: 20, bottom: 24, left: 40 },
    xAxis: { type: 'category', data: data.map((d) => d.time), boundaryGap: false },
    yAxis: { type: 'value', max, axisLabel: { formatter: `{value}${unit}` } },
    series: [
      {
        name,
        type: 'line',
        data: data.map((d) => d.value),
        smooth: true,
        showSymbol: false,
        lineStyle: { color, width: 2 },
        areaStyle: { color, opacity: 0.1 },
      },
    ],
  })
}

async function load() {
  loading.value = true
  try {
    server.value = await getServerStatus()
    const now = new Date().toLocaleTimeString()
    cpuHistory.push({ time: now, value: server.value.cpu.percent })
    memHistory.push({ time: now, value: server.value.memory.percent })
    if (cpuHistory.length > 30) cpuHistory.shift()
    if (memHistory.length > 30) memHistory.shift()

    if (!cpuChart && cpuChartRef.value) cpuChart = echarts.init(cpuChartRef.value)
    if (!memChart && memChartRef.value) memChart = echarts.init(memChartRef.value)
    renderLine(cpuChart, cpuHistory, 'CPU 使用率', '#4361ee', 100, '%')
    renderLine(memChart, memHistory, '内存使用率', '#9b5de5', 100, '%')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  timer = setInterval(load, 3000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
  cpuChart?.dispose()
  memChart?.dispose()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>服务器状态</h1>
      <p>CPU / 内存 / 磁盘实时监控（每 3 秒自动刷新）</p>
    </div>

    <div class="metric-grid">
      <StatCard title="CPU 使用率" :value="server ? server.cpu.percent + '%' : '-'" icon="Cpu" color="#4361ee" />
      <StatCard title="内存使用率" :value="server ? server.memory.percent + '%' : '-'" icon="Coin" color="#9b5de5" />
      <StatCard
        title="磁盘使用率"
        :value="server ? server.disk.percent + '%' : '-'"
        icon="FolderOpened"
        color="#e76f51"
      />
      <StatCard title="进程内存" :value="server ? server.processMemory + ' MB' : '-'" icon="DataLine" color="#e6a23c" />
      <StatCard title="线程数" :value="server?.threads ?? '-'" icon="Share" color="#2c6e49" />
      <StatCard title="CPU 核心" :value="server?.cpu.cores ?? '-'" icon="Monitor" color="#4c956c" />
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">CPU 使用率趋势</h3>
          <div ref="cpuChartRef" style="width: 100%; height: 300px" />
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">内存使用率趋势</h3>
          <div ref="memChartRef" style="width: 100%; height: 300px" />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">资源详情</h3>
          <el-descriptions v-if="server" :column="2" border>
            <el-descriptions-item label="主机名">{{ server.hostname }}</el-descriptions-item>
            <el-descriptions-item label="系统">{{ server.platform }}</el-descriptions-item>
            <el-descriptions-item label="Python">{{ server.pythonVersion }}</el-descriptions-item>
            <el-descriptions-item label="CPU 频率">{{
              server.cpu.freq ? server.cpu.freq + ' MHz' : '-'
            }}</el-descriptions-item>
            <el-descriptions-item label="运行时长">{{ fmtUptime(server.uptimeSeconds) }}</el-descriptions-item>
            <el-descriptions-item label="启动时间">{{
              server.bootTime?.replace('T', ' ').slice(0, 19)
            }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">内存与磁盘</h3>
          <template v-if="server">
            <div class="bar-item">
              <div class="bar-label">内存：{{ server.memory.used }} / {{ server.memory.total }} MB</div>
              <el-progress
                :percentage="Math.round(server.memory.percent)"
                :stroke-width="18"
                :color="server.memory.percent > 85 ? '#f56c6c' : '#4c956c'"
              />
            </div>
            <div class="bar-item">
              <div class="bar-label">磁盘：{{ server.disk.used }} / {{ server.disk.total }} GB</div>
              <el-progress
                :percentage="Math.round(server.disk.percent)"
                :stroke-width="18"
                :color="server.disk.percent > 85 ? '#f56c6c' : '#e6a23c'"
              />
            </div>
            <div class="bar-item">
              <div class="bar-label">进程 CPU：{{ server.processCpu }}%</div>
              <el-progress
                :percentage="Math.min(100, Math.round(server.processCpu))"
                :stroke-width="18"
                color="#4361ee"
              />
            </div>
          </template>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.bar-item {
  margin-bottom: 18px;

  .bar-label {
    font-size: 13px;
    color: #606266;
    margin-bottom: 6px;
  }
}
</style>
