import request from '../utils/request'

// 基础响应结构定义 (对应后端通用返回格式)
export interface ApiResponse<T = any> {
    code: number
    message: string
    data: T
}

// 登录参数
export interface LoginParams {
    phone: string
    password?: string
    code?: string
    loginType: 'password' | 'code' | 'wechat' | 'google'
}

// 注册参数
export interface RegisterParams {
    phone: string
    password?: string
    code: string
}

// 登录成功返回的数据结构
export interface LoginResponseData {
    token: string
    user: {
        id: number
        phone: string
        avatar?: string
        nickname?: string
    }
}

/**
 * 用户登录接口
 * @param data 登录参数
 */
export const loginApi = (data: LoginParams) => {
    return request.post<any, ApiResponse<LoginResponseData>>('/auth/login', data)
}

/**
 * 用户注册接口
 * @param data 注册参数
 */
export const registerApi = (data: RegisterParams) => {
    return request.post<any, ApiResponse<null>>('/auth/register', data)
}

/**
 * 获取图片/短信验证码接口
 * @param phone 手机号
 * @param type 用途类型 (register, login, resetPwd)
 */
export const getVerificationCodeApi = (phone: string, type: 'register' | 'login' | 'resetPwd') => {
    return request.post<any, ApiResponse<null>>('/auth/send-code', { phone, type })
}

/**
 * 用户退出登录
 */
export const logoutApi = () => {
    return request.post<any, ApiResponse<null>>('/auth/logout')
}
