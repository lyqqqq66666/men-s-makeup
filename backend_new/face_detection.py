import cv2
import numpy as np
import mediapipe as mp

# 初始化 MediaPipe 人脸网格模型
mp_face_mesh = mp.solutions.face_mesh

# 全局模型实例
# 也可以考虑封装成单例类以更好地管理生命周期
# 这里的配置：静态图片模式（适用于非视频流），最多检测一张人脸（专注主角），置信度 0.5
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=1,
    min_detection_confidence=0.5
)

def detect_face_landmarks_mediapipe(image):
    """
    调用 MediaPipe 获取人脸关键点及面部轮廓。

    参数:
        image: 输入图像 (BGR 格式，OpenCV 默认)

    返回:
        tuple: (人脸矩形框, 关键点数组)
            - face_rect: (x1, y1, x2, y2) 对应左上角和右下角坐标
            - landmarks: numpy 数组，即 [[x, y], ...]
            - 如果未检测到人脸，返回 (None, None)
    """
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(image_rgb)

    if not results.multi_face_landmarks:
        return None, None

    face_landmarks = results.multi_face_landmarks[0]
    h, w, _ = image.shape

    # 将归一化的关键点坐标转换为实际像素坐标

    landmarks = np.array([
        [int(landmark.x * w), int(landmark.y * h)]
        for landmark in face_landmarks.landmark
    ])

    # 根据关键点计算人脸的最小外接矩形

    x1 = int(np.min(landmarks[:, 0]))
    y1 = int(np.min(landmarks[:, 1]))
    x2 = int(np.max(landmarks[:, 0]))
    y2 = int(np.max(landmarks[:, 1]))
    face_rect = (x1, y1, x2, y2)

    return face_rect, landmarks

def close_face_mesh():
    """手动释放资源"""
    face_mesh.close()

if __name__ == "__main__":
    # 简单的测试代码
    print("face_detection 模块已加载")
