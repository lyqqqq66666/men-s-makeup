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
    #模型初始化
    def initialize_model(self):
        gc.collect()
        self.device = "cpu"
        # MediaPipe (默认就在 CPU 运行，无需修改)
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
        # CLIP
        print("加载视觉感知模块")
        try:
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        except Exception as e:
            print(f"警告: CLIP 加载失败: {e}")
            self.clip_model = None
        # Models
        print("加载生成模型")
        base_model = "digiplay/majicMIX_realistic_v6"
        controlnet_model = "lllyasviel/sd-controlnet-canny"
        self.controlnet = ControlNetModel.from_pretrained(controlnet_model, use_safetensors=False)
        self.pipe = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(base_model, controlnet=self.controlnet, safety_checker=None)
        self.pipe.set_progress_bar_config(disable=True)
        self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipe.scheduler.config, use_karras_sigmas=True, algorithm_type="dpmsolver++"
        )
        #开启切片和 Tiling以节省 CPU 内存
        self.pipe.enable_attention_slicing()
        self.pipe.enable_vae_tiling()
        self.pipe.to(self.device)
    # 眼镜佩戴检测
    def detect_glasses(self, image: Image.Image) -> bool:
        if self.clip_model is None: return False
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
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            return image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        return image

    def process(self, image: Image.Image, style: str = "clean") -> Image.Image:
        original_size = image.size
        # 1. 缩放
        process_img = self.resize_for_inference(image, max_size=768)
        # 2. 检测
        has_glasses = self.detect_glasses(process_img)
        if style not in self.STYLE_CONFIG: style = "clean"
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
        generator = torch.Generator(device="cpu").manual_seed(42)

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

        return output_small.resize(original_size, Image.LANCZOS)


#主程序
if __name__ == "__main__":
    ai = MakeupGenerator()
    img_name = ("test_pc/最终结果_无损扩展.jpg")

    if not os.path.exists(img_name):
        if os.path.exists(img_name.replace(".jpg", ".png")):
            img_name = img_name.replace(".jpg", ".png")
        else:
            print(f"错误: 未找到图片 {img_name}")
            sys.exit(1)

    img = Image.open(img_name).convert("RGB")
    while True:
        print("\n智颜方正")
        print("1. Clean| 2. Business| 3. Idol")
        print("q. 退出")
        c = input("请选择: ").strip()
        if c == 'q': break
        m = {"1": "clean", "2": "business", "3": "idol"}
        if c in m:
            s = m[c]
            start_time = time.time()
            res = ai.process(img, style=s)
            save_path = f"output_pc/result_{s}.jpg"
            os.makedirs("output_pc", exist_ok=True)
            res.save(save_path, quality=100, subsampling=0)
            duration = time.time() - start_time
            file_size_kb = os.path.getsize(save_path) / 1024
            print(f"完成: {save_path} (大小: {file_size_kb:.1f} KB | 耗时: {duration:.1f}s)")
        else:
            print("无效输入")