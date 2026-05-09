import cv2
import numpy as np
import os
import face_detection  # 导入我们刚拆分出的模块

def calculate_correction_angle(landmarks):
    """计算原始矫正角度"""
    # 获取双眼中心点坐标
    left_eye_center = landmarks[160]
    right_eye_center = landmarks[385]

    left_x, left_y = left_eye_center
    right_x, right_y = right_eye_center

    # 打印调试信息：由双眼坐标判断倾斜情况
    print(f"左眼中心：({left_x}, {left_y}) | 右眼中心：({right_x}, {right_y})")
    print(f"双眼高度差（Y轴）：{right_y - left_y:.1f}（正值表示右眼低于左眼，负值相反）")

    # 计算两眼连线的倾斜弧度及角度
    dx = right_x - left_x
    dy = right_y - left_y
    angle_rad = np.arctan2(dy, dx)
    tilt_angle = angle_rad * 180 / np.pi

    # 根据高度差确定原始倾斜方向
    if dy > 0:
        original_correction = -tilt_angle
        original_direction = "顺时针"
    elif dy < 0:
        original_correction = -tilt_angle
        original_direction = "逆时针"
    else:
        original_correction = 0
        original_direction = "无"

    # 计算反向旋转角度进行矫正
    final_correction = -original_correction
    final_direction = "逆时针" if original_direction == "顺时针" else "顺时针" if original_direction != "无" else "无"

    # 限制最大矫正角度，避免过度旋转
    final_correction = np.clip(final_correction, -30, 30)
    print(f"检测到倾斜：{original_direction} {abs(original_correction):.2f}° → 计划矫正：{final_direction} {abs(final_correction):.2f}°")
    return final_correction, final_direction

def get_average_border_color(image, thickness=10):
    """
    计算图像边缘的平均颜色，用于背景填充。
    取上下左右边缘的像素平均值。
    """
    h, w = image.shape[:2]
    
    # 提取四个边缘区域
    # 注意避免重叠部分重复计算太多，但求平均影响不大
    regions = []
    if h > thickness:
        regions.append(image[0:thickness, :]) # Top
        regions.append(image[h-thickness:h, :]) # Bottom
    if w > thickness:
        regions.append(image[:, 0:thickness]) # Left
        regions.append(image[:, w-thickness:w]) # Right
        
    if not regions:
        return (255, 255, 255) # Fallback white

    # 计算所有边缘像素的平均值
    total_avg = np.zeros(3)
    count = 0
    for roi in regions:
        avg = np.mean(roi, axis=(0, 1))
        total_avg += avg
        count += 1
        
    final_avg = total_avg / count
    return tuple(map(int, final_avg))

def rotate_image(image, angle):
    """基于 OpenCV 的旋转函数，返回旋转矩阵和旋转后原始图像顶点的坐标"""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)

    rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale=1.0)

    # 计算旋转后的新图像尺寸
    cos_angle = np.abs(rotation_matrix[0, 0])
    sin_angle = np.abs(rotation_matrix[0, 1])
    new_w = int((h * sin_angle) + (w * cos_angle))
    new_h = int((h * cos_angle) + (w * sin_angle))

    # 调整旋转矩阵的平移分量，以防图像被裁剪
    rotation_matrix[0, 2] += (new_w / 2) - center[0]
    rotation_matrix[1, 2] += (new_h / 2) - center[1]

    # 边界填充：使用复制边界模式 (Replicate)
    # 策略：不使用纯色填充，而是利用边缘像素进行延伸，视觉上更自然
    rotated_image = cv2.warpAffine(
        image, rotation_matrix, (new_w, new_h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )

    # 计算原始图像四个顶点在旋转后的新坐标
    orig_corners = np.array([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]], dtype=np.float32)
    rotated_corners = cv2.transform(np.array([orig_corners]), rotation_matrix)[0]
    rotated_corners = np.round(rotated_corners).astype(int)  # 转换为整数坐标以方便绘图

    return rotated_image, rotated_corners

