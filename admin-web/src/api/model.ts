import http from './http'

export interface ModelInfo {
  version: string | null
  status: string
  trainedAt?: string
  nSamples: number
  nFeatures: number
  auc?: number
  ks?: number
  recall?: number
  precision?: number
  f1?: number
}

export interface ModelMetrics {
  auc: number
  ks: number
  recall: number
  precision: number
  f1: number
  accuracy: number
  bestThreshold: number
  confusionMatrix: number[][]
  rocCurve: { fpr: number; tpr: number }[]
  ksCurve: { threshold: number; tpr: number; fpr: number; diff: number }[]
  ivTable: { factor: string; iv: number; nBins: number }[]
  featureImportance: { factor: string; weight: number }[]
  cvScores: number[]
  psi: number | null
  defaultRate?: number
  nSamples?: number
  nFeatures?: number
  featureNames?: string[]
  smoteApplied?: boolean
  experiments?: any // 三组对比实验
}

export interface Thresholds {
  lowRiskThreshold: number
  highRiskThreshold: number
  baseRate: number
  riskPremiumFactor: number
}

export interface ModelVersionItem {
  id: number
  version: string
  status: string
  nSamples: number
  nFeatures: number
  auc?: number
  ks?: number
  recall?: number
  precision?: number
  f1?: number
  trainedBy?: string
  createdAt?: string
}

export function getModelInfo(): Promise<ModelInfo> {
  return http.get('/model/info')
}

export function getModelMetrics(): Promise<ModelMetrics | null> {
  return http.get('/model/metrics')
}

export function getModelMonitor(): Promise<any> {
  return http.get('/model/monitor')
}


export function trainModel(nSamples?: number): Promise<any> {
  return http.post('/model/train', nSamples ? { nSamples } : {})
}

export function listModelVersions(): Promise<ModelVersionItem[]> {
  return http.get('/model/versions')
}

export function getThresholds(): Promise<Thresholds> {
  return http.get('/model/thresholds')
}

export function saveThresholds(data: Thresholds): Promise<Thresholds> {
  return http.put('/model/thresholds', data)
}
