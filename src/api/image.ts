import request from '../utils/request'

/**
 * 人脸识别接口 - 检测并获取面部特征点
 * @param data 包含图片文件的 FormData
 */
export const detectFace = (data: FormData) => {
    return request({
        url: '/api/image/detect-face',
        method: 'post',
        data,
        headers: { 'Content-Type': 'multipart/form-data' }
    })
}

/**
 * 模糊检测接口 - 评估上传图片的清晰度
 * @param data 包含图片文件的 FormData
 */
export const detectBlur = (data: FormData) => {
    return request({
        url: '/api/image/detect-blur',
        method: 'post',
        data,
        headers: { 'Content-Type': 'multipart/form-data' }
    })
}

/**
 * 智能图像矫正接口 - 自动调整人像角度、光影与清晰度
 * @param data 包含图片文件的 FormData
 */
export const smartCorrect = (data: FormData) => {
    return request({
        url: '/api/image/smart-correct',
        method: 'post',
        data,
        headers: { 'Content-Type': 'multipart/form-data' }
    })
}

/**
 * 批量处理接口 (可选) - 一次性完成识别、检测与矫正
 * @param data 包含图片文件的 FormData
 */
export const processImageFull = (data: FormData) => {
    return request({
        url: '/api/image/process-full',
        method: 'post',
        data,
        headers: { 'Content-Type': 'multipart/form-data' }
    })
}
