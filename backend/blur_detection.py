import cv2
import numpy as np

# def detect_blurriness(image_input, threshold=35, edge_ratio=0.2):
#     """
#     检测图片的模糊程度，重点分析中心和边缘区域

#     参数:
#         image_input: 图片文件路径 或 Numpy图像数组(BGR)
#         threshold: 清晰度阈值，默认调整为 35 (针对Face ROI)
#         edge_ratio: 边缘区域占整体图片的比例

#     返回:
#         dict: 包含整体、中心、边缘的清晰度值和模糊判断结果
#     """
#     # 如果是字符串，则作为路径读取；否则作为图像数组处理
#     if isinstance(image_input, str):
#         image = cv2.imdecode(np.fromfile(image_input, dtype=np.uint8), cv2.IMREAD_COLOR)
#         if image is None:
#             raise ValueError(f"无法读取图片: {image_input}")
#     else:
#         # 复制一份以免修改原图
#         image = image_input.copy()

#     if image is None or image.size == 0:
#         raise ValueError("输入图像为空")

#     # [新增] 图像标准化：如果有且尺寸过大，缩小到宽 500
#     current_h, current_w = image.shape[:2]
#     target_w = 500
#     if current_w > target_w:
#         scale = target_w / current_w
#         new_w = target_w
#         new_h = int(current_h * scale)
#         image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

#     gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#     height, width = gray.shape

#     # 1. 计算整体图片的清晰度（拉普拉斯方差）
#     laplacian = cv2.Laplacian(gray, cv2.CV_64F)
#     overall_var = np.var(laplacian)

#     # 2. 提取中心区域并计算清晰度
#     center_h_start = int(height * 0.25)
#     center_h_end = int(height * 0.75)
#     center_w_start = int(width * 0.25)
#     center_w_end = int(width * 0.75)
#     center_region = gray[center_h_start:center_h_end, center_w_start:center_w_end]
#     center_laplacian = cv2.Laplacian(center_region, cv2.CV_64F)
#     center_var = np.var(center_laplacian)

#     # 3. 提取边缘区域并计算清晰度
#     # 边缘区域包括：顶部、底部、左侧、右侧四条边
#     edge_height = int(height * edge_ratio)
#     edge_width = int(width * edge_ratio)

#     # 顶部边缘
#     top_edge = gray[0:edge_height, :]
#     # 底部边缘
#     bottom_edge = gray[height-edge_height:height, :]
#     # 左侧边缘（排除顶部和底部已计算的部分）
#     left_edge = gray[edge_height:height-edge_height, 0:edge_width]
#     # 右侧边缘（排除顶部和底部已计算的部分）
#     right_edge = gray[edge_height:height-edge_height, width-edge_width:width]

#     # 分别计算每个边缘区域的清晰度，再取平均值
#     # 计算顶部边缘清晰度
#     top_laplacian = cv2.Laplacian(top_edge, cv2.CV_64F)
#     top_var = np.var(top_laplacian)

#     # 计算底部边缘清晰度
#     bottom_laplacian = cv2.Laplacian(bottom_edge, cv2.CV_64F)
#     bottom_var = np.var(bottom_laplacian)

#     # 计算左侧边缘清晰度
#     left_laplacian = cv2.Laplacian(left_edge, cv2.CV_64F)
#     left_var = np.var(left_laplacian)

#     # 计算右侧边缘清晰度
#     right_laplacian = cv2.Laplacian(right_edge, cv2.CV_64F)
#     right_var = np.var(right_laplacian)

#     # 边缘区域整体清晰度：取四个边缘的平均值
#     edge_var = np.mean([top_var, bottom_var, left_var, right_var])

#     # 4. 判断是否模糊
#     is_blurry_overall = overall_var < threshold
#     is_blurry_center = center_var < threshold
#     is_blurry_edge = edge_var < threshold

#     # 综合判断（只要中心或边缘有一个模糊，就认为图片模糊）
#     is_blurry = is_blurry_center or is_blurry_edge

#     return {
#         "overall_clarity": round(overall_var, 2),
#         "center_clarity": round(center_var, 2),
#         "edge_clarity": round(edge_var, 2),
#         "top_edge_clarity": round(top_var, 2),
#         "bottom_edge_clarity": round(bottom_var, 2),
#         "left_edge_clarity": round(left_var, 2),
#         "right_edge_clarity": round(right_var, 2), # Corrected from edge_var to right_var
#         "is_blurry_overall": is_blurry_overall,
#         "is_blurry_center": is_blurry_center,
#         "is_blurry_edge": is_blurry_edge,
#         "is_blurry": is_blurry,
#         "threshold": threshold
#     }


