<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { downloadTemplate, exportRecords, importCsv } from '@/api/data'

const fileList = ref<any[]>([])
const importing = ref(false)
const importResult = ref<{ imported: number; errors: any[] } | null>(null)

async function handleTemplate() {
  await downloadTemplate()
  ElMessage.success('模板已下载')
}

async function handleExport() {
  await exportRecords()
  ElMessage.success('已导出评估记录')
}

async function handleImport() {
  if (!fileList.value.length) {
    ElMessage.warning('请先选择 CSV 文件')
    return
  }
  importing.value = true
  try {
    const res = await importCsv(fileList.value[0].raw as File)
    importResult.value = res
    ElMessage.success(`成功导入 ${res.imported} 条记录`)
    fileList.value = []
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>数据导入导出</h1>
      <p>批量导入涉农主体数据（CSV）并自动评估，或导出全部评估记录</p>
    </div>

    <el-row :gutter="16">
      <el-col :span="12">
        <div class="info-card">
          <h3 class="card-title">批量导入</h3>
          <el-alert type="info" :closable="false" style="margin-bottom: 14px">
            <template #title>
              请先下载模板填写数据。CSV 需包含企业名称与 21 项指标列（可留空），导入时系统自动完成信用评估。
            </template>
          </el-alert>
          <el-upload
            v-model:file-list="fileList"
            drag
            accept=".csv"
            :auto-upload="false"
            :limit="1"
            style="margin-bottom: 14px"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">将 CSV 文件拖到此处，或<em>点击选择</em></div>
          </el-upload>
          <div class="toolbar">
            <el-button type="success" plain @click="handleTemplate">下载模板</el-button>
            <el-button type="primary" :loading="importing" @click="handleImport">开始导入</el-button>
          </div>

          <template v-if="importResult">
            <el-alert
              :title="`导入完成：成功 ${importResult.imported} 条${importResult.errors.length ? '，失败 ' + importResult.errors.length + ' 条' : ''}`"
              :type="importResult.errors.length ? 'warning' : 'success'"
              :closable="false"
              style="margin-top: 10px"
            />
            <el-table
              v-if="importResult.errors.length"
              :data="importResult.errors"
              size="small"
              style="margin-top: 10px"
            >
              <el-table-column prop="row" label="行号" width="80" />
              <el-table-column prop="error" label="错误信息" />
            </el-table>
          </template>
        </div>
      </el-col>

      <el-col :span="12">
        <div class="info-card">
          <h3 class="card-title">数据导出</h3>
          <p class="form-tip" style="margin-top: 0">
            导出全部评估记录为 CSV 文件，包含企业信息、21 项指标、信用评分、风险等级与授信建议。
          </p>
          <el-button type="primary" plain @click="handleExport">导出评估记录 CSV</el-button>

          <el-divider />
          <h4 style="margin: 0 0 8px">模板字段说明</h4>
          <el-table
            :data="[
              { f: 'enterpriseName', d: '企业名称（必填）' },
              { f: 'businessType', d: '经营类型：种植/养殖/加工/混合' },
              { f: 'productType', d: '主营产品' },
              { f: 'age', d: '年龄（岁）' },
              { f: 'education', d: '受教育程度：小学及以下/初中/高中/大专及以上' },
              { f: 'familyMembers', d: '家庭成员数量（人）' },
              { f: 'landConfirmedArea', d: '土地确权面积（亩）' },
              { f: 'landTransferYears', d: '土地流转年限（年）' },
              { f: 'plantingStructure', d: '种植结构：主粮种植/经济作物/混合经营/设施农业' },
              { f: 'landUtilization', d: '土地规模利用率（%）' },
              { f: 'grainSubsidy', d: '粮食直补金额（元）' },
              { f: 'machinerySubsidy', d: '农机购置补贴（元）' },
              { f: 'otherSubsidy', d: '其他涉农补贴（元）' },
              { f: 'insuranceCoverage', d: '农业保险覆盖率（%）' },
              { f: 'claimCount', d: '历年理赔次数（次）' },
              { f: 'claimAmount', d: '历年理赔金额（元）' },
              { f: 'claimRatio', d: '理赔金额占比（%）' },
              { f: 'yearsOperating', d: '经营年限（年）' },
              { f: 'businessConcentration', d: '经营范围集中度（%）' },
              { f: 'annualRevenue', d: '年销售收入（万元）' },
              { f: 'revenueStability', d: '收入稳定性：稳定/基本稳定/波动较大/大幅波动' },
              { f: 'creditStatus', d: '征信状况：无不良记录/轻微逾期/多次逾期/严重失信' },
              { f: 'loanHistory', d: '历史贷款记录（次）' },
              { f: 'loanOverdueHistory', d: '历史逾期记录（次）' },
            ]"
            size="small"
          >
            <el-table-column prop="f" label="字段" width="190" />
            <el-table-column prop="d" label="说明" />
          </el-table>
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
</style>
