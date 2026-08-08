import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api/v1',
  timeout: 60000,
})

http.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res && typeof res === 'object' && 'code' in res) {
      if (res.code !== 200) {
        ElMessage.error(res.message || '请求失败')
        return Promise.reject(new Error(res.message || '请求失败'))
      }
      return res.data as any
    }
    return res
  },
  (error) => {
    if (error.response?.status === 401) {
      const auth = useAuthStore()
      if (router.currentRoute.value.path !== '/login') {
        // 登录过期：提示后 3 秒自动返回登录页
        ElMessage.warning('登录已过期，请重新登录')
        setTimeout(() => {
          auth.logout()
          router.push('/login')
        }, 3000)
      } else {
        // 登录页自身失败：直接提示，不延迟跳转
        ElMessage.error('用户名或密码错误')
      }
    } else {
      ElMessage.error(error.message || '网络错误')
    }
    return Promise.reject(error)
  }
)

export default http
