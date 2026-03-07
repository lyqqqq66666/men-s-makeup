import os
import sys
import warnings
import time
import gc
import logging
import cv2
import numpy as np
from PIL import Image
import mediapipe as mp

try:
    import torch
    # [修复] 解决某些环境下 torch 缺失 xpu 属性导致的初始化崩溃
    if not hasattr(torch, 'xpu'):
        class MockXPU:
            _is_available = False
            def is_available(self): return False
            def empty_cache(self): pass
            def set_device(self, *args, **kwargs): pass
            def synchronize(self, *args, **kwargs): pass
            def current_device(self): return 0
        torch.xpu = MockXPU()
        
    from diffusers import (
        StableDiffusionControlNetImg2ImgPipeline,
        ControlNetModel,
        DPMSolverMultistepScheduler
    )
    from transformers import CLIPProcessor, CLIPModel
    HAS_AI_LIBS = True
except Exception as e:
    print(f"警告: AI 相关库 (torch/diffusers) 导入失败或发生错误: {e}")
    HAS_AI_LIBS = False

# 过滤掉不必要的日志
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings("ignore")
if HAS_AI_LIBS:
    logging.getLogger("transformers").setLevel(logging.ERROR)
    logging.getLogger("diffusers").setLevel(logging.ERROR)
    logging.getLogger("accelerate").setLevel(logging.ERROR)

# 全局设置
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# 指定模型存储在 backend/models 文件夹下，方便管理
MODELS_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.environ["HUGGINGFACE_HUB_CACHE"] = MODELS_CACHE_DIR
os.makedirs(MODELS_CACHE_DIR, exist_ok=True)

