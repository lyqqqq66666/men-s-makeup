import request from '@/utils/request'
import type { ApiResponse } from './auth'

// 1. 定义响应中 data 字段的数据类型
export interface HealthData {
    status: string
}

// 2. 封装 API 请求函数
export const getHealthApi = () => {
    // 泛型参数说明：第一个 any 是请求参数类型(此处无)，第二个是响应数据类型
    // 注意：这里的 URL 是去掉前面 BaseURL 后的相对路径 '/health'
    return request.get<any, ApiResponse<HealthData>>('/api/health')
}
