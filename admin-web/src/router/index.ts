import { createRouter, createWebHashHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '系统概览', icon: 'Odometer' },
      },
      {
        path: 'records',
        name: 'Records',
        component: () => import('@/views/records/Records.vue'),
        meta: { title: '评估记录', icon: 'Document' },
      },
      {
        path: 'indicators',
        name: 'Indicators',
        component: () => import('@/views/indicators/Indicators.vue'),
        meta: { title: '指标管理', icon: 'Collection' },
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/Users.vue'),
        meta: { title: '用户管理', icon: 'User' },
      },
      {
        path: 'config',
        name: 'Config',
        component: () => import('@/views/config/Config.vue'),
        meta: { title: '系统配置', icon: 'Setting' },
      },
      {
        path: 'model/train',
        name: 'ModelTrain',
        component: () => import('@/views/model/ModelTrain.vue'),
        meta: { title: '模型训练与评估', icon: 'TrendCharts' },
      },
      {
        path: 'model/versions',
        name: 'ModelVersions',
        component: () => import('@/views/model/ModelVersions.vue'),
        meta: { title: '模型版本', icon: 'Histogram' },
      },
      {
        path: 'model/simulation',
        name: 'ModelSimulation',
        component: () => import('@/views/model/ModelSimulation.vue'),
        meta: { title: '业务仿真验证', icon: 'MagicStick' },
      },
      {
        path: 'model/monitor',
        name: 'ModelMonitor',
        component: () => import('@/views/model/ModelMonitor.vue'),
        meta: { title: '模型监控', icon: 'Monitor' },
      },
      {
        path: 'api/list',
        name: 'ApiList',
        component: () => import('@/views/api/ApiList.vue'),
        meta: { title: '接口列表', icon: 'Connection' },
      },
      {
        path: 'api/logs',
        name: 'ApiLogs',
        component: () => import('@/views/api/ApiLogs.vue'),
        meta: { title: '接口日志', icon: 'List' },
      },
      {
        path: 'api/tester',
        name: 'ApiTester',
        component: () => import('@/views/api/ApiTester.vue'),
        meta: { title: '接口测试', icon: 'Promotion' },
      },
      {
        path: 'monitor/server',
        name: 'ServerMonitor',
        component: () => import('@/views/monitor/ServerMonitor.vue'),
        meta: { title: '服务器状态', icon: 'Monitor' },
      },
      {
        path: 'monitor/database',
        name: 'DatabaseMonitor',
        component: () => import('@/views/monitor/DatabaseMonitor.vue'),
        meta: { title: '数据库状态', icon: 'Coin' },
      },
      {
        path: 'monitor/health',
        name: 'HealthCheck',
        component: () => import('@/views/monitor/HealthCheck.vue'),
        meta: { title: '健康检查', icon: 'FirstAidKit' },
      },
      {
        path: 'data/import',
        name: 'DataImport',
        component: () => import('@/views/data/DataImport.vue'),
        meta: { title: '数据导入导出', icon: 'UploadFilled' },
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
