import http from './http'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

export interface ImportResult {
  imported: number
  errors: { row: number; error: string }[]
}

export function downloadTemplate(): Promise<void> {
  return new Promise((resolve) => {
    const auth = useAuthStore()
    axios({
      url: `${import.meta.env.VITE_API_BASE || '/api/v1'}/data/template`,
      method: 'get',
      responseType: 'blob',
      headers: { Authorization: `Bearer ${auth.token}` },
    }).then((res) => {
      const blob = new Blob([res.data])
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'risk_import_template.csv'
      a.click()
      URL.revokeObjectURL(url)
      resolve()
    })
  })
}

export function exportRecords(): Promise<void> {
  return new Promise((resolve) => {
    const auth = useAuthStore()
    axios({
      url: `${import.meta.env.VITE_API_BASE || '/api/v1'}/data/export`,
      method: 'get',
      responseType: 'blob',
      headers: { Authorization: `Bearer ${auth.token}` },
    }).then((res) => {
      const blob = new Blob([res.data])
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'assessment_records.csv'
      a.click()
      URL.revokeObjectURL(url)
      resolve()
    })
  })
}

export async function importCsv(file: File): Promise<ImportResult> {
  const form = new FormData()
  form.append('file', file)
  return http.post('/data/import', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
