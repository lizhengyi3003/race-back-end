import http from './http'

export function getDashboardStats(): Promise<any> {
  return http.get('/dashboard/stats')
}

export function getIndustryDistribution(): Promise<any[]> {
  return http.get('/dashboard/industry-distribution')
}

export function getScoreDistribution(): Promise<any[]> {
  return http.get('/dashboard/score-distribution')
}

export function getTrend(days = 30): Promise<any[]> {
  return http.get('/dashboard/trend', { params: { days } })
}
