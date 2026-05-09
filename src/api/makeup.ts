import request from '@/utils/request'

export const createMakeupSessionApi = (data: any, isFormData = false) => {
  console.log('>>> [Debug] request createMakeupSessionApi. isFormData:', isFormData)
  return request({
    url: '/api/makeup/session',
    method: 'POST',
    data,
    headers: isFormData ? { 'Content-Type': 'multipart/form-data' } : undefined
  })
}

export const applyMakeupApi = (data: { session_id: string; product_id: string; category?: string }) => {
  console.log('>>> [Debug] request applyMakeupApi:', data)
  return request({ url: '/api/makeup/apply', method: 'POST', data })
}

export const undoMakeupApi = (data: { session_id: string }) => {
  console.log('>>> [Debug] request undoMakeupApi:', data)
  return request({ url: '/api/makeup/undo', method: 'POST', data })
}

export const resetMakeupApi = (data: { session_id: string }) => {
  console.log('>>> [Debug] request resetMakeupApi:', data)
  return request({ url: '/api/makeup/reset', method: 'POST', data })
}

export const resetPartMakeupApi = (data: { session_id: string; category: string }) => {
  console.log('>>> [Debug] request resetPartMakeupApi:', data)
  return request({ url: '/api/makeup/reset-part', method: 'POST', data })
}

export const getStyleTemplatesApi = () => {
  console.log('>>> [Debug] request getStyleTemplatesApi')
  return request({ url: '/api/makeup/style-templates', method: 'GET' })
}

export const saveMakeupSchemeApi = (data: any) => {
  console.log('>>> [Debug] request saveMakeupSchemeApi:', data)
  return request({ url: '/api/makeup/schemes', method: 'POST', data })
}

export const getMakeupSchemesApi = () => {
  console.log('>>> [Debug] request getMakeupSchemesApi')
  return request({ url: '/api/makeup/schemes', method: 'GET' })
}

export const getMakeupSchemeDetailApi = (scheme_id: string) => {
  console.log('>>> [Debug] request getMakeupSchemeDetailApi:', scheme_id)
  return request({ url: `/api/makeup/schemes/${scheme_id}`, method: 'GET' })
}

export const deleteMakeupSchemeApi = (scheme_id: string) => {
  console.log('>>> [Debug] request deleteMakeupSchemeApi:', scheme_id)
  return request({ url: `/api/makeup/schemes/${scheme_id}`, method: 'DELETE' })
}

export const getMakeupSessionApi = (session_id: string) => {
  console.log('>>> [Debug] request getMakeupSessionApi:', session_id)
  return request({ url: `/api/makeup/session/${session_id}`, method: 'GET' })
}

export const scoreMakeupApi = (data: { session_id: string }) => {
  console.log('>>> [Debug] request scoreMakeupApi:', data)
  return request({ url: '/api/makeup/score', method: 'POST', data })
}
