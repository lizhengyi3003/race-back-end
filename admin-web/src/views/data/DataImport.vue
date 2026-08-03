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
              { f: 'landConfirmedArea', d: '确权耕地总面积（亩）' },
              { f: 'landTransferYears', d: '土地流转合同年限（年）' },
              { f: 'landTransferStability', d: '土地流转稳定性：稳定/小幅调整/频繁变更' },
              { f: 'blackSoilProtection', d: '黑土地保护性耕作面积（亩）' },
              { f: 'grainSubsidy', d: '耕地地力保护补贴（元）' },
              { f: 'machinerySubsidy', d: '大型农机购置补贴（元）' },
              { f: 'grainScaleSubsidy', d: '粮食规模种植专项补贴（元）' },
              { f: 'specialtyCropSubsidy', d: '特色经济作物补贴（元）' },
              { f: 'insuranceYears', d: '农业保险连续投保年限（年）' },
              { f: 'claimCount', d: '历史保险理赔频次（次）' },
              { f: 'facilityInsurance', d: '设施农业附加保险：完整投保/仅基础险/未投保' },
              { f: 'yearsOperating', d: '主体持续经营年限（年）' },
              { f: 'purchaseOrder', d: '长期收购订单：年度订单/零散收购/无稳定渠道' },
              { f: 'annualRevenue', d: '农产品年稳定营收（万元）' },
              { f: 'creditRecord', d: '历年涉农信贷履约：无逾期/有逾期' },
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
