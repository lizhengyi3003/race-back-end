<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({ username: 'admin', password: 'admin123' })
const loading = ref(false)

async function handleLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const res = await login(form.username, form.password)
    auth.setLogin(res.token, res.user)
    ElMessage.success('登录成功')
    router.push('/')
  } catch {
    // 错误已由拦截器提示
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="brand">
        <div class="logo">
          <el-icon :size="30" color="#fff"><Grid /></el-icon>
        </div>
        <h1>涉农信贷风险智能评估系统</h1>
        <p>后台管理平台 · 基于多元统计模型的信用评分卡</p>
      </div>
      <el-form :model="form" @submit.prevent="handleLogin">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" :prefix-icon="'User'" />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="'Lock'"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button type="primary" size="large" class="submit" :loading="loading" @click="handleLogin">
          登 录
        </el-button>
      </el-form>
      <div class="tip">默认账号 admin / admin123</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1d2b3a 0%, #2c6e49 100%);
}

.login-card {
  width: 400px;
  background: #fff;
  border-radius: 14px;
  padding: 36px 40px 28px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.25);

  .brand {
    text-align: center;
    margin-bottom: 28px;

    .logo {
      width: 60px;
      height: 60px;
      margin: 0 auto 14px;
      border-radius: 16px;
      background: linear-gradient(135deg, #2c6e49, #4c956c);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    h1 {
      margin: 0 0 6px;
      font-size: 19px;
      color: #303133;
    }

    p {
      margin: 0;
      font-size: 12px;
      color: #909399;
    }
  }

  .submit {
    width: 100%;
    margin-top: 4px;
  }

  .tip {
    margin-top: 16px;
    text-align: center;
    font-size: 12px;
    color: #c0c4cc;
  }
}
</style>
