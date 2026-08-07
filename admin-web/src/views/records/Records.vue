<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listRecords, deleteRecord, getRecord, type AssessmentRecord } from '@/api/admin'
import { exportRecords } from '@/api/data'

const loading = ref(false)
const records = ref<AssessmentRecord[]>([])
const total = ref(0)
const query = reactive({ page: 1, size: 10, keyword: '', level: '', businessType: '' })
const detailVisible = ref(false)
const detail = ref<any>(null)

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

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>评估记录</h1>
      <p>涉农主体信贷风险评估历史记录管理</p>
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
        <el-select v-model="query.businessType" placeholder="经营类型" clearable style="width: 140px">
          <el-option label="种植" value="种植" />
          <el-option label="养殖" value="养殖" />
          <el-option label="加工" value="加工" />
          <el-option label="混合" value="混合" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
        <div style="flex: 1" />
        <el-button type="success" plain @click="exportRecords">导出 CSV</el-button>
      </div>

      <el-table v-loading="loading" :data="records" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="enterpriseName" label="企业名称" min-width="170" show-overflow-tooltip />
        <el-table-column prop="businessType" label="经营类型" width="90" />
        <el-table-column prop="productType" label="主营产品" width="110" show-overflow-tooltip />
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
        <el-table-column label="风险等级" width="100">
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
        <el-table-column label="操作" width="130" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

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
          <el-descriptions-item label="主营产品">{{ detail.productType || '-' }}</el-descriptions-item>
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
          <el-descriptions-item v-if="detail.assessorName" label="评估人">{{ detail.assessorName }}</el-descriptions-item>
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
          <h4 style="margin: 18px 0 10px">
            动态指标明细（{{ detail.indicatorValues.length }} 项）
          </h4>
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
                  :type="row.quality === '直接' ? 'success' : row.quality === '代理' ? 'warning' : row.quality === '存疑' ? 'danger' : 'info'"
                  size="small"
                  >{{ row.quality }}</el-tag
                >
              </template>
            </el-table-column>
          </el-table>
        </template>

        <!-- 传统 15 项指标（兼容旧记录） -->
        <template v-if="detail.landConfirmedArea != null || detail.grainSubsidy != null || detail.yearsOperating != null">
          <h4 style="margin: 18px 0 10px">风险输入指标</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="确权耕地总面积">{{ detail.landConfirmedArea ?? '-' }} 亩</el-descriptions-item>
            <el-descriptions-item label="土地流转合同年限">{{ detail.landTransferYears ?? '-' }} 年</el-descriptions-item>
            <el-descriptions-item label="土地流转稳定性">{{ detail.landTransferStability || '-' }}</el-descriptions-item>
            <el-descriptions-item label="黑土地保护耕作面积"
              >{{ detail.blackSoilProtection ?? '-' }} 亩</el-descriptions-item
            >
            <el-descriptions-item label="耕地地力保护补贴">{{ detail.grainSubsidy ?? '-' }} 元</el-descriptions-item>
            <el-descriptions-item label="大型农机购置补贴">{{ detail.machinerySubsidy ?? '-' }} 元</el-descriptions-item>
            <el-descriptions-item label="粮食规模种植补贴">{{ detail.grainScaleSubsidy ?? '-' }} 元</el-descriptions-item>
            <el-descriptions-item label="特色经济作物补贴"
              >{{ detail.specialtyCropSubsidy ?? '-' }} 元</el-descriptions-item
            >
            <el-descriptions-item label="农业保险连续投保年限"
              >{{ detail.insuranceYears ?? '-' }} 年</el-descriptions-item
            >
            <el-descriptions-item label="历史保险理赔频次">{{ detail.claimCount ?? '-' }} 次</el-descriptions-item>
            <el-descriptions-item label="设施农业附加保险">{{ detail.facilityInsurance || '-' }}</el-descriptions-item>
            <el-descriptions-item label="主体持续经营年限">{{ detail.yearsOperating ?? '-' }} 年</el-descriptions-item>
            <el-descriptions-item label="长期收购订单">{{ detail.purchaseOrder || '-' }}</el-descriptions-item>
            <el-descriptions-item label="农产品年稳定营收">{{ detail.annualRevenue ?? '-' }} 万元</el-descriptions-item>
            <el-descriptions-item label="历年信贷履约记录">{{ detail.creditRecord || '-' }}</el-descriptions-item>
          </el-descriptions>
        </template>

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
  </div>
</template>
