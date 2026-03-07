# 化妆品模拟上妆核心逻辑示例 (用于软著2源代码)

import cv2
import numpy as np
import mediapipe as mp

class CosmeticApplier:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5
        )
        
        # 嘴唇关键点索引 (MediaPipe V2)
        self.LIPS_INDICES = [
            61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 178, 88, 95,
            185, 40, 39, 37, 0, 267, 269, 270, 409, 415, 310, 311, 312, 13, 82, 81, 42, 183
        ]

    def apply_lipstick(self, image, color_bgr, intensity=0.5):
        """
        给嘴唇上妆
        :param image: 原始图像 (OpenCV格式)
        :param color_bgr: 目标颜色 (B, G, R)
        :param intensity: 上妆强度 (0.0 - 1.0)
        """
        h, w = image.shape[:2]
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb_image)
        
        if not results.multi_face_landmarks:
            return image
        
        landmarks = results.multi_face_landmarks[0]
        points = []
        for idx in self.LIPS_INDICES:
            pt = landmarks.landmark[idx]
            points.append([int(pt.x * w), int(pt.y * h)])
        
        points = np.array(points)
        
        # 创建掩膜
        mask = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.fillPoly(mask, [cv2.convexHull(points)], 255)
        
        # 颜色应用 (使用掩膜和高斯模糊边缘使其自然)
        mask_blur = cv2.GaussianBlur(mask, (7, 7), 0)
        mask_norm = mask_blur / 255.0
        
        overlay = image.copy()
        overlay[:] = color_bgr
        
        # 混合图像
        for c in range(3):
            image[:, :, c] = (1.0 - mask_norm * intensity) * image[:, :, c] + \
                             (mask_norm * intensity) * overlay[:, :, c]
            
        return image

# 测试代码
if __name__ == "__main__":
    applier = CosmeticApplier()
    # 模拟读取图片并调用 apply_lipstick...
    print("CosmeticApplier 模块加载成功，可用于软著申请代码提交。")
