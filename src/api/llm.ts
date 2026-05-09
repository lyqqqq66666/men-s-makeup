/**
 * LLM API 调用模块
 * 用于调用后端 DeepSeek LLM 接口
 */

import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const llmApi = axios.create({
  baseURL: `${API_BASE}/api/llm`,
  timeout: 30000,
})

llmApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

llmApi.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('LLM API Error:', error)
    return Promise.reject(error)
  }
)

export async function getSeasonDescription(seasonType: string): Promise<{season_type: string, description: string}> {
  const response = await llmApi.get('/season_description', {
    params: { season_type: seasonType }
  })
  return response.data
}

export async function getStyleFeatures(seasonType: string, style: string = 'clean'): Promise<{season_type: string, style: string, features: string[]}> {
  const response = await llmApi.get('/style_features', {
    params: { season_type: seasonType, style }
  })
  return response.data
}

export async function getProductRecommendation(productName: string, seasonType: string, colorInfo: string = ''): Promise<{product_name: string, recommendation: string}> {
  const response = await llmApi.get('/product_recommendation', {
    params: {
      product_name: productName,
      season_type: seasonType,
      color_info: colorInfo
    }
  })
  return response.data
}

interface Product {
  product_id: number
  name: string
  shade_name?: string
  color_hex?: string
}

export async function batchGetRecommendations(products: Product[], seasonType: string): Promise<Map<number, string>> {
  const promises = products.map((product: Product) =>
    getProductRecommendation(
      product.name,
      seasonType,
      product.shade_name || product.color_hex || ''
    ).then(result => ({
      product_id: product.product_id,
      recommendation: result.recommendation
    })).catch(() => ({
      product_id: product.product_id,
      recommendation: ''
    }))
  )
  
  const results = await Promise.all(promises)
  const map = new Map<number, string>()
  results.forEach(r => map.set(r.product_id, r.recommendation))
  return map
}

export default {
  getSeasonDescription,
  getStyleFeatures,
  getProductRecommendation,
  batchGetRecommendations
}