def detect_blur_with_landmarks(image, landmarks, threshold=50, debug_prefix=""):
    """
    基于人脸关键点的精准模糊检测。
    仅检测眼睛和嘴巴区域的清晰度，忽略皮肤区域。
    
    参数:
        image: 原始图像 (BGR numpy array)
        landmarks: 人脸关键点列表 [(x,y), ...]
        threshold: 清晰度阈值
        debug_prefix: 调试文件名前缀（例如文件名），若不为空则会将ROI保存到 images/outputs/debug_rois/
    
    返回:
        dict: 包含评分和判断结果
    """
    if image is None or len(landmarks) == 0:
        return {"is_blurry": True, "score": 0.0, "details": "No image or landmarks"}
    
    h, w = image.shape[:2]
    
    # 左眼, 右眼, 嘴巴 (外轮廓)
    LEFT_EYE_INDICES = [33, 133, 157, 158, 159, 160, 161, 246, 7, 163, 144, 145, 153, 154, 155, 173]
    RIGHT_EYE_INDICES = [362, 263, 384, 385, 386, 387, 388, 466, 249, 390, 373, 374, 380, 381, 382, 398]
    LIPS_INDICES = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
    
    saved_debug_paths = []

    def get_roi_variance(indices, name, expand=10):
        # 提取关键点
        points = []
        for idx in indices:
            if idx < len(landmarks):
                points.append(landmarks[idx])
        
        if not points:
            return 0.0
            
        points = np.array(points, dtype=np.int32)
        
        # 计算包围盒
        x_min, y_min = np.min(points, axis=0)
        x_max, y_max = np.max(points, axis=0)
        
        # 适当外扩
        x_min = max(0, x_min - expand)
        y_min = max(0, y_min - expand)
        x_max = min(w, x_max + expand)
        y_max = min(h, y_max + expand)
        
        # 裁剪ROI
        roi = image[y_min:y_max, x_min:x_max]
        
        if roi.size == 0:
            return 0.0
            
        # 尺寸标准化
        roi_h, roi_w = roi.shape[:2]
        if roi_w > 200:
            scale = 200 / roi_w
            roi = cv2.resize(roi, (200, int(roi_h * scale)))
            
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # [关键改进] 直方图均衡化：增强对比度
        # 这对于处理光线柔和但其实很清晰的图片非常有效
        gray_roi_eq = cv2.equalizeHist(gray_roi)
        
        # 保存调试图片
        if debug_prefix:
            import os
            # 使用相对于模块的绝对路径
            base_dir = os.path.dirname(os.path.abspath(__file__))
            debug_dir = os.path.join(base_dir, "database", "debug_rois") # 按要求存放在数据库目录中
            
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir, exist_ok=True)
                
            filename = f"{debug_prefix}_{name}.jpg"
            save_path = os.path.join(debug_dir, filename)
            
            cv2.imencode('.jpg', roi)[1].tofile(save_path)
            
            # 记录数据库用的相对路径
            rel_path = os.path.join("database", "debug_rois", filename)
            saved_debug_paths.append(rel_path)

        return cv2.Laplacian(gray_roi_eq, cv2.CV_64F).var()

    left_eye_score = get_roi_variance(LEFT_EYE_INDICES, "left_eye")
    right_eye_score = get_roi_variance(RIGHT_EYE_INDICES, "right_eye")
    mouth_score = get_roi_variance(LIPS_INDICES, "mouth")
    
    final_score = max(left_eye_score, right_eye_score, mouth_score)
    
    return {
        "is_blurry": final_score < threshold,
        "score": round(final_score, 2),
        "details": f"L_Eye: {int(left_eye_score)}, R_Eye: {int(right_eye_score)}, Mouth: {int(mouth_score)}",
        "debug_paths": saved_debug_paths
    }

if __name__ == "__main__":
    # 测试示例
    # 图片路径
    image_path = "photo.jpg"
    # 注意：如果同一级目录没有photo.jpg，这里会报错，这只是一个测试入口
    
    import os
    if os.path.exists(image_path):
        try:
            result = detect_blurriness(image_path)
            print(f"检测结果：{result['is_blurry']}")
        except Exception as e:
            print(f"检测出错: {e}")
    else:
        print("blur_detection 模块已加载 (未找到测试图片 photo.jpg)")
