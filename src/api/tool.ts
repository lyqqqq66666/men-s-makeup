import request from '@/utils/request'

// 压缩图片
export const compressImageApi = (data: FormData) => {
  console.log('>>> [Debug] request compressImageApi')
  return request({
    url: '/api/media/compress',
    method: 'POST',
    data,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 上传并预处理图片
export const processUploadImageApi = (data: FormData) => {
  console.log('>>> [Debug] request processUploadImageApi')
  return request({
    url: '/api/media/process-upload',
    method: 'POST',
    data,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}
