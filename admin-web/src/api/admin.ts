import http from './http'

export interface PageData<T> {
  total: number
  page: number
  size: number
  items: T[]
}

export interface AssessmentRecord {
  id: number
  enterpriseName: string
  businessType: string
  score: number
  probability: number
  level: string
  suggestedAmount: number
  suggestedRate: number
  assessorName?: string
  createdAt?: string
  completeness?: number
  veto?: string
  mixedBusiness?: Record<string, number>
  indicatorValues?: { code: string; name: string; level: string; unit: string; value: string | null; quality: string }[]
  input?: any
  result?: any
}

export function listRecords(params: any): Promise<PageData<AssessmentRecord>> {
  return http.get('/risk/records', { params })
}

export function getRecord(id: number): Promise<AssessmentRecord> {
  return http.get(`/risk/records/${id}`)
}

export function deleteRecord(id: number): Promise<void> {
  return http.delete(`/risk/records/${id}`)
}

export interface SystemOverview {
  users: number
  records: number
  models: number
  apiLogs: number
  apiLogsToday: number
  database: string
  version: string
  serverTime: string
}

export function getSystemOverview(): Promise<SystemOverview> {
  return http.get('/admin/stats')
}

export function listUsers(params: any): Promise<PageData<UserItem>> {
  return http.get('/admin/users', { params })
}

export interface UserItem {
  id: number
  username: string
  realName: string
  role: string
  status: number
  lastLoginAt?: string
  createdAt?: string
}

export function createUser(data: any): Promise<UserItem> {
  return http.post('/admin/users', data)
}

export function updateUser(id: number, data: any): Promise<UserItem> {
  return http.put(`/admin/users/${id}`, data)
}

export function deleteUser(id: number): Promise<void> {
  return http.delete(`/admin/users/${id}`)
}

export function resetPassword(id: number, newPassword: string): Promise<void> {
  return http.post(`/admin/users/${id}/reset-password`, { newPassword })
}

export function listApiLogs(params: any): Promise<PageData<ApiLogItem>> {
  // 过滤空值查询参数：axios 会把 undefined/空串序列化成 status= 等，导致后端 422
  const clean: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(params || {})) {
    if (v !== undefined && v !== null && v !== '') clean[k] = v
  }
  return http.get('/admin/api-logs', { params: clean })
}

export interface ApiLogItem {
  id: number
  method: string
  path: string
  statusCode: number
  durationMs: number
  clientIp?: string
  username?: string
  reqBody?: string
  respPreview?: string
  createdAt?: string
}

export function cleanupApiLogs(days?: number): Promise<any> {
  return http.delete('/admin/api-logs', { params: days ? { days } : {} })
}

export function getApiSpec(): Promise<ApiSpecItem[]> {
  return http.get('/admin/api-spec')
}

export interface ApiSpecItem {
  method: string
  path: string
  summary: string
  tags: string[]
  authRequired: boolean
  authMode: 'required' | 'optional' | 'none'
  parameters: { name: string; in: string; required: boolean }[]
  requestBodyExample?: any
}

export function listSystemConfigs(): Promise<any[]> {
  return http.get('/admin/configs')
}

export function updateSystemConfig(key: string, value: string): Promise<any> {
  return http.put(`/admin/configs/${key}`, undefined, { params: { value } })
}
