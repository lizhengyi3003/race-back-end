<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { getApiSpec, type ApiSpecItem } from '@/api/admin'

const route = useRoute()
const auth = useAuthStore()

const spec = ref<ApiSpecItem[]>([])
const method = ref('GET')
const path = ref('')
const bodyText = ref('')
const queryParams = ref('')

const sending = ref(false)
const response = ref<{ status?: number; body?: string; time?: number; error?: string }>({})

const methods = ['GET', 'POST', 'PUT', 'DELETE']

const methodColor: Record<string, string> = {
  GET: '#67c23a',
  POST: '#409eff',
  PUT: '#e6a23c',
  DELETE: '#f56c6c',
}

// 路径参数：识别 {xxx} 占位符并允许填写
const pathParams = ref<string[]>([])
const pathParamValues = ref<Record<string, string>>({})

function extractParams(p: string) {
  const m = [...p.matchAll(/\{(\w+)\}/g)].map((x) => x[1])
  pathParams.value = m
  pathParamValues.value = {}
  m.forEach((k) => (pathParamValues.value[k] = ''))
}

function resolvedPath() {
  let p = path.value
  pathParams.value.forEach((k) => {
    const v = (pathParamValues.value[k] || '').trim()
    p = p.replace(`{${k}}`, v || `{${k}}`)
  })
  return p
}

function onSelect(item: ApiSpecItem) {
  method.value = item.method
  path.value = item.path
  bodyText.value = item.requestBodyExample ? JSON.stringify(item.requestBodyExample, null, 2) : ''
  extractParams(item.path)
}

async function send() {
  if (!path.value) {
    ElMessage.warning('请输入接口路径')
    return
  }
  sending.value = true
  const start = Date.now()
  const url = `${import.meta.env.VITE_API_BASE || '/api/v1'}${resolvedPath()}${queryParams.value ? '?' + queryParams.value : ''}`
  const config: any = {
    method: method.value.toLowerCase(),
    url,
    headers: { Authorization: `Bearer ${auth.token}` },
  }
  if (['post', 'put', 'patch'].includes(method.value.toLowerCase()) && bodyText.value.trim()) {
    try {
      config.data = JSON.parse(bodyText.value)
      config.headers['Content-Type'] = 'application/json'
    } catch {
      ElMessage.error('请求体不是合法 JSON')
      sending.value = false
      return
    }
  }
  try {
    const res = await axios.request(config)
    response.value = {
      status: res.status,
      body: JSON.stringify(res.data, null, 2),
      time: Date.now() - start,
    }
  } catch (e: any) {
    response.value = {
      status: e.response?.status,
      body: JSON.stringify(e.response?.data || e.message, null, 2),
      time: Date.now() - start,
      error: e.message,
    }
  } finally {
    sending.value = false
  }
}

onMounted(async () => {
  spec.value = await getApiSpec()
  if (route.query.path) {
    path.value = String(route.query.path)
    method.value = String(route.query.method || 'GET')
    const item = spec.value.find((s) => s.path === path.value && s.method === method.value)
    if (item) onSelect(item)
    else extractParams(path.value)
  }
})
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>接口测试</h1>
      <p>API 调试控制台（自动携带登录凭证，直连后端）</p>
    </div>

    <el-row :gutter="16">
      <el-col :span="10">
        <div class="info-card">
          <h3 class="card-title">接口选择</h3>
          <el-input
            v-model="path"
            placeholder="接口路径"
            clearable
            style="margin-bottom: 10px"
            @change="extractParams(path)"
          >
            <template #prepend>
              <el-select v-model="method" style="width: 100px">
                <el-option v-for="m in methods" :key="m" :label="m" :value="m" />
              </el-select>
            </template>
          </el-input>
          <template v-if="pathParams.length">
            <div style="font-size: 12px; color: #909399; margin-bottom: 4px">路径参数（{xxx} 占位符）</div>
            <el-input
              v-for="p in pathParams"
              :key="p"
              v-model="pathParamValues[p]"
              :placeholder="`{${p}} 填写实际值`"
              clearable
              size="small"
              style="margin-bottom: 6px"
            >
              <template #prepend>{{ p }}</template>
            </el-input>
          </template>
          <el-input
            v-model="queryParams"
            placeholder="查询参数（可选，如 page=1&size=10）"
            clearable
            style="margin-bottom: 10px"
          />
          <el-input
            v-model="bodyText"
            type="textarea"
            :rows="8"
            placeholder="请求体 JSON（POST/PUT 可选）"
            class="code-input"
          />
          <div class="toolbar" style="margin-top: 10px; margin-bottom: 0">
            <el-button type="primary" :loading="sending" @click="send">发送请求</el-button>
          </div>

          <el-divider />
          <h4 style="margin: 0 0 8px">快速选择</h4>
          <el-select
            v-model="path"
            placeholder="从接口列表选择"
            filterable
            style="width: 100%"
            @change="onSelect(spec.find((s) => s.path === path)!)"
          >
            <el-option v-for="s in spec" :key="s.method + s.path" :label="`${s.method} ${s.path}`" :value="s.path">
              <span>
                <el-tag
                  :color="methodColor[s.method]"
                  size="small"
                  style="border: none; color: #fff; margin-right: 6px"
                  >{{ s.method }}</el-tag
                >
                <code>{{ s.path }}</code>
              </span>
            </el-option>
          </el-select>
        </div>
      </el-col>

      <el-col :span="14">
        <div class="info-card">
          <h3 class="card-title">响应结果</h3>
          <template v-if="response.status">
            <el-tag :type="response.status < 400 ? 'success' : 'danger'" style="margin-bottom: 10px">
              状态码 {{ response.status }} · 耗时 {{ response.time }} ms
            </el-tag>
            <pre class="code-block">{{ response.body }}</pre>
          </template>
          <el-empty v-else description="选择接口并发送请求后，响应将显示在此处" />
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.code-input :deep(textarea) {
  font-family: 'Consolas', monospace;
  font-size: 13px;
  background: #1e1e1e;
  color: #d4d4d4;
}

.code-block {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 14px;
  border-radius: 6px;
  font-size: 13px;
  max-height: 480px;
  overflow: auto;
}
</style>
