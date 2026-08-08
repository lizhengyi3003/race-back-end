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

/** 行为验证码类型：四种交互模式随机 */
export type CaptchaType = 'click' | 'slide' | 'drag' | 'rotate'

/** 行为验证码数据 */
export interface CaptchaData {
  type: CaptchaType
  captchaKey: string
  image: string
  thumb: string
  width: number
  height: number
  thumbWidth: number
  thumbHeight: number
  thumbSize: number
  displayX: number
  displayY: number
}

/** 登录（captchaKey 为已完成的行为验证码） */
export async function login(username: string, password: string, captchaKey = ''): Promise<LoginResult> {
  return http.post('/auth/login', { username, password, captchaKey })
}

/** 获取行为验证码（四种模式随机） */
export async function getCaptcha(): Promise<CaptchaData> {
  return http.get('/captcha')
}

/** 校验验证码（value 由前端按类型拼接） */
export async function checkCaptcha(captchaKey: string, type: CaptchaType, value: string): Promise<{ passed: boolean }> {
  return http.post('/captcha/check', { captchaKey, type, value })
}

export async function getMe(): Promise<UserInfo> {
  return http.get('/auth/me')
}
