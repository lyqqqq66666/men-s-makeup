import os
import sys
import cv2
import numpy as np

def remove_background_refined(input_path, output_path):
    print(f"执行精细化背景去除: {input_path} -> {output_path}...")
    try:
        # 加载图像
        img = cv2.imread(input_path)
        if img is None:
            print("加载图像失败")
            return False
            
        h, w = img.shape[:2]
        
        # 创建遮罩 (h+2, w+2) - OpenCV floodFill 需要的尺寸
        mask = np.zeros((h+2, w+2), np.uint8)
        
        # 目标是去除白色背景。
        # 这里从图片的四个角进行漫水填充（Flood Fill），并设置非常低的容差。
        # 这样可以防止颜色溢出到人脸或衣物（即使它们是浅色，但只要不是纯白背景）
        
        seeds = [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1)]
        
        # 使用比 0 稍高的容差以应对压缩伪影，但要远低于 10。
        # 设定为 2 比较合适。
        tol = (2, 2, 2)
        
        # 漫水填充逻辑
        # cv2.floodFill(image, mask, seedPoint, newVal, loDiff, upDiff, flags)
        
        im_flood = img.copy()
        flags = 4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE
        
        for seed in seeds:
            # 检查种子点是否已经被遮罩覆盖
            if mask[seed[1]+1, seed[0]+1] == 0:
                cv2.floodFill(im_flood, mask, seed, (255,255,255), tol, tol, flags)
                
        # 裁剪遮罩以匹配原图尺寸
        mask_crop = mask[1:h+1, 1:w+1]
        
        # 创建 RGBA 图像
        rgba = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        
        # 设置 Alpha 通道
        # 仅将遮罩为 1 的区域（即被填充的背景）Alpha 设为 0，其余为 255
        rgba[:, :, 3] = np.where(mask_crop != 0, 0, 255).astype('uint8')
        
        # 保存结果
        cv2.imwrite(output_path, rgba)
        print("精细化漫水填充处理成功！")
        return True
    except Exception as e:
        print(f"精细化处理失败: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        input_p = "src/assets/login/logonew.png"
        output_p = "src/assets/login/logonew.png"
    else:
        input_p = sys.argv[1]
        output_p = sys.argv[2]
    
    if os.path.exists(input_p):
        remove_background_refined(input_p, output_p)
    else:
        print(f"File not found: {input_p}")
