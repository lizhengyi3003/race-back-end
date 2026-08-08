<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listRecords,
  deleteRecord,
  getRecord,
  getBacktestStats,
  updateRecordOutcome,
  type AssessmentRecord,
  type BacktestStats,
} from '@/api/admin'

const loading = ref(false)
const records = ref<AssessmentRecord[]>([])
const total = ref(0)
const query = reactive({ page: 1, size: 10, keyword: '', level: '', businessType: '' })
const detailVisible = ref(false)
const detail = ref<any>(null)

// ---- 真实回测 ----
const stats = ref<BacktestStats | null>(null)
const outcomeVisible = ref(false)
const outcomeForm = reactive({ id: 0, enterpriseName: '', outcome: 'pending', note: '' })
const OUTCOME_OPTIONS = [
  { label: '正常还款', value: 'normal', type: 'success' },
  { label: '逾期', value: 'overdue', type: 'danger' },
  { label: '未放款', value: 'rejected', type: 'info' },
  { label: '待回填', value: 'pending', type: 'warning' },
]

async function loadStats() {
  try {
    stats.value = await getBacktestStats()
  } catch {
    // 忽略（统计接口失败不影响列表）
  }
}

function outcomeTag(outcome?: string) {
  return OUTCOME_OPTIONS.find((o) => o.value === outcome)?.type || 'info'
}
function outcomeLabel(outcome?: string) {
  return OUTCOME_OPTIONS.find((o) => o.value === outcome)?.label || outcome || '待回填'
}

function openOutcome(row: AssessmentRecord) {
  outcomeForm.id = row.id
  outcomeForm.enterpriseName = row.enterpriseName
  outcomeForm.outcome = row.outcome || 'pending'
  outcomeForm.note = row.outcomeNote || ''
  outcomeVisible.value = true
}

async function saveOutcome() {
  await updateRecordOutcome(outcomeForm.id, { outcome: outcomeForm.outcome, note: outcomeForm.note })
  ElMessage.success('已回填')
  outcomeVisible.value = false
  load()
  loadStats()
}

