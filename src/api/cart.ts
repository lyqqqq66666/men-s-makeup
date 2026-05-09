import request from '@/utils/request'

// 获取购物车
export const getCartApi = () => {
  console.log('>>> [Debug] request getCartApi')
  return request({
    url: '/api/cart',
    method: 'GET'
  })
}

// 加入购物车
export const addToCartApi = (data: { product_id: number; quantity: number; sku_id?: string }) => {
  console.log('>>> [Debug] request addToCartApi:', data)
  return request({
    url: '/api/cart/items',
    method: 'POST',
    data
  })
}

// 更新购物车商品数量
export const updateCartItemApi = (data: { product_id: number; quantity: number }) => {
  console.log('>>> [Debug] request updateCartItemApi:', data)
  return request({
    url: '/api/cart/items',
    method: 'PUT',
    data
  })
}

// 移除购物车商品
export const removeCartItemApi = (product_id: number) => {
  console.log('>>> [Debug] request removeCartItemApi:', product_id)
  return request({
    url: `/api/cart/items/${product_id}`,
    method: 'DELETE'
  })
}

// 清空购物车
export const clearCartApi = () => {
  console.log('>>> [Debug] request clearCartApi')
  return request({
    url: '/api/cart/clear',
    method: 'POST'
  })
}

// 批量加入套装到购物车
export const addBundlesToCartApi = (data: { bundle_ids: number[] }) => {
  console.log('>>> [Debug] request addBundlesToCartApi:', data)
  return request({
    url: '/api/cart/bundles',
    method: 'POST',
    data
  })
}

// 批量设置购物车
export const bulkSetCartApi = (data: { items: any[] }) => {
  console.log('>>> [Debug] request bulkSetCartApi:', data)
  return request({
    url: '/api/cart/items/bulk',
    method: 'POST',
    data
  })
}
