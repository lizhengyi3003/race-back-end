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

/** 行为验证码数据 */
export interface CaptchaData {
  captchaKey: string
  image: string
  thumb: string
  width: number
  height: number
  thumbWidth: number
  thumbHeight: number
}

/** 登录（captchaKey 为已完成的行为验证码） */
export async function login(username: string, password: string, captchaKey = ''): Promise<LoginResult> {
  return http.post('/auth/login', { username, password, captchaKey })
}

/** 获取点选验证码 */
export async function getCaptcha(): Promise<CaptchaData> {
  return http.get('/captcha')
}

/** 校验验证码点选坐标 */
export async function checkCaptcha(captchaKey: string, dots: Array<[number, number]>): Promise<{ passed: boolean }> {
  return http.post('/captcha/check', { captchaKey, dots })
}

export async function getMe(): Promise<UserInfo> {
  return http.get('/auth/me')
}
