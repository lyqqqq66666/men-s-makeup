import request from '../utils/request'
import type { ApiResponse } from './auth'

/**
 * 用户模块接口定义
 */

// 1. 获取当前用户信息
export interface UserInfoData {
    user_id: string
    phone: string
    nickname: string
    avatar: string
    season_type: string | null
    last_login_at: string
    last_history: any
    user: {
        id: string
        phone: string
        avatar: string
        nickname: string
    }
}
export const getUserInfoApi = () => {
    return request.get<any, ApiResponse<UserInfoData>>('/api/user/info')
}

// 2. 更新用户资料 (头像)
export interface UpdateProfileParams {
    avatar: string
}
export const updateProfileApi = (data: UpdateProfileParams) => {
    return request.put<any, ApiResponse<any>>('/api/user/profile', data)
}

// 3. 单独修改昵称
export interface UpdateNicknameParams {
    nickname: string
}
export const updateNicknameApi = (data: UpdateNicknameParams) => {
    return request.put<any, ApiResponse<any>>('/api/user/nickname', data)
}

// 4. 上传用户头像 (Multipart)
export const uploadAvatarApi = (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request.post<any, ApiResponse<{ avatar: string; relative_path: string }>>('/api/user/avatar/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    })
}

// 5. 获取用户试妆历史
export const getUserHistoryApi = (limit: number = 20) => {
    return request.get<any, ApiResponse<{ items: any[]; count: number }>>('/api/user/history', { params: { limit } })
}

// 6. 获取用户图片列表
export const getUserImagesApi = (limit: number = 50) => {
    return request.get<any, ApiResponse<{ items: any[]; count: number }>>('/api/user/images', { params: { limit } })
}

// 7. 删除用户图片
export const deleteUserImageApi = (imageId: string) => {
    return request.delete<any, ApiResponse<{ image_id: string }>>(`/api/user/images/${imageId}`)
}

// 8. 获取用户最近一张可用图片
export const getLatestUserImageApi = () => {
    return request.get<any, ApiResponse<any>>('/api/user/images/latest')
}

// 9. 获取用户偏好设置
export interface UserPreferences {
    preferred_scenes: string[]
    preferred_categories: string[]
    preferred_finishes: string[]
    budget_min: number
    budget_max: number
}
export const getUserPreferencesApi = () => {
    return request.get<any, ApiResponse<UserPreferences>>('/api/user/preferences')
}

// 10. 更新用户偏好设置
export const updateUserPreferencesApi = (data: UserPreferences) => {
    return request.put<any, ApiResponse<UserPreferences>>('/api/user/preferences', data)
}

// 11. 获取会员信息
export const getMembershipApi = () => {
    return request.get<any, ApiResponse<any>>('/api/user/membership')
}
