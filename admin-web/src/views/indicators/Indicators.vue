<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getIndicatorStats,
  listIndicators,
  updateIndicator,
  type IndicatorItem,
  type IndicatorStats,
} from '@/api/indicator'

const loading = ref(false)
const saving = ref(false)
const items = ref<IndicatorItem[]>([])
const total = ref(0)
const stats = ref<IndicatorStats | null>(null)

const query = reactive({
  page: 1,
  size: 20,
  keyword: '',
  level: '',
  indicatorType: '',
  isFeature: undefined as boolean | undefined,
  isVeto: undefined as boolean | undefined,
})

const levelTag: Record<string, string> = {
  基本项: 'primary',
  大类: 'success',
  中类: 'warning',
  小类: 'info',
}

async function load() {
  loading.value = true
  try {
    const res = await listIndicators(query)
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  stats.value = await getIndicatorStats()
}

function search() {
  query.page = 1
  load()
}

function reset() {
  query.keyword = ''
  query.level = ''
  query.indicatorType = ''
  query.isFeature = undefined
  query.isVeto = undefined
  search()
}

// ---------- 编辑 ----------
const editVisible = ref(false)
const editForm = reactive<Record<string, any>>({
  code: '',
  name: '',
  level: '',
  indicator_type: '数值',
  unit: '',
  value_range: '',
  data_source: '',
  is_feature: false,
  risk_meaning: '',
  weight_star: 3,
  region: '',
  is_veto: false,
  cycle: '',
  scoring_rule: '',
  scoring_config: '',
  display_order: 0,
})

const typeOptions = ['数值', '枚举', '布尔', '文本']
const cycleOptions = ['年报', '季报', '月报', '实时']

function openEdit(row: IndicatorItem) {
  Object.assign(editForm, {
    code: row.code,
    name: row.name,
    level: row.level,
    indicator_type: row.indicator_type,
    unit: row.unit,
    value_range: row.value_range,
    data_source: row.data_source,
    is_feature: row.is_feature,
    risk_meaning: row.risk_meaning,
    weight_star: row.weight_star,
    region: row.region,
    is_veto: row.is_veto,
    cycle: row.cycle,
    scoring_rule: row.scoring_rule,
    scoring_config: row.scoring_config ? JSON.stringify(row.scoring_config, null, 2) : '',
    display_order: row.display_order,
  })
  editVisible.value = true
}

function parseScoringConfig(): Record<string, any> | null | undefined {
  const raw = String(editForm.scoring_config).trim()
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw)
    if (typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('需为 JSON 对象')
    }
    return parsed
  } catch (e: any) {
    ElMessage.error(`scoring_config 不是合法 JSON：${e.message}`)
    return undefined
  }
}

async function save() {
  const scoringConfig = parseScoringConfig()
  if (scoringConfig === undefined) return
  saving.value = true
  try {
    const payload: Record<string, any> = {
      name: editForm.name,
      indicator_type: editForm.indicator_type,
      unit: editForm.unit,
      value_range: editForm.value_range,
      data_source: editForm.data_source,
      is_feature: editForm.is_feature,
      risk_meaning: editForm.risk_meaning,
      weight_star: editForm.weight_star,
      region: editForm.region,
      is_veto: editForm.is_veto,
      cycle: editForm.cycle,
      scoring_rule: editForm.scoring_rule,
      scoring_config: scoringConfig as Record<string, any> | null,
      display_order: editForm.display_order,
    }
    await updateIndicator(editForm.code, payload)
    ElMessage.success('已保存')
    editVisible.value = false
    load()
  } finally {
    saving.value = false
  }
}

const weightStarText = computed(() => {
  const map: Record<number, string> = { 3: '★★★ 一般', 3.5: '★★★☆ 中', 4: '★★★★ 中高', 4.5: '★★★★☆ 高', 5: '★★★★★ 极高' }
  return map[editForm.weight_star] || `${editForm.weight_star} 星`
})

onMounted(() => {
  load()
  loadStats()
})

// ---------- 一键开关 ----------
async function toggleFeature(row: IndicatorItem) {
  await updateIndicator(row.code, { is_feature: !row.is_feature })
  ElMessage.success(row.is_feature ? '已取消特色' : '已设为特色')
  load()
}

