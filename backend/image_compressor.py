from PIL import Image, ExifTags, ImageOps
import os
import sys

class ImageCompressor:
    def __init__(self):
        self.supported_formats = ['.jpg', '.jpeg', '.png']

    def fix_orientation(self, img):
        """
        根据 EXIF 数据修正图片方向。
        """
        try:
            exif = img._getexif()
            if exif:
                orientation = exif.get(274)  # 274 is the tag for Orientation
                if orientation:
                    if orientation == 3:
                        img = img.rotate(180, expand=True)
                    elif orientation == 6:
                        img = img.rotate(270, expand=True)
                    elif orientation == 8:
                        img = img.rotate(90, expand=True)
        except Exception:
            # 如果 EXIF 数据缺失或损坏，直接返回原图
            pass
        return img

    def compress(self, input_path, output_path, quality=85, quantize=False):
        """
        在保持分辨率的同时压缩图片文件。
        
        参数:
            input_path (str): 源图片路径
            output_path (str): 压缩后图片的保存路径
            quality (int): JPEG 质量参数 (1-100)，默认 85
            quantize (bool): 针对 PNG 格式，是否启用色彩量化（有损压缩但体积更小）
        
        返回:
            bool: 成功返回 True，否则 False
        """
        try:
            if not os.path.exists(input_path):
                print(f"Error: Input file not found: {input_path}")
                return False

            filename, ext = os.path.splitext(input_path)
            ext = ext.lower()

            if ext not in self.supported_formats:
                print(f"Error: Unsupported format {ext}")
                return False

            with Image.open(input_path) as img:
                # 打印原始图片信息
                print(f"原始: {img.format}, 尺寸: {img.size}, 模式: {img.mode}")
                
                # 在处理前修正方向
                img = self.fix_orientation(img)
                
                # Ensure mode is consistent after rotation/transposition if needed
                # (Though rotate() usually preserves mode)

                if ext in ['.jpg', '.jpeg']:
                    # JPEG 压缩
                    # 如果是 RGBA 模式则转换为 RGB（JPEG 不支持透明通道）
                    if img.mode == 'RGBA':
                        img = img.convert('RGB')
                    
                    # 当保存时，Pillow 默认不保留 EXIF 除非显式指定。
                    # 由于我们已经手动旋转修正了方向，我们希望丢弃旧的 EXIF 方向标签。
                    img.save(output_path, 'JPEG', quality=quality, optimize=True)
                
                elif ext == '.png':
                    # PNG 压缩
                    if quantize:
                        # PNG 有损压缩 (色彩量化)
                        # 转换为 P 模式 (基于调色板)，限制为 256 色
                        # 这会显著减小体积，但属于有损压缩
                        img_quantized = img.quantize(colors=256, method=2)
                        img_quantized.save(output_path, 'PNG', optimize=True)
                    else:
                        # PNG 无损优化
                        img.save(output_path, 'PNG', optimize=True, compress_level=9)
                
                return True

        except Exception as e:
            print(f"Compression failed: {str(e)}")
            return False

if __name__ == "__main__":
    # 简单的命令行测试工具
    if len(sys.argv) < 3:
        print("用法: python image_compressor.py <输入文件> <输出文件> [质量]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    quality = int(sys.argv[3]) if len(sys.argv) > 3 else 85
    
    compressor = ImageCompressor()
    compressor.compress(input_file, output_file, quality)
