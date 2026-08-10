<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import StatCard from '@/components/StatCard.vue'
import { getModelInfo, getModelMetrics, trainModel, type ModelInfo, type ModelMetrics } from '@/api/model'

const info = ref<ModelInfo | null>(null)
const metrics = ref<ModelMetrics | null>(null)
const training = ref(false)
const nSamples = ref<number | undefined>(undefined)

const cvMean = computed(() => {
  const s = metrics.value?.cvScores
  if (!s || !s.length) return 0
  return s.reduce((a, b) => a + b, 0) / s.length
})
const cvStr = computed(() => metrics.value?.cvScores?.map((s) => s.toFixed(4)).join('，') || '')

// 三组对比实验（对齐计划书 3.3.3）
const experiments = computed(() => {
  const ex = metrics.value?.experiments as any
  if (!ex) return []
  return [
    { title: '实验一 · 替代数据指标体系有效性验证', desc: ex.experiment1?.desc, groups: ex.experiment1?.groups },
    { title: '实验二 · 特征工程方案对比', desc: ex.experiment2?.desc, groups: ex.experiment2?.groups },
    { title: '实验三 · 涉农专属模型 vs 通用风控模型', desc: ex.experiment3?.desc, groups: ex.experiment3?.groups },
  ]
})

const rocChartRef = ref<HTMLElement>()
const ksChartRef = ref<HTMLElement>()
const ivChartRef = ref<HTMLElement>()

// 混淆矩阵（HTML 网格展示，避免 heatmap 渲染问题）
const cmDisplay = computed(() => {
  const cm = metrics.value?.confusionMatrix
  if (!cm || cm.length !== 2 || !cm[0]?.length) return null
  const labels = ['非违约', '违约']
  const cell = (actual: number, pred: number, name: string) => ({
    actual: labels[actual],
    pred: labels[pred],
    value: cm[actual][pred],
    name,
    color: actual === pred ? '#2c6e49' : '#f56c6c',
  })
  return [cell(0, 0, 'TN · 正确拒绝'), cell(0, 1, 'FP · 误判'), cell(1, 0, 'FN · 漏判'), cell(1, 1, 'TP · 正确识别')]
})

let charts: echarts.ECharts[] = []

function disposeCharts() {
  charts.forEach((c) => c.dispose())
  charts = []
}

function renderCharts() {
  if (!metrics.value) return
  disposeCharts()

  // ROC
  if (rocChartRef.value && metrics.value.rocCurve) {
    const chart = echarts.init(rocChartRef.value)
    charts.push(chart)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { top: 20, right: 20, bottom: 40, left: 50 },
      xAxis: { type: 'value', name: 'FPR', min: 0, max: 1 },
      yAxis: { type: 'value', name: 'TPR', min: 0, max: 1 },
      series: [
        {
          type: 'line',
          data: metrics.value.rocCurve.map((p) => [p.fpr, p.tpr]),
          smooth: true,
          showSymbol: false,
          lineStyle: { color: '#2c6e49', width: 2 },
        },
        {
          type: 'line',
          data: [
            [0, 0],
            [1, 1],
          ],
          showSymbol: false,
          lineStyle: { color: '#c0c4cc', type: 'dashed' },
          silent: true,
        },
      ],
    })
  }

  // KS
  if (ksChartRef.value && metrics.value.ksCurve) {
    const chart = echarts.init(ksChartRef.value)
    charts.push(chart)
    const data = metrics.value.ksCurve
    chart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['TPR', 'FPR', '差值'] },
      grid: { top: 40, right: 20, bottom: 40, left: 50 },
      xAxis: {
        type: 'category',
        data: data.map((p) => (p.threshold != null ? p.threshold.toFixed(2) : '')),
        axisLabel: { show: false },
      },
      yAxis: { type: 'value' },
      series: [
        { name: 'TPR', type: 'line', data: data.map((p) => p.tpr), showSymbol: false },
        { name: 'FPR', type: 'line', data: data.map((p) => p.fpr), showSymbol: false },
        {
          name: '差值',
          type: 'line',
          data: data.map((p) => p.diff),
          showSymbol: false,
          lineStyle: { color: '#e6a23c' },
        },
      ],
    })
  }

  // IV 条形图
  if (ivChartRef.value && metrics.value.ivTable) {
    const chart = echarts.init(ivChartRef.value)
    charts.push(chart)
    const sorted = [...metrics.value.ivTable].sort((a, b) => a.iv - b.iv)
    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { top: 20, right: 30, bottom: 20, left: 120 },
      xAxis: { type: 'value', name: 'IV' },
      yAxis: { type: 'category', data: sorted.map((d) => d.factor) },
      series: [
        {
          type: 'bar',
          data: sorted.map((d) => ({
            value: d.iv,
            itemStyle: {
              color: d.iv >= 0.1 ? '#67c23a' : d.iv >= 0.02 ? '#e6a23c' : '#909399',
              borderRadius: [0, 4, 4, 0],
            },
          })),
          label: { show: true, position: 'right', formatter: '{c}' },
          barWidth: 18,
        },
      ],
    })
  }
}

