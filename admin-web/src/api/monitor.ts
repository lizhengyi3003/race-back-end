import http from './http'

export interface ServerStatus {
  hostname: string
  platform: string
  pythonVersion: string
  uptimeSeconds: number
  bootTime?: string
  cpu: { percent: number; cores: number; freq: number }
  memory: { total: number; used: number; free: number; percent: number }
  disk: { total: number; used: number; free: number; percent: number }
  processCpu: number
  processMemory: number
  threads: number
}

export interface DatabaseStatus {
  connected: boolean
  dialect: string
  tables: { name: string; rows: number; sizeMb: number }[]
  totalSizeMb: number
}

export interface HealthStatus {
  status: string
  service: string
  database: string
  modelExists: boolean
  modelVersion?: string
  timestamp: string
}

export function getServerStatus(): Promise<ServerStatus> {
  return http.get('/monitor/server')
}

export function getDatabaseStatus(): Promise<DatabaseStatus> {
  return http.get('/monitor/database')
}

export function getHealth(): Promise<HealthStatus> {
  return http.get('/monitor/health')
}