# def crop_by_rotated_corners(rotated_image, rotated_corners):
#     """
#     (已弃用) 根据矫正后原始图像的四个顶点裁剪矩形
#     保留此函数仅供参考，新逻辑不再调用
#     """
#     # ... (function body omitted for brevity if not used) ...
#     pass 

def face_correction_ultimate(image_path, output_dir="correction_results_ultimate", output_filename=None):
    """主函数：人脸识别与矫正 + 无损旋转扩展"""
    # 读取图像数据
    image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError(f"无法读取图像：{image_path}")

    os.makedirs(output_dir, exist_ok=True)

    # 步骤1：检测人脸和关键点 (调用 face_detection 模块)
    face_rect, landmarks = face_detection.detect_face_landmarks_mediapipe(image)
    
    if face_rect is None:
        print("未检测到人脸！")
        save_path = os.path.join(output_dir, "无脸图像.jpg")
        cv2.imencode('.jpg', image)[1].tofile(save_path)
        return

    x1, y1, x2, y2 = face_rect
    # 步骤2：计算矫正所需的倾斜角度
    correction_angle, direction = calculate_correction_angle(landmarks)


    # 步骤3：执行矫正
    if abs(correction_angle) > 0.5:
        # 使用自定义的 rotate_image 函数进行无损旋转
        corrected_image, rotated_corners = rotate_image(image, correction_angle)
        
        # 保持完整背景，不进行额外裁剪
        final_image = corrected_image
        print(f"已完成人脸矫正 ({direction} {abs(correction_angle):.1f}° -> 无损扩展及边缘复制填充)")
            
    else:
        corrected_image = image.copy()
        final_image = image.copy()
        rotated_corners = [] # 无需旋转
        print("检测到人脸已处于水平状态，无需矫正")

    # 步骤5：结果可视化（在图像上标注）
    result_image = corrected_image.copy()
    
    if len(rotated_corners) > 0:
        # 绘制原始图像旋转后的四个顶点
        for i, (x, y) in enumerate(rotated_corners):
            cv2.circle(result_image, (x, y), 6, (0, 0, 255), -1)
            cv2.putText(result_image, f"Point {i}", (x+10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    # 注意：如果旋转了图像，原始的人脸框坐标需要映射到新图才能准确绘制。
    # 为保持逻辑简洁，此处省略复杂映射，仅在原图未旋转或简单展示时使用。
    
    # 历史代码保留：用于调试的文字标注（已注释，仅在控制台输出日志）
    # info_text = f"Correction: {direction} {abs(correction_angle):.1f}"
    # cv2.putText(
    #    final_image, info_text, (20, 50),
    #    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2
    # )

    # 保存结果
    # 强制统一为 JPG 格式以保证兼容性
    if output_filename:
        base_name = os.path.splitext(output_filename)[0]
        final_save_name = f"{base_name}.jpg"
    else:
        final_save_name = "result.jpg"
        
    save_path = os.path.join(output_dir, final_save_name)
    
    # 写入文件
    result, encoded_img = cv2.imencode('.jpg', final_image)
    if result:
        encoded_img.tofile(save_path)
    print(f"  -> 结果已保存至: {final_save_name} (格式: JPG)")
    
    # 返回信息供数据库记录使用
    return {
        'angle': correction_angle,
        'save_path': save_path,
        'filename': final_save_name
    }

if __name__ == "__main__":
    # 图像路径
    INPUT_IMAGE_PATH = "photo.jpg"
    
    import os
    if os.path.exists(INPUT_IMAGE_PATH):
        try:
            face_correction_ultimate(INPUT_IMAGE_PATH)
        except Exception as e:
            print(f"程序出错：{str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            face_detection.close_face_mesh()
    else:
        print("face_correction 模块已加载 (未找到测试图片 photo.jpg)")
