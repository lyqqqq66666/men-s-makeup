"""
分步上妆模块 - Step-by-Step Makeup Application
基于人脸关键点检测，实现局部妆容叠加

功能：
1. 底妆处理 - 肤色均匀
2. 眉部处理 - 眉形修饰
3. 眼部处理 - 眼影/眼线
4. 唇部处理 - 唇色上妆
5. 轮廓处理 - 修容高光

使用 MediaPipe Face Mesh 的 468 关键点进行精确定位
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional
from PIL import Image

class StepMakeupEngine:
    """分步上妆引擎"""
    
    # MediaPipe Face Mesh 关键点索引定义
    # 来源: MediaPipe Face Mesh (468个关键点)
    
    # 眉部关键点
    LEFT_EYEBROW = list(range(336, 346))  # 左眉毛
    RIGHT_EYEBROW = list(range(346, 356))  # 右眉毛
    
    # 眼部关键点
    LEFT_EYE = [33, 133, 160, 159, 158, 157, 173, 133]  # 左眼轮廓
    RIGHT_EYE = [362, 263, 387, 386, 385, 384, 398, 263]  # 右眼轮廓
    LEFT_IRIS = 468  # 左眼虹膜中心
    RIGHT_IRIS = 473  # 右眼虹膜中心
    
    # 唇部关键点
    UPPER_LIP = list(range(61, 76))  # 上唇
    LOWER_LIP = list(range(61, 81))  # 下唇
    MOUTH_OUTER = list(range(61, 81))  # 嘴唇外轮廓
    
    # 面部轮廓关键点
    FACE_OVAL = list(range(10, 118))  # 面部外轮廓（简化）
    
    # 鼻部关键点
    NOSE_TIP = 4
    NOSE_BRIDGE = list(range(168, 174))
    
    def __init__(self):
        self.landmarks = None
        self.image_shape = None
    
    def set_face_data(self, landmarks: np.ndarray, image_shape: Tuple[int, int, int]):
        """
        设置人脸数据
        
        Args:
            landmarks: MediaPipe 检测的468个关键点坐标 (N, 2)
            image_shape: 图像尺寸 (H, W, C)
        """
        self.landmarks = landmarks
        self.image_shape = image_shape
    
    def get_landmark_points(self, indices: List[int]) -> np.ndarray:
        """根据索引获取关键点坐标"""
        if self.landmarks is None:
            raise ValueError("请先调用 set_face_data 设置人脸数据")
        return self.landmarks[indices]
    
    def create_region_mask(self, points: np.ndarray, image_shape: Tuple[int, int], 
                          dilation: int = 5, blur: int = 15) -> np.ndarray:
        """
        根据关键点创建区域遮罩
        
        Args:
            points: 关键点坐标 (N, 2)
            image_shape: 图像尺寸
            dilation: 膨胀程度
            blur: 模糊程度（用于边缘过渡）
        
        Returns:
            0-1 范围的灰度遮罩图
        """
        h, w = image_shape[:2]
        mask = np.zeros((h, w), dtype=np.float32)
        
        # 将关键点转换为整数坐标
        points_int = np.array(points, dtype=np.int32)
        
        # 使用凸包填充区域
        hull = cv2.convexHull(points_int)
        cv2.fillConvexPoly(mask, hull, 1)
        
        # 形态学操作：膨胀 + 模糊
        if dilation > 0:
            kernel = np.ones((dilation, dilation), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=1)
        
        if blur > 0:
            mask = cv2.GaussianBlur(mask, (blur, blur), 0)
        
        return mask
    
    def apply_color_overlay(self, image: np.ndarray, mask: np.ndarray, 
                          hex_color: str, opacity: float = 0.6) -> np.ndarray:
        """
        在指定区域应用颜色叠加
        
        Args:
            image: BGR 图像
            mask: 0-1 范围的遮罩
            hex_color: 十六进制颜色，如 "#E07A5F"
            opacity: 透明度 (0-1)
        
        Returns:
            处理后的 BGR 图像
        """
        # 转换颜色
        hex_color = hex_color.lstrip('#')
        rgb = np.array([int(hex_color[i:i+2], 16) for i in (0, 2, 4)])
        bgr = rgb[::-1]  # RGB to BGR
        
        # 创建颜色层
        color_layer = np.zeros_like(image)
        color_layer[:, :] = bgr
        
        # 调整遮罩透明度
        alpha = mask * opacity
        
        # 混合
        result = image.copy()
        for c in range(3):
            result[:, :, c] = np.clip(
                image[:, :, c] * (1 - alpha) + color_layer[:, :, c] * alpha,
                0, 255
            ).astype(np.uint8)
        
        return result
    
    def apply_lip_makeup(self, image: np.ndarray, hex_color: str = "#B14A5A",
                        opacity: float = 0.7) -> np.ndarray:
        """唇部上妆"""
        try:
            # 获取唇部关键点
            upper_lip_pts = self.get_landmark_points(self.UPPER_LIP)
            lower_lip_pts = self.get_landmark_points(self.LOWER_LIP)
            
            # 合并上下唇关键点
            lip_points = np.vstack([upper_lip_pts, lower_lip_pts])
            
            # 创建唇部遮罩
            lip_mask = self.create_region_mask(
                lip_points, 
                image.shape,
                dilation=3,
                blur=11
            )
            
            # 应用唇色
            result = self.apply_color_overlay(image, lip_mask, hex_color, opacity)
            
            # 可选：添加轻微光泽
            result = self.add_lip_gloss(result, lip_mask)
            
            return result
        except Exception as e:
            print(f"唇部上妆失败: {e}")
            return image
    
    def add_lip_gloss(self, image: np.ndarray, lip_mask: np.ndarray) -> np.ndarray:
        """为唇部添加光泽效果"""
        # 创建高光遮罩（嘴唇中心区域）
        gloss_mask = cv2.GaussianBlur(lip_mask, (21, 21), 0)
        gloss_mask = np.clip(gloss_mask * 0.3, 0, 0.3)
        
        # 添加白色高光
        highlight = np.zeros_like(image)
        highlight[:, :] = [255, 255, 255]
        
        result = image.copy()
        for c in range(3):
            result[:, :, c] = np.clip(
                image[:, :, c] + highlight[:, :, c] * gloss_mask,
                0, 255
            ).astype(np.uint8)
        
        return result
    
    def apply_eye_makeup(self, image: np.ndarray, hex_color: str = "#6B4423",
                        is_left: bool = True, opacity: float = 0.5) -> np.ndarray:
        """眼部上妆（眼影）"""
        try:
            # 选择眼睛
            eye_points = self.get_landmark_points(self.LEFT_EYE) if is_left \
                        else self.get_landmark_points(self.RIGHT_EYE)
            
            # 创建眼部遮罩（稍微扩展上方区域作为眼影区域）
            eye_center = np.mean(eye_points, axis=0)
            extended_points = eye_points.copy()
            
            # 向上扩展30%
            y_min = np.min(eye_points[:, 1])
            extension = int((eye_center[1] - y_min) * 0.3)
            extended_points[:, 1] -= extension
            
            # 创建遮罩
            eye_mask = self.create_region_mask(
                extended_points,
                image.shape,
                dilation=2,
                blur=15
            )
            
            # 应用眼影颜色
            result = self.apply_color_overlay(image, eye_mask, hex_color, opacity)
            
            return result
        except Exception as e:
            print(f"眼部上妆失败: {e}")
            return image
    
    def apply_eyebrow_makeup(self, image: np.ndarray, hex_color: str = "#2C2C2C",
                           is_left: bool = True, opacity: float = 0.8) -> np.ndarray:
        """眉部上妆"""
        try:
            # 选择眉毛
            brow_points = self.get_landmark_points(self.LEFT_EYEBROW) if is_left \
                         else self.get_landmark_points(self.RIGHT_EYEBROW)
            
            # 创建眉部遮罩
            brow_mask = self.create_region_mask(
                brow_points,
                image.shape,
                dilation=4,
                blur=9
            )
            
            # 应用眉色
            result = self.apply_color_overlay(image, brow_mask, hex_color, opacity)
            
            return result
        except Exception as e:
            print(f"眉部上妆失败: {e}")
            return image
    
    def apply_base_makeup(self, image: np.ndarray, intensity: float = 0.15) -> np.ndarray:
        """底妆处理 - 肤色均匀化"""
        try:
            # 获取面部轮廓
            face_points = self.get_landmark_points(self.FACE_OVAL)
            
            # 创建面部遮罩
            face_mask = self.create_region_mask(
                face_points,
                image.shape,
                dilation=10,
                blur=25
            )
            
            # 计算原图肤色平均值
            h, w = image.shape[:2]
            mask_2d = face_mask[:, :, np.newaxis] if len(face_mask.shape) == 2 else face_mask
            
            # 平滑肤色
            blurred = cv2.GaussianBlur(image, (31, 31), 0)
            
            # 混合
            result = image.copy()
            for c in range(3):
                result[:, :, c] = np.clip(
                    image[:, :, c] * (1 - mask_2d * intensity) + 
                    blurred[:, :, c] * mask_2d * intensity,
                    0, 255
                ).astype(np.uint8)
            
            return result
        except Exception as e:
            print(f"底妆处理失败: {e}")
            return image
    
    def apply_contour_makeup(self, image: np.ndarray, highlight_color: str = "#F5E6D3",
                           shadow_color: str = "#8B7355", intensity: float = 0.25) -> np.ndarray:
        """轮廓处理 - 修容高光"""
        try:
            h, w = image.shape[:2]
            result = image.copy()
            
            # 颧骨高光区域
            cheek_points = np.array([
                [int(w * 0.3), int(h * 0.5)],
                [int(w * 0.35), int(h * 0.55)],
                [int(w * 0.4), int(h * 0.5)],
                [int(w * 0.35), int(h * 0.48)]
            ], dtype=np.int32)
            
            cheek_mask = self.create_region_mask(cheek_points, image.shape, dilation=15, blur=21)
            result = self.apply_color_overlay(result, cheek_mask, highlight_color, intensity)
            
            # 鼻梁高光
            nose_bridge = np.array([
                [int(w * 0.5), int(h * 0.35)],
                [int(w * 0.5), int(h * 0.55)],
            ], dtype=np.int32)
            nose_mask = self.create_region_mask(nose_bridge, image.shape, dilation=8, blur=15)
            result = self.apply_color_overlay(result, nose_mask, highlight_color, intensity * 0.7)
            
            return result
        except Exception as e:
            print(f"轮廓处理失败: {e}")
            return image
    
    def process_step_by_step(self, image: Image.Image, steps: List[Dict]) -> Image.Image:
        """
        分步处理妆容
        
        Args:
            image: PIL Image
            steps: 妆容步骤列表，格式如:
                [
                    {"type": "base", "params": {"intensity": 0.15}},
                    {"type": "lip", "params": {"hex_color": "#B14A5A", "opacity": 0.7}},
                    {"type": "eye", "params": {"hex_color": "#6B4423", "is_left": True, "opacity": 0.5}},
                    {"type": "brow", "params": {"hex_color": "#2C2C2C", "is_left": True, "opacity": 0.8}},
                ]
        
        Returns:
            处理后的 PIL Image
        """
        # 转换图像
        img_array = np.array(image)
        if img_array.shape[2] == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        elif len(img_array.shape) == 2:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
        else:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # 这里假设已经通过 face_detection 模块获取了关键点
        # 实际使用时需要先调用 detect_face_landmarks_mediapipe
        
        result = img_array
        
        # 按顺序执行每一步
        for step in steps:
            step_type = step.get("type", "")
            params = step.get("params", {})
            
            if step_type == "base":
                intensity = params.get("intensity", 0.15)
                result = self.apply_base_makeup(result, intensity)
                
            elif step_type == "lip":
                hex_color = params.get("hex_color", "#B14A5A")
                opacity = params.get("opacity", 0.7)
                result = self.apply_lip_makeup(result, hex_color, opacity)
                
            elif step_type == "eye":
                hex_color = params.get("hex_color", "#6B4423")
                is_left = params.get("is_left", True)
                opacity = params.get("opacity", 0.5)
                result = self.apply_eye_makeup(result, hex_color, is_left, opacity)
                
            elif step_type == "brow":
                hex_color = params.get("hex_color", "#2C2C2C")
                is_left = params.get("is_left", True)
                opacity = params.get("opacity", 0.8)
                result = self.apply_eyebrow_makeup(result, hex_color, is_left, opacity)
                
            elif step_type == "contour":
                highlight = params.get("highlight_color", "#F5E6D3")
                shadow = params.get("shadow_color", "#8B7355")
                intensity = params.get("intensity", 0.25)
                result = self.apply_contour_makeup(result, highlight, shadow, intensity)
        
        # 转回 PIL Image
        result_bgr = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        return Image.fromarray(result_bgr)


def quick_step_makeup(image_path: str, output_path: str, style: str = "clean"):
    """
    快速分步上妆函数
    
    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径
        style: 妆容风格 ("clean", "business", "idol")
    """
    # 导入依赖模块
    import face_detection
    from PIL import Image
    
    # 加载图片
    image = Image.open(image_path)
    img_array = np.array(image)
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # 检测人脸
    face_rect, landmarks = face_detection.detect_face_landmarks_mediapipe(img_bgr)
    
    if face_rect is None:
        print("未检测到人脸！")
        return False
    
    # 初始化上妆引擎
    engine = StepMakeupEngine()
    engine.set_face_data(landmarks, img_bgr.shape)
    
    # 根据风格定义步骤
    style_configs = {
        "clean": [
            {"type": "base", "params": {"intensity": 0.1}},
            {"type": "lip", "params": {"hex_color": "#C98B7B", "opacity": 0.5}},
        ],
        "business": [
            {"type": "base", "params": {"intensity": 0.15}},
            {"type": "brow", "params": {"hex_color": "#2C2C2C", "is_left": True, "opacity": 0.7}},
            {"type": "brow", "params": {"hex_color": "#2C2C2C", "is_left": False, "opacity": 0.7}},
            {"type": "lip", "params": {"hex_color": "#B87A6A", "opacity": 0.6}},
            {"type": "contour", "params": {"intensity": 0.2}},
        ],
        "idol": [
            {"type": "base", "params": {"intensity": 0.2}},
            {"type": "eye", "params": {"hex_color": "#6B4423", "is_left": True, "opacity": 0.4}},
            {"type": "eye", "params": {"hex_color": "#6B4423", "is_left": False, "opacity": 0.4}},
            {"type": "brow", "params": {"hex_color": "#4A3728", "is_left": True, "opacity": 0.6}},
            {"type": "brow", "params": {"hex_color": "#4A3728", "is_left": False, "opacity": 0.6}},
            {"type": "lip", "params": {"hex_color": "#E07A5F", "opacity": 0.7}},
            {"type": "contour", "params": {"intensity": 0.25}},
        ],
    }
    
    steps = style_configs.get(style, style_configs["clean"])
    
    # 处理
    result = engine.process_step_by_step(image, steps)
    
    # 保存
    result.save(output_path)
    print(f"分步上妆完成: {output_path}")
    return True


if __name__ == "__main__":
    print("分步上妆模块已加载")
    print("使用方法:")
    print("  from step_makeup import StepMakeupEngine, quick_step_makeup")
    print("  quick_step_makeup('input.jpg', 'output.jpg', style='clean')")
