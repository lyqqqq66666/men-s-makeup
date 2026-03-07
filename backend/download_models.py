import os
import sys

# 设置模型下载加速
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

try:
    from huggingface_hub import snapshot_download
    from transformers import CLIPModel, CLIPProcessor
    from diffusers import ControlNetModel, StableDiffusionControlNetImg2ImgPipeline
except ImportError:
    print("正在安装必要的库: huggingface_hub diffusers transformers accelerate ...")
    os.system(f"{sys.executable} -m pip install huggingface_hub diffusers transformers accelerate -i https://pypi.tuna.tsinghua.edu.cn/simple")
    from huggingface_hub import snapshot_download

# 配置存储路径 (backend/models)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

# 设置环境变量，让之后的运行也默认使用这个文件夹
os.environ["HUGGINGFACE_HUB_CACHE"] = MODELS_DIR

MODELS = [
    {"id": "openai/clip-vit-base-patch32", "name": "视觉检测模型 (CLIP)"},
    {"id": "lllyasviel/sd-controlnet-canny", "name": "轮廓控制模型 (ControlNet)"},
    {"id": "digiplay/majicMIX_realistic_v6", "name": "基础生成模型 (Stable Diffusion)"}
]

def download():
    print("="*50)
    print("智颜方正 - 模型预下载工具")
    print(f"存储路径: {MODELS_DIR}")
    print("="*50)

    for i, model in enumerate(MODELS):
        print(f"\n[{i+1}/{len(MODELS)}] 正在下载 {model['name']}...")
        print(f"模型 ID: {model['id']}")
        try:
            # 下载到指定 cache 目录
            snapshot_download(
                repo_id=model['id'],
                cache_dir=MODELS_DIR,
                resume_download=True,
                # local_dir_use_symlinks 取其一即可，这里使用 cache_dir 模式方便代码加载
            )
            print(f"✅ {model['name']} 下载成功 / 已存在")
        except Exception as e:
            print(f"❌ {model['name']} 下载失败: {e}")
            print("请检查网络连接或尝试手动运行：export HF_ENDPOINT=https://hf-mirror.com")

if __name__ == "__main__":
    download()
    print("\n" + "="*50)
    print("所有模型已准备就绪！")
    print("现在您可以安全地运行后端服务了。")
    print("="*50)
