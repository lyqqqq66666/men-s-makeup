import request from '../utils/request'
import type { ApiResponse } from './auth'

/**
 * 推荐模块接口定义
 */

// 1. 个性化推荐 (PCA)
export interface PersonalizedRecommendationData {
    products: any[]
    behavior_snapshot: any[]
}
export const getPersonalizedRecommendationsApi = (limit: number = 10) => {
    return request.get<any, ApiResponse<PersonalizedRecommendationData>>('/api/pca/personalized_recommendations', { params: { limit } })
}

// 2. 搭配推荐
export interface PairRecommendationData {
    source_sku_id: string
    items: any[]
}
export const getPairRecommendationsApi = (sourceSkuId: string, limit: number = 6) => {
    return request.get<any, ApiResponse<PairRecommendationData>>('/api/recommend/pairs', { 
        params: { source_sku_id: sourceSkuId, limit } 
    })
}

// 3. 推荐商品 (根据季型和分类)
export interface ProductRecommendationData {
    season: string
    category: string | null
    products: any[]
}
export const getProductRecommendationsApi = (params: { season?: string; category?: string; limit?: number; user_id?: string }) => {
    return request.get<any, ApiResponse<ProductRecommendationData>>('/api/recommend/products', { params })
}

// 4. 套装推荐
export interface BundleRecommendationData {
    bundle_name: string
    products: any[]
    total_price: number
    discount_price: number
    season: string
}
export const getBundleRecommendationsApi = (params: { season?: string; current_product?: string; user_id?: string }) => {
    return request.get<any, ApiResponse<BundleRecommendationData>>('/api/recommend/bundles', { params })
}
