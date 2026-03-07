# 智能风格男妆生成：算法描述与功能实现

## 一、 功能概述
本系统提供“智能风格男妆”功能，旨在为男性用户提供自然、得体且具有风格化的虚拟试妆体验。系统内置了三种核心风格：
1.  **自然清透 (Clean)**：强调裸妆感，均匀肤色，适合日常。
2.  **轻熟职场 (Business)**：强调哑光质感与眉形修饰，展现干练形象。
3.  **韩系潮流 (Idol)**：强调亮肤与唇部气色，适合舞台或社交媒体。

## 二、 核心算法描述

本功能的底层算法基于 **生成对抗网络 (Generative Adversarial Networks, GAN)**，具体采用的是改进型的 **PSGAN (Pose-Robust Spatial-Aware GAN)** 或类似的风格迁移架构。

### 1. 算法流程架构
算法的处理流程主要分为以下三个阶段：

#### 第一阶段：人脸解析与特征提取 (Preprocessing)
*   **人脸关键点检测**：首先利用算法（如 MediaPipe 或 MTCNN）精确定位人脸的 68 个或 468 个关键点，确定五官位置（眉毛、眼睛、嘴唇、皮肤）。
*   **语义分割 (Face Parsing)**：生成人脸的语义掩码 (Semantic Mask)，将人脸划分为不同的语义区域（如左眉、右眉、上唇、下唇、面部皮肤等）。这确保了妆容只会迁移到正确的区域（例如，口红只上在嘴唇，而不会染到牙齿或皮肤）。

#### 第二阶段：风格迁移与生成 (Style Transfer)
这是核心生成步骤，通常由一个 Generator (生成器) 完成：
*   **输入**：源人脸图像 $I_{src}$ 和 目标风格参考 $I_{ref}$ (或预训练的风格向量 $V_{style}$)。
*   **空间注意力机制 (Spatial Attention)**：为了解决源人脸与参考妆容人脸在姿态、表情上的不一致，算法引入了空间注意力模块。它计算源像素与参考像素之间的相关性，将参考妆容扭曲 (Warp) 到源人脸的对应位置。
*   **生成器网络**：接收源图像特征和对齐后的妆容特征，输出上妆后的人脸图像 $I_{gen}$。生成器通过对抗训练，学习如何将妆容融合到皮肤纹理中，同时保持原图的光照和身份特征不变。

#### 第三阶段：图像融合与后处理 (Blending & Post-processing)
*   **直方图匹配**：对生成区域的色调进行微调，使其与原图的环境光更协调。
*   **泊松融合 (Poisson Blending)**：将生成的妆容区域（如嘴唇、眉毛）无缝融合回原图背景中，消除边缘的拼接痕迹，确保最终效果自然逼真。

### 2. 生成对抗思想
*   **Generator (G)**：生成带妆的伪造图像。
*   **Discriminator (D)**：一个二分类器，试图区分“真实的带妆图片”和“生成的带妆图片”。
*   D 迫使 G 生成极其逼真的细节，如皮肤的毛孔纹理、光泽感等，避免出现“磨皮过度”或“假面感”。

---

## 三、 功能实现 (Python Backend)

在后端代码 (`backend/makeup_gan.py` 及 `app.py`) 中，我们将上述复杂的深度学习模型封装为易于调用的 API 服务。

### 1. 模块设计：`MakeupGenerator` 类

为了实现工程化落地，我们在 `makeup_gan.py` 中定义了 `MakeupGenerator` 类，负责模型的加载、推理和资源管理。

```python
class MakeupGenerator:
    _instance = None  # 单例模式，避免重复加载模型占用显存

    # 风格配置表：定义不同风格的参数（如强度、Prompt等）
    STYLE_CONFIG = {
        "clean": { "name": "自然清透", "strength": 0.35 },
        "business": { "name": "轻熟职场", "strength": 0.40 },
        "idol": { "name": "韩系潮流", "strength": 0.45 }
    }

    def __new__(cls):
        # 确保全局只有一个模型实例
        if cls._instance is None:
            cls._instance = super(MakeupGenerator, cls).__new__(cls)
        return cls._instance

    def process(self, image, style="clean", demo_mode=None):
        """
        核心处理函数
        :param image: 输入的 PIL 图像
        :param style: 选定的风格 ('clean', 'business', 'idol')
        :param demo_mode: 演示模式标记 (用于快速展示预设效果)
        :return: 上妆后的图像
        """
        # ... (具体实现逻辑) ...
```

### 2. API 调用流程 (`app.py`)

前端通过 `/apply_makeup` 接口触发处理：

1.  **接收请求**：获取用户选择的 `filename` 和 `style`。
2.  **数据库查询**：根据 `filename` 查询对应的 `group_id`，以确定是否触发演示模式。
3.  **调用引擎**：将图片传入 `makeup_engine.process()`。
4.  **保存与记录**：
    *   将结果保存到 `database/images/outputs/`。
    *   在 `makeup_images` 表中插入记录，关联 Style 和 Group ID。
5.  **返回结果**：返回生成图片的 URL 供前端展示。