async function toggleVeto(row: IndicatorItem) {
  const next = !row.is_veto
  if (next) {
    await ElMessageBox.confirm(`将「${row.name}」设为一票否决指标？命中即拒绝授信。`, '提示', { type: 'warning' })
  }
  await updateIndicator(row.code, { is_veto: next })
  ElMessage.success(next ? '已设为一票否决' : '已取消一票否决')
  load()
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>指标管理</h1>
      <p>动态指标体系（775 项）配置：层级权重 / 特色 / 一票否决 / 评分规则</p>
    </div>

    <!-- 统计卡片 -->
    <el-row v-if="stats" :gutter="16" class="stat-row">
      <el-col :span="4">
        <div class="stat-card">
          <div class="stat-num">{{ stats.total }}</div>
          <div class="stat-label">指标总数</div>
        </div>
      </el-col>
      <el-col v-for="(n, k) in stats.by_level" :key="k" :span="4">
        <div class="stat-card">
          <div class="stat-num">{{ n }}</div>
          <div class="stat-label">{{ k }}</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card warn">
          <div class="stat-num">{{ stats.feature }}</div>
          <div class="stat-label">特色指标</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card danger">
          <div class="stat-num">{{ stats.veto }}</div>
          <div class="stat-label">一票否决</div>
        </div>
      </el-col>
    </el-row>

    <div class="info-card">
      <div class="toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索指标名称/编码"
          clearable
          style="width: 220px"
          @keyup.enter="search"
        />
        <el-select v-model="query.level" placeholder="层级" clearable style="width: 120px">
          <el-option label="基本项" value="基本项" />
          <el-option label="大类" value="大类" />
          <el-option label="中类" value="中类" />
          <el-option label="小类" value="小类" />
        </el-select>
        <el-select v-model="query.indicatorType" placeholder="指标类型" clearable style="width: 120px">
          <el-option v-for="t in typeOptions" :key="t" :label="t" :value="t" />
        </el-select>
        <el-select v-model="query.isFeature" placeholder="特色" clearable style="width: 100px">
          <el-option label="特色" :value="true" />
          <el-option label="非特色" :value="false" />
        </el-select>
        <el-select v-model="query.isVeto" placeholder="一票否决" clearable style="width: 120px">
          <el-option label="一票否决" :value="true" />
          <el-option label="非否决" :value="false" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
        <el-button @click="reset">重置</el-button>
        <div style="flex: 1" />
        <el-button @click="load">刷新</el-button>
      </div>

      <el-table v-loading="loading" :data="items" stripe size="small">
        <el-table-column prop="code" label="编码" width="110" />
        <el-table-column prop="name" label="指标名称" min-width="190" show-overflow-tooltip />
        <el-table-column label="层级" width="80">
          <template #default="{ row }">
            <el-tag :type="levelTag[row.level] as any" size="small">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="category_name" label="所属类别" width="130" show-overflow-tooltip />
        <el-table-column label="类型" width="70">
          <template #default="{ row }">
            <span :style="{ color: row.indicator_type === '数值' ? '#409eff' : '#e6a23c' }">{{
              row.indicator_type
            }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="70" />
        <el-table-column label="权重星级" width="110">
          <template #default="{ row }">
            <span :style="{ color: row.weight_star >= 4 ? '#67c23a' : row.weight_star >= 3.5 ? '#e6a23c' : '#909399' }">
              {{ row.weight_star }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="标记" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.is_feature" type="warning" size="small" effect="plain">特色</el-tag>
            <el-tag v-if="row.is_veto" type="danger" size="small" effect="plain">一票否决</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="data_source" label="数据来源" width="140" show-overflow-tooltip />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link :type="row.is_feature ? 'warning' : 'success'" size="small" @click="toggleFeature(row)">
              {{ row.is_feature ? '取消特色' : '设特色' }}
            </el-button>
            <el-button link type="danger" size="small" @click="toggleVeto(row)">
              {{ row.is_veto ? '取消否决' : '设否决' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.size"
        :total="total"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[20, 50, 100]"
        style="margin-top: 16px; justify-content: flex-end"
        @change="load"
      />
    </div>

    <!-- 编辑抽屉 -->
    <el-drawer v-model="editVisible" :title="`编辑指标 · ${editForm.code} ${editForm.name}`" size="520px">
      <el-form :model="editForm" label-width="110px">
        <el-form-item label="指标名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="指标类型">
          <el-select v-model="editForm.indicator_type" style="width: 100%">
            <el-option v-for="t in typeOptions" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="editForm.unit" placeholder="如 万元 / 亩 / %" />
        </el-form-item>
        <el-form-item label="取值说明">
          <el-input v-model="editForm.value_range" type="textarea" :rows="2" placeholder="枚举指标用 / 分隔选项" />
        </el-form-item>
        <el-form-item label="权重星级">
          <el-slider v-model="editForm.weight_star" :min="1" :max="5" :step="0.5" show-stops />
          <div class="hint">{{ weightStarText }}</div>
        </el-form-item>
        <el-form-item label="特色指标">
          <el-switch v-model="editForm.is_feature" />
        </el-form-item>
        <el-form-item label="一票否决">
          <el-switch v-model="editForm.is_veto" />
        </el-form-item>
        <el-form-item label="采集周期">
          <el-select v-model="editForm.cycle" clearable style="width: 100%">
            <el-option v-for="c in cycleOptions" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="适用区域">
          <el-input v-model="editForm.region" placeholder="如 东北 / 全国" />
        </el-form-item>
        <el-form-item label="数据来源">
          <el-input v-model="editForm.data_source" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="风险含义">
          <el-input v-model="editForm.risk_meaning" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="评分规则">
          <el-input v-model="editForm.scoring_rule" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="评分参数 JSON">
          <el-input
            v-model="editForm.scoring_config"
            type="textarea"
            :rows="6"
            placeholder='{"max": 100, "good": 60} 或 {"档位": {"优": 1.0, "良": 0.8}}'
          />
        </el-form-item>
        <el-form-item label="排序号">
          <el-input-number v-model="editForm.display_order" :min="0" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
          <el-button @click="editVisible = false">取消</el-button>
        </el-form-item>
      </el-form>
    </el-drawer>
  </div>
</template>

<style scoped>
.stat-row {
  margin-bottom: 16px;
}
.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.stat-card .stat-num {
  font-size: 26px;
  font-weight: 700;
  color: #1d2b3a;
}
.stat-card.warn .stat-num {
  color: #e6a23c;
}
.stat-card.danger .stat-num {
  color: #f56c6c;
}
.stat-card .stat-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
.hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
