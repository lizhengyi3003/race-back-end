import http from './http'
import type { PageData } from './admin'

export interface IndicatorItem {
  id: number
  code: string
  name: string
  level: string
  category_code: string
  category_name: string
  indicator_type: string
  unit: string
  value_range: string
  options: string[]
  data_source: string
  is_feature: boolean
  risk_meaning: string
  weight_star: number
  region: string
  is_veto: boolean
  cycle: string
  scoring_rule: string
  scoring_config: Record<string, any> | null
  display_order: number
}

export interface IndicatorStats {
  total: number
  by_level: Record<string, number>
  by_type: Record<string, number>
  feature: number
  veto: number
  categories: number
}

export interface IndicatorQuery {
  page: number
  size: number
  keyword?: string
  level?: string
  categoryCode?: string
  indicatorType?: string
  isFeature?: boolean
  isVeto?: boolean
}

export function listIndicators(params: IndicatorQuery): Promise<PageData<IndicatorItem>> {
  return http.get('/admin/indicators', { params })
}

export function getIndicatorStats(): Promise<IndicatorStats> {
  return http.get('/admin/indicators/stats')
}

export function getIndicator(code: string): Promise<IndicatorItem> {
  return http.get(`/admin/indicators/${encodeURIComponent(code)}`)
}

export function updateIndicator(code: string, data: Record<string, any>): Promise<IndicatorItem> {
  return http.put(`/admin/indicators/${encodeURIComponent(code)}`, data)
}

export function getIndicatorTree(): Promise<any> {
  return http.get('/indicators/tree')
}