async function load() {
  info.value = await getModelInfo()
  metrics.value = await getModelMetrics()
  // 等待 DOM 与布局完成：图表容器位于 el-col 中，宽度依赖布局计算，
  // 缺 nextTick 时 echarts.init 可能以 0 宽初始化，导致 ROC/KS 曲线图空白
  await nextTick()
  renderCharts()
}

function resizeCharts() {
  charts.forEach((c) => c.resize())
}

async function doTrain() {
  training.value = true
  try {
    await trainModel(nSamples.value)
    ElMessage.success('训练完成')
    await load()
  } finally {
    training.value = false
  }
}

onMounted(() => {
  window.addEventListener('resize', resizeCharts)
  load()
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  disposeCharts()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>模型训练与评估</h1>
      <p>数据层评分卡（多元统计参考模型）训练与评估；线上评估由动态专家引擎执行</p>
    </div>

    <el-alert type="info" :closable="false" style="margin-bottom: 16px">
      <div class="form-tip">
        <b>模型体系说明：</b>线上评估主路径为「动态专家引擎」（四层动态指标体系 → 专家评分 →
        混合经营加权，含一票否决红线）； 本页管理的数据层评分卡为多元统计参考模型（IV 特征筛选 → WOE 编码 → Logistic
        回归）。模型训练后注册为数据层模型，在线上评估中当提交指标含其已知特征（≥2 项）时参与风险混合——数据层打分落入训练群体
        最差 15% 客群触发高风险下修、最优 15% 客群轻度上修，中间带保持专家分权威。
      </div>
    </el-alert>

    <div class="info-card" style="margin-bottom: 16px">
      <div class="toolbar">
        <div>
          <el-tag v-if="info" type="success" style="margin-right: 8px">当前模型 {{ info.version }}</el-tag>
          <el-tag v-if="info" type="info">{{ info.nSamples }} 样本 · {{ info.nFeatures }} 特征</el-tag>
        </div>
        <div style="flex: 1" />
        <el-input-number
          v-model="nSamples"
          :min="1000"
          :max="20000"
          :step="1000"
          placeholder="样本量"
          style="width: 160px"
        />
        <el-button type="primary" :loading="training" @click="doTrain">开始训练</el-button>
      </div>
      <div class="form-tip">
        训练数据：真实微观调查数据融合（CHFS + CMES + CFPS，约 9.3 万样本）→ 可解释风险因子合成违约标签（违约率约 5%，
        A+B 双标签：A 主标签入模、B 真实负面信号做排序一致性验证）；训练流程为 IV 特征筛选 → WOE 编码 → SMOTE
        过采样 → Logistic 回归 + 5 折交叉验证。
      </div>
    </div>

    <div class="metric-grid">
      <StatCard
        title="AUC"
        :value="metrics?.auc != null ? metrics.auc.toFixed(4) : '-'"
        icon="TrendCharts"
        color="#2c6e49"
        desc="排序区分度：0.5=随机、1=完美。违约标签为合成，指标偏乐观；真实区分力参考 B 验证（真实负面信号 Spearman 一致性）。参考价值：中"
      />
      <StatCard
        title="KS"
        :value="metrics?.ks != null ? metrics.ks.toFixed(4) : '-'"
        icon="DataLine"
        color="#4361ee"
        desc="好坏客群累计分布最大差距：&gt;0.3 可接受、&gt;0.5 良好。同受合成标签影响。参考价值：中"
      />
      <StatCard
        title="召回率"
        :value="metrics?.recall != null ? (metrics.recall * 100).toFixed(1) + '%' : '-'"
        icon="CircleCheck"
        color="#67c23a"
        desc="真实违约户中被识别出的比例。依赖分类阈值，换阈值即变，且基于合成标签。参考价值：低"
      />
      <StatCard
        title="精确率"
        :value="metrics?.precision != null ? (metrics.precision * 100).toFixed(1) + '%' : '-'"
        icon="Aim"
        color="#e76f51"
        desc="判为违约的客群中确违约的比例，远超整体违约率即有甄别力。依赖阈值。参考价值：低-中"
      />
      <StatCard
        title="F1"
        :value="metrics?.f1 != null ? metrics.f1.toFixed(4) : '-'"
        icon="Star"
        color="#9b5de5"
        desc="召回与精确的调和平均，兼顾抓全与抓准。依赖阈值。参考价值：低"
      />
      <StatCard
        title="PSI"
        :value="metrics ? (metrics.psi ?? 0).toFixed(4) : '-'"
        icon="Odometer"
        color="#e6a23c"
        desc="训练/测试评分分布漂移，&lt;0.1 无漂移。不依赖标签、可信度高。参考价值：高"
      />
    </div>

    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">ROC 曲线（AUC={{ metrics?.auc?.toFixed(4) }})</h3>
          <div ref="rocChartRef" style="width: 100%; height: 300px" />
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">KS 曲线（KS={{ metrics?.ks?.toFixed(4) }})</h3>
          <div ref="ksChartRef" style="width: 100%; height: 300px" />
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">混淆矩阵</h3>
          <div v-if="cmDisplay" class="cm-grid">
            <div class="cm-cell cm-corner"></div>
            <div class="cm-cell cm-head">预测：非违约</div>
            <div class="cm-cell cm-head">预测：违约</div>
            <div class="cm-cell cm-rownum">实际：非违约</div>
            <div
              v-for="c in cmDisplay.slice(0, 2)"
              :key="c.name"
              class="cm-cell cm-value"
              :style="{ background: c.color }"
            >
              <div class="cm-num">{{ c.value }}</div>
              <div class="cm-name">{{ c.name }}</div>
            </div>
            <div class="cm-cell cm-rownum">实际：违约</div>
            <div
              v-for="c in cmDisplay.slice(2, 4)"
              :key="c.name"
              class="cm-cell cm-value"
              :style="{ background: c.color }"
            >
              <div class="cm-num">{{ c.value }}</div>
              <div class="cm-name">{{ c.name }}</div>
            </div>
          </div>
          <div v-if="cmDisplay" class="cm-legend">
            <span><i class="dot" style="background: #2c6e49"></i>预测正确（TN/TP）</span>
            <span><i class="dot" style="background: #f56c6c"></i>预测错误（FP/FN）</span>
          </div>
        </div>
      </el-col>
      <el-col :xs="24" :md="12">
        <div class="info-card">
          <h3 class="card-title">评分卡特征 IV 值（特征筛选）</h3>
          <div ref="ivChartRef" style="width: 100%; height: 280px" />
          <div class="form-tip">
            IV 值为数据层评分卡入模特征（替代数据指标）的筛选依据：IV ≥ 0.1 强预测力、0.02~0.1 中等、&lt; 0.02 剔除。
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="info-card" style="margin-top: 16px">
      <h3 class="card-title">5 折交叉验证 AUC</h3>
      <el-progress
        v-if="metrics?.cvScores?.length"
        :percentage="Math.round(cvMean * 100)"
        :format="() => `均值 ${cvMean.toFixed(4)}`"
        :stroke-width="18"
        color="#4c956c"
      />
      <div v-if="metrics?.cvScores" class="form-tip" style="margin-top: 8px">各折：{{ cvStr }}</div>
      <div v-if="metrics?.featureNames" class="form-tip">
        评分卡入模特征（{{ metrics?.featureNames?.length }} 项）：{{ metrics?.featureNames?.join('，') }}
      </div>
    </div>

    <!-- 三组对比实验（对齐计划书 3.3.3）-->
    <div v-for="ex in experiments" :key="ex.title" class="info-card" style="margin-top: 16px">
      <h3 class="card-title">{{ ex.title }}</h3>
      <div class="form-tip" style="margin-bottom: 10px">{{ ex.desc }}</div>
      <el-table :data="Object.entries(ex.groups || {}).map(([name, g]: any) => ({ name, ...g }))" size="small">
        <el-table-column prop="name" label="方案" min-width="180">
          <template #default="{ row }">
            <span style="font-weight: 600">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="AUC" width="110">
          <template #default="{ row }">
            <span
              :style="{ fontWeight: 600, color: row.auc >= 0.8 ? '#67c23a' : row.auc >= 0.7 ? '#e6a23c' : '#f56c6c' }"
              >{{ row.auc.toFixed(4) }}</span
            >
          </template>
        </el-table-column>
        <el-table-column label="KS" width="110">
          <template #default="{ row }">{{ row.ks.toFixed(4) }}</template>
        </el-table-column>
        <el-table-column label="召回率" width="110">
          <template #default="{ row }">{{ (row.recall * 100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column label="精确率" width="110">
          <template #default="{ row }">{{ (row.precision * 100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column label="F1" width="110">
          <template #default="{ row }">{{ row.f1.toFixed(4) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}

/* 混淆矩阵（HTML 网格） */
.cm-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  max-width: 520px;
  margin: 0 auto;

  .cm-cell {
    border-radius: 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 86px;
    padding: 12px;
  }

  .cm-corner {
    background: transparent;
  }

  .cm-head {
    background: #f0f2f5;
    color: #606266;
    font-size: 13px;
    font-weight: 600;
  }

  .cm-rownum {
    background: #f7f9fb;
    color: #606266;
    font-size: 13px;
    font-weight: 600;
  }

  .cm-value {
    color: #fff;

    .cm-num {
      font-size: 28px;
      font-weight: 700;
      line-height: 1.2;
    }

    .cm-name {
      font-size: 12px;
      opacity: 0.92;
      margin-top: 4px;
    }
  }
}

.cm-legend {
  display: flex;
  justify-content: center;
  gap: 22px;
  margin-top: 14px;
  font-size: 12px;
  color: #606266;

  .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    margin-right: 5px;
    vertical-align: middle;
  }
}
</style>
