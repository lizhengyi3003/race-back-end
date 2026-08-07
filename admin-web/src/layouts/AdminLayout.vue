<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeMenu = computed(() => route.path)
const collapsed = ref(false)

async function handleLogout() {
  await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
  auth.logout()
  router.push('/login')
}

const menus = [
  { path: '/dashboard', title: '系统概览', icon: 'Odometer' },
  {
    title: '数据管理',
    icon: 'FolderOpened',
    children: [
      { path: '/records', title: '评估记录', icon: 'Document' },
      { path: '/indicators', title: '指标管理', icon: 'Collection' },
      { path: '/users', title: '用户管理', icon: 'User' },
      { path: '/config', title: '系统配置', icon: 'Setting' },
    ],
  },
  {
    title: '模型管理',
    icon: 'Cpu',
    children: [
      { path: '/model/train', title: '模型训练与评估', icon: 'TrendCharts' },
      { path: '/model/versions', title: '模型版本', icon: 'Histogram' },
      { path: '/model/simulation', title: '业务仿真验证', icon: 'MagicStick' },
      { path: '/model/monitor', title: '模型监控', icon: 'Monitor' },
    ],
  },
  {
    title: 'API 管理',
    icon: 'Connection',
    children: [
      { path: '/api/list', title: '接口列表', icon: 'Grid' },
      { path: '/api/logs', title: '接口日志', icon: 'List' },
      { path: '/api/tester', title: '接口测试', icon: 'Promotion' },
    ],
  },
  {
    title: '系统监控',
    icon: 'Monitor',
    children: [
      { path: '/monitor/server', title: '服务器状态', icon: 'Cpu' },
      { path: '/monitor/database', title: '数据库状态', icon: 'Coin' },
      { path: '/monitor/health', title: '健康检查', icon: 'FirstAidKit' },
    ],
  },
  { path: '/data/import', title: '数据导入导出', icon: 'UploadFilled' },
]
</script>

<template>
  <el-container class="layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="aside">
      <div class="logo">
        <el-icon :size="22" color="#4c956c"><Grid /></el-icon>
        <span v-show="!collapsed" class="logo-text">风控管理平台</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        :collapse="collapsed"
        class="menu"
        background-color="#1d2b3a"
        text-color="#a5b3c4"
        active-text-color="#67c23a"
      >
        <template v-for="m in menus" :key="m.path || m.title">
          <el-sub-menu v-if="m.children" :index="m.title">
            <template #title>
              <el-icon><component :is="m.icon" /></el-icon>
              <span>{{ m.title }}</span>
            </template>
            <el-menu-item v-for="c in m.children" :key="c.path" :index="c.path">
              <el-icon><component :is="c.icon" /></el-icon>
              <span>{{ c.title }}</span>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="m.path!">
            <el-icon><component :is="m.icon" /></el-icon>
            <span>{{ m.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="collapsed = !collapsed">
            <Expand v-if="collapsed" />
            <Fold v-else />
          </el-icon>
          <span class="page-title">{{ route.meta.title }}</span>
        </div>
        <div class="header-right">
          <el-tag size="small" type="success" effect="plain" class="env-tag">本地环境</el-tag>
          <el-dropdown>
            <span class="user-info">
              <el-avatar :size="30" class="avatar">{{
                auth.user?.realName?.[0] || auth.user?.username?.[0]
              }}</el-avatar>
              <span class="username">{{ auth.user?.realName || auth.user?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>{{ auth.user?.role === 'admin' ? '管理员' : '分析师' }}</el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped lang="scss">
.layout {
  height: 100vh;
}

.aside {
  background: #1d2b3a;
  transition: width 0.2s;
  overflow-x: hidden;

  .logo {
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: #fff;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);

    .logo-text {
      font-size: 15px;
      font-weight: 600;
      white-space: nowrap;
    }
  }

  .menu {
    border-right: none;
  }
}

.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  z-index: 10;

  .header-left {
    display: flex;
    align-items: center;
    gap: 14px;

    .collapse-btn {
      font-size: 20px;
      cursor: pointer;
      color: #606266;
    }

    .page-title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 14px;

    .env-tag {
      margin-right: 4px;
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      color: #303133;
      outline: none;

      .avatar {
        background: #2c6e49;
        color: #fff;
        font-size: 14px;
      }
    }
  }
}

.main {
  background: #f0f2f5;
  padding: 0;
  overflow: auto;
}
</style>
