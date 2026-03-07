import request from '../utils/request'

/**
 * 一键妆容渲染接口 - 基于风格应用完整妆效
 * @param data { image_id: string, style: string }
 */
export const applyFullStyle = (data: { image_id: string; style: string }) => {
    return request({
        url: '/api/makeup/apply-style',
        method: 'post',
        data
    })
}

/**
 * 局部累加渲染接口 - 单独应用底妆、眉毛、眼妆等
 * @param data { image_id: string, step: 'base'|'eyebrow'|'eye'|'contour'|'lip', product_id?: number }
 */
export const applyMakeupStep = (data: {
    image_id: string;
    step: 'base' | 'eyebrow' | 'eye' | 'contour' | 'lip';
    product_id?: number | string
}) => {
    return request({
        url: '/api/makeup/apply-step',
        method: 'post',
        data
    })
}

/**
 * 撤销上一步操作接口
 * @param data { session_id: string }
 */
export const undoMakeup = (data: { session_id: string }) => {
    return request({
        url: '/api/makeup/undo',
        method: 'post',
        data
    })
}

/**
 * 重置妆容接口 - 回到原始/矫正后的状态
 * @param data { session_id: string }
 */
export const resetMakeup = (data: { session_id: string }) => {
    return request({
        url: '/api/makeup/reset',
        method: 'post',
        data
    })
}

/**
 * 获取套装推荐接口
 * @param params { season: string }
 */
export const getSetRecommendations = (params: { season: string }) => {
    return request({
        url: '/api/makeup/sets',
        method: 'get',
        params
    })
}

/**
 * 保存妆容方案接口
 * @param data { name: string, image_id: string, configuration: any }
 */
export const saveMakeupPlan = (data: { name: string; image_id: string; configuration: any }) => {
    return request({
        url: '/api/makeup/plan/save',
        method: 'post',
        data
    })
}

/**
 * 获取用户方案列表接口
 */
export const getPlanList = () => {
    return request({
        url: '/api/makeup/plans',
        method: 'get'
    })
}
