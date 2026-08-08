import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 懒加载 chunk 失败（如部署后旧 chunk 404）时自动刷新加载最新版本，最多 2 次
const MAX_AUTO_RELOAD = 2
function lazyView(loader: () => Promise<unknown>): () => Promise<unknown> {
  return () =>
    loader().catch((err: unknown) => {
      const count = Number(sessionStorage.getItem('__race_admin_chunk_reload__') || 0)
      if (count < MAX_AUTO_RELOAD) {
        sessionStorage.setItem('__race_admin_chunk_reload__', String(count + 1))
        window.location.reload()
      }
      sessionStorage.removeItem('__race_admin_chunk_reload__')
      throw err
    })
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: lazyView(() => import('@/views/Login.vue')),
    meta: { title: '登录' },
  },
  {
    path: '/',
    component: lazyView(() => import('@/layouts/AdminLayout.vue')),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: lazyView(() => import('@/views/Dashboard.vue')),
        meta: { title: '系统概览', icon: 'Odometer' },
      },
      {
        path: 'records',
        name: 'Records',
        component: lazyView(() => import('@/views/records/Records.vue')),
        meta: { title: '评估记录', icon: 'Document' },
      },
      {
        path: 'indicators',
        name: 'Indicators',
        component: lazyView(() => import('@/views/indicators/Indicators.vue')),
        meta: { title: '指标管理', icon: 'Collection' },
      },
      {
        path: 'users',
        name: 'Users',
        component: lazyView(() => import('@/views/users/Users.vue')),
        meta: { title: '用户管理', icon: 'User' },
      },
      {
        path: 'config',
        name: 'Config',
        component: lazyView(() => import('@/views/config/Config.vue')),
        meta: { title: '系统配置', icon: 'Setting' },
      },
      {
        path: 'model/train',
        name: 'ModelTrain',
        component: lazyView(() => import('@/views/model/ModelTrain.vue')),
        meta: { title: '模型训练与评估', icon: 'TrendCharts' },
      },
      {
        path: 'model/versions',
        name: 'ModelVersions',
        component: lazyView(() => import('@/views/model/ModelVersions.vue')),
        meta: { title: '模型版本', icon: 'Histogram' },
      },
      {
        path: 'model/monitor',
        name: 'ModelMonitor',
        component: lazyView(() => import('@/views/model/ModelMonitor.vue')),
        meta: { title: '模型监控', icon: 'Monitor' },
      },
      {
        path: 'api/list',
        name: 'ApiList',
        component: lazyView(() => import('@/views/api/ApiList.vue')),
        meta: { title: '接口列表', icon: 'Connection' },
      },
      {
        path: 'api/logs',
        name: 'ApiLogs',
        component: lazyView(() => import('@/views/api/ApiLogs.vue')),
        meta: { title: '接口日志', icon: 'List' },
      },
      {
        path: 'api/tester',
        name: 'ApiTester',
        component: lazyView(() => import('@/views/api/ApiTester.vue')),
        meta: { title: '接口测试', icon: 'Promotion' },
      },
      {
        path: 'monitor/server',
        name: 'ServerMonitor',
        component: lazyView(() => import('@/views/monitor/ServerMonitor.vue')),
        meta: { title: '服务器状态', icon: 'Monitor' },
      },
      {
        path: 'monitor/database',
        name: 'DatabaseMonitor',
        component: lazyView(() => import('@/views/monitor/DatabaseMonitor.vue')),
        meta: { title: '数据库状态', icon: 'Coin' },
      },
      {
        path: 'monitor/health',
        name: 'HealthCheck',
        component: lazyView(() => import('@/views/monitor/HealthCheck.vue')),
        meta: { title: '健康检查', icon: 'FirstAidKit' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  document.title = `${String(to.meta.title || '管理平台')} - 涉农信贷风控管理平台`
  if (to.path !== '/login' && !auth.token) {
    return '/login'
  }
  if (to.path === '/login' && auth.token) {
    return '/'
  }
})

export default router
