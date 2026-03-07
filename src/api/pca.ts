import request from '../utils/request'

/**
 * 色彩诊断接口 - 分析用户季型与推荐色号
 * @param data 包含图片文件或图片ID的 FormData
 */
export const analyzeColorType = (data: FormData) => {
    return request({
        url: '/api/pca/analyze_color_type',
        method: 'post',
        data,
        headers: { 'Content-Type': 'multipart/form-data' }
    })
}

/**
 * 基于季型的商品推荐接口
 * @param params 包含季型(season)等信息的对象
 */
export const recommendProducts = (params: { season: string; limit?: number }) => {
    return request({
        url: '/api/pca/recommend_products',
        method: 'get',
        params
    })
}
