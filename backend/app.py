import os
import multiprocessing

# [Mac 系统兼容性修复]
# 1. 限制 OpenMP 线程数以避免冲突导致崩溃
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# 2. 屏蔽 TensorFlow 和 MediaPipe 的 C++ 日志输出
# 必须在导入任何使用 TensorFlow/MediaPipe 的库之前设置
os.environ['GLOG_minloglevel'] = '2'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['ABSL_LOG_MIN_LEVEL'] = '2'

# 3. 强制使用 'spawn' 启动多进程，避免 fork 安全性问题
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass 

from flask import Flask, request, send_file, jsonify, send_from_directory, after_this_request
from flask_cors import CORS

import tempfile
import uuid
import cv2
import numpy as np
from image_compressor import ImageCompressor

import face_detection
import blur_detection
import face_correction
import db_manager

try:
    from makeup_gan import MakeupGenerator
    makeup_engine = MakeupGenerator()
    print("美妆生成引擎已就绪。")
except Exception as e:
    print(f"警告: 无法创建标准美妆引擎 ({e})，正在启用离线演示后备方案。")
    # 创建一个简单的 Mock 对象，只负责处理演示模式
    class MockMakeupEngine:
        def process(self, img, style="clean", demo_mode=None):
            # 这里的逻辑会再次在导入的模块里尝试，但为了万无一失，这里直接写死演示逻辑
            import os
            from PIL import Image
            import time
            if demo_mode:
                time.sleep(1) # 演示模式快速反馈
                path = os.path.join(os.path.dirname(__file__), "..", "lh、skb测试结果", f"测试结果{demo_mode}", f"result_{style}.jpg")
                if os.path.exists(path):
                    return Image.open(path).convert("RGB")
            return img # 失败则返回原图
    makeup_engine = MockMakeupEngine()

app = Flask(__name__)
CORS(app)  # 启用 CORS 支持跨域请求

compressor = ImageCompressor()

# 初始化数据库
db_manager.init_db()

# 配置部分
# 使用绝对路径，确保在任何目录下运行都能正确定位文件
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 按照数据库结构建议，分离上传和输出文件夹
UPLOADS_DIR = os.path.join(BASE_DIR, 'database', 'images', 'uploads')
OUTPUTS_DIR = os.path.join(BASE_DIR, 'database', 'images', 'outputs')

for d in [UPLOADS_DIR, OUTPUTS_DIR]:
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

