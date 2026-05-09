import os
import sys
import warnings
import time
import gc
import logging
import cv2
import numpy as np
import torch
from PIL import Image
import mediapipe as mp

# 过滤掉不必要的日志
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings("ignore")
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("diffusers").setLevel(logging.ERROR)
logging.getLogger("accelerate").setLevel(logging.ERROR)

from diffusers import (
    StableDiffusionControlNetImg2ImgPipeline,
    ControlNetModel,
    DPMSolverMultistepScheduler
)
from transformers import CLIPProcessor, CLIPModel

# 全局设置
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

class MakeupGenerator:
    _instance = None
    STYLE_CONFIG = {
        "clean": {
            "name": "清爽少年 (Clean)",
            "prompt": (
                "realistic male portrait, maintain original face, clear skin, natural glow, "
                "neat eyebrows, bright eyes, moisturized lips, sharp focus"
            ),
            "negative": (
                "heavy makeup, oily, beard, mustache, acne, jewelry, blur, plastic skin, changing face shape"
            ),
            "strength": 0.35,
            "glasses_vibe": "(clear lenses:1.3), (eyes visible through glasses:1.2)"
        },
        "business": {
            "name": "轻熟职场 (Business)",
            "prompt": (
                "professional male portrait, maintain original face, matte skin, even skin tone, "
                "groomed eyebrows, confident eyes, clean shaven, detailed skin texture"
            ),
            "negative": (
                "oil, shine, beard, stubble, messy hair, jewelry, lipstick, changing face shape"
            ),
            "strength": 0.40,
            "glasses_vibe": "(anti-reflective lenses:1.2), (clear visibility:1.2)"
        },
        "idol": {
            "name": "韩系爱豆 (Idol)",
            "prompt": (
                "kpop male portrait, maintain original face, bright porcelain skin, subtle shading, natural lip color, sharp focus"
            ),
            "negative": (
                "beard, mustache, rough skin, jewelry, piercing, heavy eyeliner, red lips, feminine, changing face shape"
            ),
            "strength": 0.45,
            "glasses_vibe": "(transparent lenses:1.3), (no glare:1.2)"
        }
    }

    FAST_STYLE_PRESET = {
        "clean": {"max_size": 512, "steps": 6, "guidance": 5.2},
        "business": {"max_size": 576, "steps": 7, "guidance": 5.5},
        "idol": {"max_size": 576, "steps": 8, "guidance": 5.8},
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MakeupGenerator, cls).__new__(cls)
            cls._instance.initialize_model()
        return cls._instance

    # 模型初始化
    def initialize_model(self):
        gc.collect()
        try:
            torch.set_num_threads(max(1, min(os.cpu_count() or 1, 8)))
        except Exception:
            pass
        self.device = "cpu"  # Mac M1/M2/Intel 通常使用 CPU 或 MPS (这里保守使用 CPU)
        self._glasses_detect_cache = {}
        
        # MediaPipe (默认就在 CPU 运行，无需修改)
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
        
        # CLIP
        print("加载视觉感知模块...")
        try:
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        except Exception as e:
            print(f"警告: CLIP 加载失败: {e}")
            self.clip_model = None
            
        # Models
        print("加载生成模型 (这可能需要几分钟下载模型)...")
        base_model = "digiplay/majicMIX_realistic_v6"
        controlnet_model = "lllyasviel/sd-controlnet-canny"
        
        try:
            self.controlnet = ControlNetModel.from_pretrained(controlnet_model, use_safetensors=False)
            self.pipe = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(base_model, controlnet=self.controlnet, safety_checker=None)
            self.pipe.set_progress_bar_config(disable=True)
            self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                self.pipe.scheduler.config, use_karras_sigmas=True, algorithm_type="dpmsolver++"
            )
            # 开启切片和 Tiling 以节省 CPU 内存
            self.pipe.enable_attention_slicing()
            self.pipe.enable_vae_tiling()
            self.pipe.to(self.device)
            print("生成模型加载完成。")
        except Exception as e:
            print(f"错误: 生成模型加载失败: {e}")
            raise e

    # 眼镜佩戴检测
    def detect_glasses(self, image: Image.Image) -> bool:
        if self.clip_model is None: return False
        try:
            cache_image = image.copy()
            cache_image.thumbnail((128, 128), Image.LANCZOS)
            cache_key = hash(cache_image.tobytes())
            if cache_key in self._glasses_detect_cache:
                return self._glasses_detect_cache[cache_key]
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
            detect_source = detect_source.copy()
            detect_source.thumbnail((224, 224), Image.LANCZOS)
            inputs = self.clip_processor(
                text=["face with glasses", "face without glasses"],
                images=detect_source,
                return_tensors="pt",
                padding=True
            )
            with torch.inference_mode():
                outputs = self.clip_model(**inputs)

            probs = outputs.logits_per_image.softmax(dim=1)[0]
            score = probs[0].item()
            detected = score > 0.5
            if len(self._glasses_detect_cache) > 128:
                self._glasses_detect_cache.clear()
            self._glasses_detect_cache[cache_key] = detected
            return detected

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

    def resize_for_inference(self, image, max_size=512):
        w, h = image.size
        # 如果图片过大则缩小，过小不放大，保持原分辨率处理可能会太慢，这里维持768限制
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            return image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        return image

    def process(self, image: Image.Image, style: str = "clean", demo_mode: str = None) -> Image.Image:
        """
        处理图片生成美妆。
        注意：demo_mode 参数保留以兼容接口，但实际逻辑已被注释，强制使用实时生成。
        """
        
        # --- 旧的模拟逻辑 (已注释) ---
        # if demo_mode:
        #     print(f"[处理] 演示模式 ({demo_mode}), 风格: {style}。正在模拟生成过程...")
        #     # 模拟处理等待时间
        #     for i in range(20):
        #         time.sleep(1) # 循环休眠20秒以模拟进度
        #     
        #     style_map = {
        #         "clean": "result_clean.jpg",
        #         "business": "result_business.jpg",
        #         "idol": "result_idol.jpg"
        #     }
        #     
        #     target_file = style_map.get(style, "result_clean.jpg")
        #     base_demo_dir = "lh、skb测试结果"
        #     sub_dir = f"测试结果{demo_mode}"
        #     demo_path = os.path.join(base_demo_dir, sub_dir, target_file)
        #     
        #     if not os.path.exists(demo_path):
        #          fallback_path = os.path.join("..", base_demo_dir, sub_dir, target_file)
        #          if os.path.exists(fallback_path):
        #              demo_path = fallback_path
        #          else:
        #              print(f"[错误] 未找到演示文件: {demo_path}")
        #              return image 
        #     
        #     try:
        #         print(f"[处理] 加载演示结果: {demo_path}")
        #         return Image.open(demo_path).convert("RGB")
        #     except Exception as e:
        #         print(f"[错误] 加载演示图片失败: {e}")
        #         return image
        # ---------------------------

        # --- 真实模型处理逻辑 ---
        
        original_size = image.size
        
        if style not in self.STYLE_CONFIG: 
            style = "clean"
        style_cfg = self.STYLE_CONFIG[style]
        speed_cfg = self.FAST_STYLE_PRESET.get(style, self.FAST_STYLE_PRESET["clean"])

        # 1. 缩放（保留比当前更强的细节，但仍控制 CPU 推理时间）
        process_img = self.resize_for_inference(image, max_size=int(speed_cfg["max_size"]))

        # 2. 检测
        has_glasses = self.detect_glasses(process_img)
        
        # 3. 线稿
        control_image = self.preprocess_canny(process_img, lock_body=True, is_sensitive=has_glasses)

        base_pos = style_cfg["prompt"]
        base_neg = style_cfg["negative"] + ", bad anatomy, distorted, change clothes"
        target_strength = style_cfg["strength"]
        actual_control = 1.12
        
        # 4. 策略应用
        status_msg = ""
        if has_glasses:
            status_msg = "眼镜模式"
            glasses_prompt = style_cfg.get("glasses_vibe", "")
            base_pos += f", {glasses_prompt}, (transparent lenses:1.3)"
            target_strength = min(target_strength + 0.04, 0.55)
            actual_control = 1.2

        gc.collect()

        # [CPU 修改] 使用 CPU 生成器
        device_name = getattr(self, "device", "cpu")
        generator = torch.Generator(device=device_name).manual_seed(42)

        print(f"[Process] {style_cfg['name']} | 力度: {target_strength} | {status_msg}")

        # 在 CPU 上运行推理
        with torch.inference_mode():
            output_small = self.pipe(
                prompt=base_pos,
                negative_prompt=base_neg,
                image=process_img,
                control_image=control_image,
                strength=target_strength,
                controlnet_conditioning_scale=actual_control,
                num_inference_steps=int(speed_cfg["steps"]),
                guidance_scale=float(speed_cfg["guidance"]),
                generator=generator
            ).images[0]

        # 恢复原始尺寸
        return output_small.resize(original_size, Image.LANCZOS)

# 主程序入口 (测试用)
if __name__ == "__main__":
    ai = MakeupGenerator()
    print("MakeupGenerator 初始化完成")
