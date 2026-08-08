<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listUsers, createUser, updateUser, deleteUser, resetPassword, type UserItem } from '@/api/admin'

const loading = ref(false)
const users = ref<UserItem[]>([])
const total = ref(0)
const query = reactive({ page: 1, size: 10, keyword: '' })

const dialogVisible = ref(false)
const isEdit = ref(false)
const form = reactive({ id: 0, username: '', password: '', realName: '', role: 'analyst', status: 1 })

const pwdDialogVisible = ref(false)
const pwdTarget = ref<UserItem | null>(null)
const newPassword = ref('')

async function load() {
  loading.value = true
  try {
    const res = await listUsers(query)
    users.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function onSearch() {
  query.page = 1
  load()
}

function openAdd() {
  isEdit.value = false
  Object.assign(form, { id: 0, username: '', password: '', realName: '', role: 'analyst', status: 1 })
  dialogVisible.value = true
}

function openEdit(row: UserItem) {
  isEdit.value = true
  Object.assign(form, {
    id: row.id,
    username: row.username,
    password: '',
    realName: row.realName,
    role: row.role,
    status: row.status,
  })
  dialogVisible.value = true
}

async function save() {
  if (isEdit.value) {
    await updateUser(form.id, { realName: form.realName, role: form.role, status: form.status })
    ElMessage.success('已更新')
  } else {
    if (!form.username || !form.password) {
      ElMessage.warning('用户名和密码必填')
      return
    }
    await createUser({ username: form.username, password: form.password, realName: form.realName, role: form.role })
    ElMessage.success('已创建')
  }
  dialogVisible.value = false
  load()
}

async function remove(row: UserItem) {
  await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '提示', { type: 'warning' })
  await deleteUser(row.id)
  ElMessage.success('已删除')
  load()
}

function openPwd(row: UserItem) {
  pwdTarget.value = row
  newPassword.value = ''
  pwdDialogVisible.value = true
}

async function doResetPwd() {
  if (!newPassword.value) {
    ElMessage.warning('请输入新密码')
    return
  }
  await resetPassword(pwdTarget.value!.id, newPassword.value)
  ElMessage.success('密码已重置')
  pwdDialogVisible.value = false
}

onMounted(load)
</script>

<template>
  <div class="page-container">
    <div class="page-header">
      <h1>用户管理</h1>
      <p>管理平台账号与角色权限</p>
    </div>

    <div class="info-card">
      <div class="toolbar">
        <el-input
          v-model="query.keyword"
          placeholder="搜索用户名/姓名"
          clearable
          style="width: 240px"
          @keyup.enter="onSearch"
        />
        <el-button type="primary" @click="onSearch">查询</el-button>
        <div style="flex: 1" />
        <el-button type="success" @click="openAdd">新增用户</el-button>
      </div>

      <el-table v-loading="loading" :data="users" stripe style="min-width: 1150px">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" min-width="130" />
        <el-table-column prop="realName" label="姓名" min-width="120" />
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" size="small">{{
              row.role === 'admin' ? '管理员' : '分析师'
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">{{
              row.status === 1 ? '启用' : '禁用'
            }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lastLoginAt" label="最近登录" width="180">
          <template #default="{ row }">{{ row.lastLoginAt?.replace('T', ' ').slice(0, 19) || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
            <el-button link type="warning" size="small" @click="openPwd(row)">重置密码</el-button>
            <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="query.page"
        v-model:page-size="query.size"
        :total="total"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        style="margin-top: 16px; justify-content: flex-end"
        @change="load"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="440px">
      <el-form label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="isEdit" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.realName" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="分析师" value="analyst" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isEdit" label="状态">
          <el-switch
            v-model="form.status"
            :active-value="1"
            :inactive-value="0"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="pwdDialogVisible" title="重置密码" width="420px">
      <el-form label-width="80px">
        <el-form-item label="用户">{{ pwdTarget?.username }}</el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="newPassword" type="password" show-password placeholder="请输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="doResetPwd">确定重置</el-button>
      </template>
    </el-dialog>
  </div>
</template>