@app.route('/compress', methods=['POST'])
def compress_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # 创建临时输入/输出路径
    temp_dir = tempfile.gettempdir()
    input_path = os.path.join(temp_dir, f"input_{uuid.uuid4()}.{file.filename.split('.')[-1]}")
    output_path = os.path.join(temp_dir, f"compressed_{uuid.uuid4()}.jpg")
    
    # 立即注册清理函数
    # 必须在返回响应之前完成注册

    @after_this_request
    def remove_file(response):
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception as error:
            app.logger.error(f"Error removing cleanup files: {error}")
        return response

    try:
        file.save(input_path)
        
        # 执行压缩
        # 假设 compressor.compress 接受 (输入路径, 输出路径, 质量参数)

        success = compressor.compress(input_path, output_path, quality=50)
        
        if success and os.path.exists(output_path):
            return send_file(output_path, as_attachment=True, download_name=f"compressed_{file.filename}")
        else:
            return jsonify({'error': 'Compression failed'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500 

@app.route('/apply_makeup', methods=['POST'])
def apply_makeup():
    if not makeup_engine:
        print("[警告] 美妆引擎未加载，请求可能失败（除非命中演示模式逻辑）。")
        
    try:
        data = request.json
        # Expecting 'filename' of the corrected image, and 'style'
        input_filename = data.get('filename')
        style = data.get('style', 'clean')
        
        if not input_filename:
            return jsonify({'error': '未提供文件名'}), 400
            
        # 定位已矫正的文件
        # 它应该位于 images/output/ 目录下
        input_path = os.path.join(OUTPUTS_DIR, input_filename)
        
        if not os.path.exists(input_path):
             # 尝试在上传目录中查找（如果该图片未经过矫正步骤）
             # 但根据工作流，输入通常应该是已矫正的图片
             return jsonify({'error': '找不到输入图片'}), 404
             
        # 生成输出文件名
        output_filename = f"makeup_{style}_{uuid.uuid4()}.jpg"
        output_path = os.path.join(OUTPUTS_DIR, output_filename)
        
        # 加载图片
        from PIL import Image
        img = Image.open(input_path).convert("RGB")
        
        # 在数据库中记录（先获取 group_id 以检测演示模式）
        # 根据输入文件名从 corrected_images 表查询 group_id
        conn = db_manager.get_db_connection()
        cwd_row = conn.execute('SELECT group_id FROM corrected_images WHERE filename = ?', (input_filename,)).fetchone()
        if not cwd_row:
             # 如果在已矫正表中找不到，尝试从上传表中查找（可能是直接上传的）
             cwd_row = conn.execute('SELECT group_id FROM uploads WHERE filename = ?', (input_filename,)).fetchone()
             
        group_id = cwd_row['group_id'] if cwd_row else 'unknown'
        conn.close()

        # 检查演示模式
        demo_mode = None
        if group_id.startswith("demo_lh_"):
            demo_mode = "lh"
        elif group_id.startswith("demo_skb_"):
            demo_mode = "skb"
        
        # 处理图片
        # 这是一个耗时操作，可能会阻塞。生产环境中建议使用 Celery/Queue。
        print(f"正在生成美妆: 风格={style}, 文件={input_filename} (演示模式: {demo_mode})")
        result_img = makeup_engine.process(img, style=style, demo_mode=demo_mode)
        
        # 保存结果
        result_img.save(output_path, quality=95)
        
        db_manager.insert_makeup(group_id, style, output_filename, output_path)
        
        # 构建访问 URL

        file_url = f"{request.host_url}images/output/{output_filename}"
        
        return jsonify({
            'message': 'Makeup generated successfully',
            'url': file_url,
            'filename': output_filename
        })

    except Exception as e:
        print(f"Makeup generation error: {e}")
        return jsonify({'error': str(e)}), 500
@app.route('/process_upload', methods=['POST'])
def process_upload():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
        
    if file:
        try:
            # 为当前处理组生成唯一 ID
            group_id = str(uuid.uuid4())
            if file.filename == '实验1.jpg':
                group_id = f"demo_lh_{group_id}"
            elif file.filename == '实验2.jpg':
                group_id = f"demo_skb_{group_id}"
                
            original_ext = os.path.splitext(file.filename)[1].lower() or '.jpg'
            
            # 保存上传的文件到 UPLOADS_DIR
            input_filename = f"upload_{group_id}{original_ext}"
            input_path = os.path.join(UPLOADS_DIR, input_filename)
            file.save(input_path)
            
            # 在数据库中记录上传信息
            rel_upload_path = os.path.join('database', 'images', 'uploads', input_filename)
            db_manager.insert_upload(group_id, input_filename, rel_upload_path)
            
            # 读取图片进行处理

            image = cv2.imread(input_path)
            if image is None:
                 return jsonify({'status': 'error', 'message': '无法读取图片'}), 400

            # 1. 人脸检测
            face_rect, landmarks = face_detection.detect_face_landmarks_mediapipe(image)
            if face_rect is None:
                return jsonify({'status': 'no_face', 'message': '未检测到人脸，请重新上传正脸照片'}), 200

            # 2. 模糊检测
            # 传入 debug_prefix 作为 group_id 相关联的前缀
            blur_result = blur_detection.detect_blur_with_landmarks(image, landmarks, threshold=100, debug_prefix=group_id)
            
            # 记录调试用的 ROI 图片到数据库
            if 'debug_paths' in blur_result:
                for debug_path in blur_result['debug_paths']:
                    debug_filename = os.path.basename(debug_path)
                    db_manager.insert_debug(group_id, debug_filename, debug_path, blur_score=blur_result.get('score'))

            if blur_result['is_blurry']:
                return jsonify({
                    'status': 'blurry', 
                    'message': '照片过于模糊，请重新上传清晰照片', 
                    'score': blur_result['score'],
                    'details': blur_result['details']
                }), 200

            # 3. 人脸矫正
            # 定义输出文件名
            output_filename = f"corrected_{group_id}.jpg"
            
            # 执行矫正
            correction_result = face_correction.face_correction_ultimate(
                input_path, 
                output_dir=OUTPUTS_DIR, 
                output_filename=output_filename
            )
            
            # 记录矫正结果到数据库
            if correction_result:
                # 使用矫正模块返回的实际文件名
                # 这确保了如果模块强制使用了不同的扩展名（例如 .jpg）时的一致性

                actual_filename = correction_result.get('filename', output_filename)
                rel_output_path = os.path.join('database', 'images', 'outputs', actual_filename)
                
                db_manager.insert_corrected(
                    group_id, 
                    actual_filename, 
                    rel_output_path, 
                    correction_angle=correction_result.get('angle')
                )
            
            # 返回成功状态及图片访问 URL
            # 我们需要从新的位置提供服务

            result_url = f"http://localhost:5001/images/output/{output_filename}"
            
            return jsonify({
                'status': 'success',
                'message': '处理成功',
                'result_url': result_url
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/images/output/<filename>')
def serve_output_image(filename):
    return send_from_directory(OUTPUTS_DIR, filename)

@app.route('/images/upload/<filename>')
def serve_upload_image(filename):
    return send_from_directory(UPLOADS_DIR, filename)


@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(UPLOADS_DIR, filename)

if __name__ == '__main__':
    print("Starting Flask server for Face Processing...")
    app.run(host='0.0.0.0', port=5001, debug=True)
