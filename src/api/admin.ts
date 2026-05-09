import request from '@/utils/request'

export const adminGetProductsApi = () => {
  console.log('>>> [Debug] request adminGetProductsApi')
  return request({ url: '/api/admin/products', method: 'GET' })
}

export const adminCreateProductApi = (data: any) => {
  console.log('>>> [Debug] request adminCreateProductApi:', data)
  return request({ url: '/api/admin/products', method: 'POST', data })
}

export const adminGetProductDetailApi = (product_id: number) => {
  console.log('>>> [Debug] request adminGetProductDetailApi:', product_id)
  return request({ url: `/api/admin/products/${product_id}`, method: 'GET' })
}

export const adminUpdateProductApi = (product_id: number, data: any) => {
  console.log('>>> [Debug] request adminUpdateProductApi:', { product_id, data })
  return request({ url: `/api/admin/products/${product_id}`, method: 'PUT', data })
}

export const adminDeleteProductApi = (product_id: number) => {
  console.log('>>> [Debug] request adminDeleteProductApi:', product_id)
  return request({ url: `/api/admin/products/${product_id}`, method: 'DELETE' })
}
