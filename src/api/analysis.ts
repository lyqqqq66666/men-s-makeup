import request from '@/utils/request'

export interface AnalyzePCAParams {
  image: File
  user_id?: number
}

// 分析个人季型 (POST /api/pca/analyze)
export const analyzePCAApi = (data: FormData) => {
  console.log('>>> [Debug] request analyzePCAApi:', data)
  return request({
    url: '/api/pca/analyze',
    method: 'POST',
    data,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
