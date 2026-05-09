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

// 请求拦截器 - 添加 token
llmApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器
llmApi.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('LLM API Error:', error)
    return Promise.reject(error)
  }
)

/**
 * 获取季型描述文案
 * @param {string} seasonType - 季型 (warm_spring, warm_autumn, cool_summer, cool_winter)
 * @returns {Promise<{season_type: string, description: string}>}
 */
export async function getSeasonDescription(seasonType) {
  const response = await llmApi.get('/season_description', {
    params: { season_type: seasonType }
  })
  return response.data
}

/**
 * 获取风格特征建议
 * @param {string} seasonType - 季型
 * @param {string} style - 妆容风格 (clean, business, idol)
 * @returns {Promise<{season_type: string, style: string, features: string[]}>}
 */
export async function getStyleFeatures(seasonType, style = 'clean') {
  const response = await llmApi.get('/style_features', {
    params: { season_type: seasonType, style }
  })
  return response.data
}

/**
 * 获取产品推荐理由
 * @param {string} productName - 产品名称
 * @param {string} seasonType - 季型
 * @param {string} colorInfo - 色号信息
 * @returns {Promise<{product_name: string, recommendation: string}>}
 */
export async function getProductRecommendation(productName, seasonType, colorInfo = '') {
  const response = await llmApi.get('/product_recommendation', {
    params: {
      product_name: productName,
      season_type: seasonType,
      color_info: colorInfo
    }
  })
  return response.data
}

/**
 * 批量获取推荐理由
 * @param {Array} products - 产品列表
 * @param {string} seasonType - 季型
 * @returns {Promise<Map>} - product_id -> recommendation
 */
export async function batchGetRecommendations(products, seasonType) {
  const promises = products.map(product =>
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
  const map = new Map()
  results.forEach(r => map.set(r.product_id, r.recommendation))
  return map
}

export default {
  getSeasonDescription,
  getStyleFeatures,
  getProductRecommendation,
  batchGetRecommendations
}
