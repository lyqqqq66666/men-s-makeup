/**
 * 商品 API 调用模块
 */

import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const api = axios.create({
  baseURL: `${API_BASE}/api`,
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export interface Product {
  product_id: number
  name: string
  brand: string
  price: number
  category: string
  season_type?: string
  image_url?: string
  color_hex?: string
  shade_name?: string
  tags?: string[]
  description?: string
}

export interface CartItem extends Product {
  quantity: number
  image: string
}

export async function getProducts(season?: string, category?: string, limit?: number): Promise<{products: Product[], total: number}> {
  const params: any = {}
  if (season) params.season = season
  if (category) params.category = category
  if (limit) params.limit = limit
  
  const response = await api.get('/products', { params })
  return response.data
}

export async function getProductById(id: number): Promise<Product> {
  const response = await api.get(`/products/${id}`)
  return response.data
}

export async function getRecommendedProducts(season: string, limit?: number): Promise<Product[]> {
  const params: any = { season }
  if (limit) params.limit = limit
  
  const response = await api.get('/products/recommended', { params })
  return response.data
}

export default {
  getProducts,
  getProductById,
  getRecommendedProducts
}
