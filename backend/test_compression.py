import os
import shutil
from image_compressor import ImageCompressor

def test_compression():
    # 设置基础路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(base_dir, 'input')
    output_dir = os.path.join(base_dir, 'output')
    
    # 确保输入输出目录存在
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    compressor = ImageCompressor()

    # 获取待处理文件列表
    files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not files:
        print(f"No images found in {input_dir}. Please add some images to test.")
        return

    print(f"Found {len(files)} images to test.\n")
    print(f"{'File':<20} | {'Original Size':<15} | {'Compressed Size':<15} | {'Reduction':<10}")
    print("-" * 70)

    for file in files:
        input_path = os.path.join(input_dir, file)
        output_path = os.path.join(output_dir, f"compressed_{file}")
        
        # 根据文件类型确定压缩设置
        is_png = file.lower().endswith('.png')
        quantize = True if is_png else False # PNG 格式启用颜色量化以优化体积

        success = compressor.compress(input_path, output_path, quality=80, quantize=quantize)
        
        if success:
            orig_size = os.path.getsize(input_path)
            comp_size = os.path.getsize(output_path)
            reduction = (1 - comp_size / orig_size) * 100
            
            print(f"{file:<20} | {format_size(orig_size):<15} | {format_size(comp_size):<15} | {reduction:.1f}%")
        else:
            print(f"{file:<20} | FAILED")

def format_size(size_headers):
    for unit in ['B', 'KB', 'MB']:
        if size_headers < 1024:
            return f"{size_headers:.2f} {unit}"
        size_headers /= 1024
    return f"{size_headers:.2f} GB"

if __name__ == "__main__":
    test_compression()
