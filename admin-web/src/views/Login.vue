<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Click } from 'go-captcha-vue'
import 'go-captcha-vue/dist/style.css'
import { login, getCaptcha, checkCaptcha, type CaptchaData } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({ username: 'admin', password: 'admin123' })
const loading = ref(false)

// ---------- 行为验证码（go-captcha）：点击登录后弹出校验 ----------
const captchaVisible = ref(false)
const captchaData = ref<CaptchaData | null>(null)
const captchaLoading = ref(false)

/** 加载/刷新验证码（弹窗打开时调用） */
async function loadCaptcha() {
  captchaLoading.value = true
  try {
    captchaData.value = await getCaptcha()
  } catch {
    captchaData.value = null
  } finally {
    captchaLoading.value = false
  }
}

/** 打开验证码弹窗并加载验证码 */
function openCaptcha() {
  captchaVisible.value = true
  loadCaptcha()
}

/** 点选确认回调：通过则关闭弹窗并执行登录，失败则重置并换一张 */
function onCaptchaConfirm(dots: Array<{ key: number; index: number; x: number; y: number }>, reset: () => void) {
  if (!captchaData.value) return
  const dotsArr: Array<[number, number]> = dots.map((d) => [d.x, d.y])
  checkCaptcha(captchaData.value.captchaKey, dotsArr)
    .then((res) => {
      if (res.passed) {
        ElMessage.success('验证成功')
        captchaVisible.value = false
        doLogin()
      } else {
        ElMessage.warning('验证失败，请重试')
        reset()
        loadCaptcha()
      }
    })
    .catch(() => {
      reset()
      loadCaptcha()
    })
}

/** 真实登录（验证码已通过后调用） */
async function doLogin() {
  if (!captchaData.value) return
  loading.value = true
  try {
    const res = await login(form.username, form.password, captchaData.value.captchaKey)
    auth.setLogin(res.token, res.user)
    ElMessage.success('登录成功')
    router.push('/')
  } catch {
    // 登录失败：重新弹出验证码（换一张，防止同一验证码重复试探）
    captchaVisible.value = true
    loadCaptcha()
  } finally {
    loading.value = false
  }
}

function handleLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  openCaptcha()
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

    <!-- 行为验证码弹窗：点击登录后弹出，校验通过才继续登录 -->
    <el-dialog
      v-model="captchaVisible"
      title="安全验证"
      width="400px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      align-center
      append-to-body
      @closed="captchaData = null"
    >
      <div v-loading="captchaLoading" class="captcha-box">
        <div class="captcha-tip">
          <span>请依次点击下图中的字符</span>
          <el-button link type="primary" size="small" @click="loadCaptcha">换一张</el-button>
        </div>
        <Click
          v-if="captchaData"
          :data="{ image: captchaData.image, thumb: captchaData.thumb }"
          :config="{
            width: captchaData.width,
            height: captchaData.height,
            thumbWidth: captchaData.thumbWidth,
            thumbHeight: captchaData.thumbHeight,
            title: '请依次点击',
            buttonText: '确 认',
          }"
          :events="{ confirm: onCaptchaConfirm }"
        />
      </div>
    </el-dialog>
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

<!-- 验证码弹窗内容被 el-dialog teleport 到 body，需全局样式 -->
<style lang="scss">
.captcha-box {
  width: 100%;
  min-height: 60px;

  .captcha-tip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    font-size: 13px;
    color: #606266;
  }
}
</style>