async function load() {
  loading.value = true
  try {
    const res = await listRecords(query)
    records.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function search() {
  query.page = 1
  load()
}

function levelTag(level: string) {
  return level === '低风险' ? 'success' : level === '中等风险' ? 'warning' : 'danger'
}

async function showDetail(row: AssessmentRecord) {
  try {
    detail.value = await getRecord(row.id)
    detailVisible.value = true
  } catch {
    // 忽略
  }
}

async function remove(row: AssessmentRecord) {
  await ElMessageBox.confirm(`确定删除「${row.enterpriseName}」的评估记录吗？`, '提示', { type: 'warning' })
  await deleteRecord(row.id)
  ElMessage.success('已删除')
  load()
}

onMounted(() => {
  load()
  loadStats()
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>评估记录</h1>
      <p>涉农主体信贷风险评估历史记录管理</p>
    </div>

    <!-- 真实回测统计 -->
    <div v-if="stats" class="backtest-card info-card">
      <div class="backtest-head">
        <b>真实回测</b>
        <span class="backtest-sub">已回填 {{ stats.filled }}/{{ stats.total }} 条 · 现实版指标基于人工回填的真实放款结果（记录列表「回填」维护）</span>
      </div>
      <div class="backtest-grid">
        <div class="bt-item">
          <div class="bt-value">{{ stats.precisionHighRisk != null ? (stats.precisionHighRisk * 100).toFixed(1) + '%' : '-' }}</div>
          <div class="bt-label">精确率 · 判高风险中实际逾期</div>
        </div>
        <div class="bt-item">
          <div class="bt-value">{{ stats.recallOverdue != null ? (stats.recallOverdue * 100).toFixed(1) + '%' : '-' }}</div>
          <div class="bt-label">召回率 · 实际逾期中被判高风险</div>
        </div>
        <div class="bt-item">
          <div class="bt-value">{{ stats.overdueTotal }}</div>
          <div class="bt-label">已逾期样本</div>
        </div>
        <div class="bt-item">
          <div class="bt-value">{{ stats.highRiskTotal }}</div>
          <div class="bt-label">判高风险样本</div>
        </div>
      </div>
    </div>

    <div class="info-card">
      <div class="toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索企业名称/主营产品"
          clearable
          style="width: 240px"
          @keyup.enter="search"
        />
        <el-select v-model="query.level" placeholder="风险等级" clearable style="width: 140px">
          <el-option label="低风险" value="低风险" />
          <el-option label="中等风险" value="中等风险" />
          <el-option label="高风险" value="高风险" />
        </el-select>
        <el-select v-model="query.businessType" placeholder="经营类型" clearable style="width: 180px">
          <el-option label="农林牧渔业" value="01" />
          <el-option label="食用加工与制造" value="02" />
          <el-option label="非食用加工与制造" value="03" />
          <el-option label="生产资料制造与农田水利" value="04" />
          <el-option label="流通服务" value="05" />
          <el-option label="科研和技术服务" value="06" />
          <el-option label="教育培训与人力资源服务" value="07" />
          <el-option label="生态保护和环境治理" value="08" />
          <el-option label="休闲观光与农业农村管理服务" value="09" />
          <el-option label="其他支持服务" value="10" />
          <el-option label="混合经营" value="MIXED" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
        <div style="flex: 1" />
      </div>

      <div class="table-scroll">
        <el-table v-loading="loading" :data="records" stripe style="min-width: 1180px">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="enterpriseName" label="企业名称" min-width="170" show-overflow-tooltip />
          <el-table-column prop="businessType" label="经营类型" width="100" />
          <el-table-column label="信用评分" width="110">
            <template #default="{ row }">
              <span
                :style="{
                  color: row.score >= 700 ? '#67c23a' : row.score >= 500 ? '#e6a23c' : '#f56c6c',
                  fontWeight: 600,
                }"
                >{{ row.score }}</span
              >
            </template>
          </el-table-column>
          <el-table-column label="风险等级" width="140">
            <template #default="{ row }">
              <el-tag :type="levelTag(row.level)" size="small">{{ row.level }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="suggestedAmount" label="建议额度(万)" width="110" />
          <el-table-column prop="suggestedRate" label="建议利率(%)" width="100" />
          <el-table-column prop="assessorName" label="评估人" width="100" />
          <el-table-column prop="createdAt" label="时间" width="170">
            <template #default="{ row }">{{ row.createdAt?.replace('T', ' ').slice(0, 19) }}</template>
          </el-table-column>
          <el-table-column label="回填结果" width="110">
            <template #default="{ row }">
              <el-tag :type="outcomeTag(row.outcome)" size="small">{{ outcomeLabel(row.outcome) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="170" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
              <el-button link type="warning" size="small" @click="openOutcome(row)">回填</el-button>
              <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

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

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" title="评估详情" size="560px">
      <template v-if="detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="企业名称">{{ detail.enterpriseName }}</el-descriptions-item>
          <el-descriptions-item label="经营类型">{{ detail.businessType || '-' }}</el-descriptions-item>
          <el-descriptions-item label="信用评分">
            <span
              :style="{
                color: detail.score >= 700 ? '#67c23a' : detail.score >= 500 ? '#e6a23c' : '#f56c6c',
                fontWeight: 700,
                fontSize: 18,
              }"
              >{{ detail.score }}</span
            >
          </el-descriptions-item>
          <el-descriptions-item label="违约概率">{{ (detail.probability * 100).toFixed(2) }}%</el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="levelTag(detail.level)" size="small">{{ detail.level }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="建议额度">{{ detail.suggestedAmount }} 万元</el-descriptions-item>
          <el-descriptions-item label="建议利率">{{ detail.suggestedRate }}%</el-descriptions-item>
          <el-descriptions-item v-if="detail.completeness != null" label="数据完整度">
            {{ (detail.completeness * 100).toFixed(0) }}%
          </el-descriptions-item>
          <el-descriptions-item v-if="detail.assessorName" label="评估人">{{
            detail.assessorName
          }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.createdAt" label="时间" :span="2">
            {{ detail.createdAt?.replace('T', ' ').slice(0, 19) }}
          </el-descriptions-item>
        </el-descriptions>

        <template v-if="detail.veto">
          <h4 style="margin: 18px 0 10px">一票否决</h4>
          <el-alert :title="detail.veto" type="error" :closable="false" show-icon />
        </template>

        <!-- 混合经营构成 -->
        <template v-if="detail.mixedBusiness && Object.keys(detail.mixedBusiness).length">
          <h4 style="margin: 18px 0 10px">混合经营构成</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item v-for="(ratio, code) in detail.mixedBusiness" :key="code" :label="`业务 ${code}`">
              {{ (ratio * 100).toFixed(0) }}%
            </el-descriptions-item>
          </el-descriptions>
        </template>

        <!-- 动态指标明细 -->
        <template v-if="detail.indicatorValues?.length">
          <h4 style="margin: 18px 0 10px">动态指标明细（{{ detail.indicatorValues.length }} 项）</h4>
          <el-table :data="detail.indicatorValues" size="small" max-height="360">
            <el-table-column prop="code" label="编码" width="110" />
            <el-table-column prop="name" label="指标" min-width="170" show-overflow-tooltip />
            <el-table-column prop="level" label="层级" width="70" />
            <el-table-column label="值" min-width="100">
              <template #default="{ row }">{{ row.value ?? '-' }}{{ row.unit ? ' ' + row.unit : '' }}</template>
            </el-table-column>
            <el-table-column label="质量" width="80">
              <template #default="{ row }">
                <el-tag
                  :type="
                    row.quality === '直接'
                      ? 'success'
                      : row.quality === '代理'
                        ? 'warning'
                        : row.quality === '存疑'
                          ? 'danger'
                          : 'info'
                  "
                  size="small"
                  >{{ row.quality }}</el-tag
                >
              </template>
            </el-table-column>
          </el-table>
        </template>

        <!-- 主要扣分项 -->
        <template v-if="detail.result?.deductions?.length">
          <h4 style="margin: 18px 0 10px">主要扣分项</h4>
          <el-table :data="detail.result.deductions" size="small">
            <el-table-column prop="factor" label="指标" />
            <el-table-column prop="score" label="得分" width="80" />
            <el-table-column prop="reason" label="原因" />
          </el-table>
        </template>

        <h4 style="margin: 18px 0 10px">信贷建议</h4>
        <el-alert :title="detail.result?.advice || '-'" type="info" :closable="false" />
      </template>
    </el-drawer>

    <!-- 回填真实结果弹窗 -->
    <el-dialog v-model="outcomeVisible" title="回填真实结果" width="420px" append-to-body>
      <el-form label-width="90px">
        <el-form-item label="企业名称">
          <span>{{ outcomeForm.enterpriseName }}</span>
        </el-form-item>
        <el-form-item label="真实结果">
          <el-select v-model="outcomeForm.outcome" style="width: 100%">
            <el-option v-for="o in OUTCOME_OPTIONS" :key="o.value" :label="o.label" :value="o.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="outcomeForm.note"
            type="textarea"
            :rows="2"
            maxlength="255"
            placeholder="如：实际放款后 6 个月出现逾期"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="outcomeVisible = false">取消</el-button>
        <el-button type="primary" @click="saveOutcome">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

// 真实回测统计卡片
.backtest-card {
  margin-bottom: 16px;
  padding: 16px 20px;

  .backtest-head {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-bottom: 12px;

    .backtest-sub {
      font-size: 12px;
      color: #909399;
    }
  }

  .backtest-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;

    .bt-item {
      background: #f7f8fa;
      border-radius: 8px;
      padding: 12px 14px;

      .bt-value {
        font-size: 22px;
        font-weight: 700;
        color: #303133;
        line-height: 1.2;
      }

      .bt-label {
        font-size: 12px;
        color: #909399;
        margin-top: 4px;
      }
    }
  }
}

// 表格横向滚动：窄屏时避免列被压缩（风险等级/时间显示不全）
.table-scroll {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;

  :deep(.el-table) {
    width: 100%;
  }
}
</style>
