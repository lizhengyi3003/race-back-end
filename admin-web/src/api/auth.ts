import http from './http'

export interface UserInfo {
  id: number
  username: string
  realName: string
  role: string
  status: number
  lastLoginAt?: string
  createdAt?: string
}

export interface LoginResult {
  token: string
  user: UserInfo
}

export async function login(username: string, password: string): Promise<LoginResult> {
  return http.post('/auth/login', { username, password })
}

export async function getMe(): Promise<UserInfo> {
  return http.get('/auth/me')
}