class MakeupGenerator:
    _instance = None
    STYLE_CONFIG = {
        "clean": {
            "name": "清爽少年 (Clean)",
            "prompt": (
                "raw photo, realistic, 8k, (20yo male:1.2), "
                "(consistent facial features:1.5), maintain original face, "
                "(clear skin:1.2), (natural skin texture:1.1), (detailed pores:0.8), "
                "natural glow, (remove dullness:1.3), "
                "(neat eyebrows:1.2), (bright eyes:1.1), moisturized lips, "
                "soft lighting, sharp focus, high quality portrait"
            ),
            "negative": (
                "makeup, heavy makeup, oily, greasy, beard, mustache, acne, "
                "earrings, jewelry, accessories, necklace, "
                "blur, plastic skin, airbrushed, changing face shape, changing glasses frame"
            ),
            "strength": 0.35,
            "glasses_vibe": "(clear lenses:1.3), (eyes visible through glasses:1.2)"
        },
        "business": {
            "name": "轻熟职场 (Business)",
            "prompt": (
                "professional portrait, (20yo male:1.5), "
                "(consistent facial features:1.5), maintain original face, "
                "(matte skin:1.3), (oil control:1.2), (even skin tone:1.2), "
                "(groomed eyebrows:1.2), (defined jawline:0.8), determined eyes, confident, "
                "clean shaven, masculine features, detailed skin texture"
            ),
            "negative": (
                "oil, shine, sweat, beard, stubble, messy hair, "
                "earrings, jewelry, accessories, necklace, "
                "makeup, lipstick, changing face shape, changing glasses frame"
            ),
            "strength": 0.40,
            "glasses_vibe": "(anti-reflective lenses:1.2), (clear visibility:1.2)"
        },
        "idol": {
            "name": "韩系爱豆 (Idol)",
            "prompt": (
                "kpop style, stage lighting, (20yo male:1.5), "
                "(consistent facial features:1.5), maintain original face, "
                "(bright porcelain skin:1.3), (nose highlight:1.0), (T-zone highlight:0.8), "
                "(subtle shading:0.8), (natural lip color:1.1), "
                "clean look, sharp focus, (k-beauty aesthetics:1.1)"
            ),
            "negative": (
                "beard, mustache, rough skin, dark skin, "
                "earrings, silver earrings, jewelry, necklace, piercing, "
                "heavy eyeliner, lipstick, red lips, feminine, girl, "
                "changing face shape, changing glasses frame"
            ),
            "strength": 0.45,
            "glasses_vibe": "(transparent lenses:1.3), (no glare:1.2)"
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MakeupGenerator, cls).__new__(cls)
            cls._instance.initialize_model()
        return cls._instance

    # 模型初始化 (已改为延迟加载)
    def initialize_model(self):
        self.device = "cpu"
        self.pipe = None
        self.controlnet = None
        self.clip_model = None
        self.clip_processor = None
        
        # 仅初始化 MediaPipe (轻量级，始终加载)
        try:
            self.mp_face_detection = mp.solutions.face_detection
            self.face_detection = self.mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
            print("MediaPipe 初始化成功。")
        except Exception as e:
            print(f"警告: MediaPipe 初始化失败 (演示模式仍可运行): {e}")
            self.face_detection = None

        print("MakeupGenerator 初始化完成 (模型将按需延迟加载)")

    def _ensure_model_loaded(self):
        """确保重型模型已加载到内存"""
        if not HAS_AI_LIBS:
            print("[错误] 检测到当前环境缺失 PyTorch 或相关 AI 库，无法启动实时生成。")
            return False
            
        if self.pipe is not None:
            return True

        gc.collect()
        print("检测到非演示请求，正在加载生成模型 (首次加载可能需要较长时间)...")
        
        # CLIP
        try:
            if self.clip_model is None:
                self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
                self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        except Exception as e:
            print(f"警告: CLIP 加载失败: {e}")
            
        # Diffusion Models
        base_model = "digiplay/majicMIX_realistic_v6"
        controlnet_model = "lllyasviel/sd-controlnet-canny"
        
        try:
            self.controlnet = ControlNetModel.from_pretrained(controlnet_model, use_safetensors=False)
            self.pipe = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(
                base_model, controlnet=self.controlnet, safety_checker=None
            )
            self.pipe.set_progress_bar_config(disable=True)
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe.scheduler.config, use_karras_sigmas=True, algorithm_type="dpmsolver++"
            )
            self.pipe.enable_attention_slicing()
            self.pipe.enable_vae_tiling()
            self.pipe.to(self.device)
            print("生成模型加载完成。")
            return True
        except Exception as e:
            print(f"错误: 生成模型加载失败。请运行 python backend/download_models.py 下载模型。原文: {e}")
            return False

    # 眼镜佩戴检测
    def detect_glasses(self, image: Image.Image) -> bool:
        if self.clip_model is None or self.face_detection is None: 
            return False
        try:
            image_np = np.array(image)
            h, w, _ = image_np.shape
            results = self.face_detection.process(image_np)
            detect_source = image
            if results.detections:
                detection = results.detections[0]
                bboxC = detection.location_data.relative_bounding_box
                x = int(bboxC.xmin * w)
                y = int(bboxC.ymin * h)
                w_box = int(bboxC.width * w)
                h_box = int(bboxC.height * h)
                padding = int(h_box * 0.1)
                crop_y1 = max(0, y - padding)
                crop_y2 = min(h, y + int(h_box * 0.6))
                crop_x1 = max(0, x - padding)
                crop_x2 = min(w, x + w_box + padding)
                if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                    detect_source = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            inputs = self.clip_processor(
                text=["face with glasses", "face without glasses"],
                images=detect_source,
                return_tensors="pt",
                padding=True
            )
            with torch.no_grad():
                outputs = self.clip_model(**inputs)

            probs = outputs.logits_per_image.softmax(dim=1)[0]
            score = probs[0].item()

            return score > 0.5

        except Exception as e:
            print(f"检测出错: {e}")
            return False

    def preprocess_canny(self, image, lock_body=True, is_sensitive=False):
        image_np = np.array(image)
        if len(image_np.shape) == 3:
            image_gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)
        else:
            image_gray = image_np

        low, high = (20, 80) if is_sensitive else (50, 150)

        canny = cv2.Canny(image_gray, low, high)
        canny = np.concatenate([canny[:, :, None]] * 3, axis=2)
        return Image.fromarray(canny)

    def resize_for_inference(self, image, max_size=768):
        w, h = image.size
        # 如果图片过大则缩小，过小不放大，保持原分辨率处理可能会太慢，这里维持768限制
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            return image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        return image

    def process(self, image: Image.Image, style: str = "clean", demo_mode: str = None) -> Image.Image:
        # [修复] 解决某些环境下 torch 缺失 xpu 属性导致的初始化崩溃
        if not hasattr(torch, 'xpu'):
            class MockXPU:
                def is_available(self): return False
                def empty_cache(self): pass
                def set_device(self, device): pass
                def synchronize(self, device=None): pass
            torch.xpu = MockXPU()
        """
        处理图片生成美妆。
        已恢复演示模式逻辑：当 demo_mode 有效时，将直接返回预设的测试图片。
        """
        
        # --- 演示模式逻辑 (已恢复) ---
        if demo_mode:
            print(f"[处理] 演示模式 ({demo_mode}), 风格: {style}。正在模拟生成过程...")
            for i in range(2): # 缩短到 2 秒，演示更丝滑
                time.sleep(1)
            
            style_map = {
                "clean": "result_clean.jpg",
                "business": "result_business.jpg",
                "idol": "result_idol.jpg"
            }
            target_file = style_map.get(style, "result_clean.jpg")
            base_demo_dir = "lh、skb测试结果"
            sub_dir = f"测试结果{demo_mode}"
            
            # 使用绝对路径定位，确保 100% 成功
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 方案1: backend/../lh、skb测试结果
            path1 = os.path.join(current_dir, "..", base_demo_dir, sub_dir, target_file)
            # 方案2: 直接在当前运行目录寻找 (如果 user 在根目录启动)
            path2 = os.path.join(os.getcwd(), base_demo_dir, sub_dir, target_file)
            
            demo_path = None
            if os.path.exists(path1):
                demo_path = path1
            elif os.path.exists(path2):
                demo_path = path2
            
            if demo_path:
                try:
                    print(f"[处理] 成功匹配演示结果: {demo_path}")
                    return Image.open(demo_path).convert("RGB")
                except Exception as e:
                    print(f"[错误] 加载演示图片失败: {e}")
            else:
                print(f"[错误] 未找到演示文件，已尝试路径: \n1. {path1}\n2. {path2}")
        # ---------------------------

        # --- 真实模型处理逻辑 ---
        
        # 确保模型已加载，如果加载失败则返回原图或报错
        if not self._ensure_model_loaded():
            print("[错误] 无法加载生成模型，跳过处理。")
            return image

        original_size = image.size
        
        # 1. 缩放 (为了推理速度，先缩小)
        process_img = self.resize_for_inference(image, max_size=768)
        
        # 2. 检测
        has_glasses = self.detect_glasses(process_img)
        
        if style not in self.STYLE_CONFIG: 
            style = "clean"
        style_cfg = self.STYLE_CONFIG[style]
        
        # 3. 线稿
        control_image = self.preprocess_canny(process_img, lock_body=True, is_sensitive=has_glasses)

        base_pos = style_cfg["prompt"]
        base_neg = style_cfg["negative"] + ", bad anatomy, distorted, change clothes"
        target_strength = style_cfg["strength"]
        actual_control = 1.15
        
        # 4. 策略应用
        status_msg = ""
        if has_glasses:
            status_msg = "眼镜模式"
            glasses_prompt = style_cfg.get("glasses_vibe", "")
            base_pos += f", {glasses_prompt}, (transparent lenses:1.3)"
            target_strength = min(target_strength + 0.05, 0.55)
            actual_control = 1.25

        gc.collect()
        
        # [CPU 修改] 使用 CPU 生成器
        device_name = getattr(self, "device", "cpu")
        generator = torch.Generator(device=device_name).manual_seed(42)

        print(f"[Process] {style_cfg['name']} | 力度: {target_strength} | {status_msg}")

        # 在 CPU 上运行推理
        output_small = self.pipe(
            prompt=base_pos,
            negative_prompt=base_neg,
            image=process_img,
            control_image=control_image,
            strength=target_strength,
            controlnet_conditioning_scale=actual_control,
            num_inference_steps=20,
            guidance_scale=6.5,
            generator=generator
        ).images[0]

        # 恢复原始尺寸
        return output_small.resize(original_size, Image.LANCZOS)

# 主程序入口 (测试用)
if __name__ == "__main__":
    ai = MakeupGenerator()
    print("MakeupGenerator 初始化完成")
