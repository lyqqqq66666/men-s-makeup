import json
import multiprocessing
import os
import re
import logging
import tempfile
import threading
import time
import traceback
import uuid
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from flask import Flask, after_this_request, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

# [兼容性修复]
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['GLOG_minloglevel'] = '2'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['ABSL_LOG_MIN_LEVEL'] = '2'

try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

from image_compressor import ImageCompressor

import blur_detection
import db_manager
import face_correction
import face_detection

# 按需加载模型，避免 Flask debug reloader 导致父/子进程重复初始化
makeup_engine = None
_makeup_engine_error: Optional[str] = None
_makeup_engine_attempted = False
_makeup_engine_lock = threading.Lock()

app = Flask(__name__)
CORS(app)

# 日志优化：统一使用 app.logger，避免 traceback.print_exc() 在终端产生红色噪音。
app.logger.setLevel(logging.INFO)


class _GreenFormatter(logging.Formatter):
    GREEN = '\033[92m'
    RESET = '\033[0m'

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        return f'{self.GREEN}{base}{self.RESET}'


def _setup_green_logs() -> None:
    formatter = _GreenFormatter('[%(asctime)s] %(levelname)s %(message)s')

    root_logger = logging.getLogger()
    if root_logger.handlers:
        for h in root_logger.handlers:
            h.setFormatter(formatter)
    else:
        h = logging.StreamHandler()
        h.setFormatter(formatter)
        root_logger.addHandler(h)

    root_logger.setLevel(logging.INFO)
    app.logger.handlers = root_logger.handlers
    app.logger.propagate = False


_setup_green_logs()

compressor = ImageCompressor()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, 'database', 'images', 'uploads')
OUTPUTS_DIR = os.path.join(BASE_DIR, 'database', 'images', 'outputs')

_session_locks: Dict[str, threading.Lock] = {}
_session_locks_guard = threading.Lock()
_runtime_bootstrapped = False
_runtime_bootstrap_lock = threading.Lock()

for d in [UPLOADS_DIR, OUTPUTS_DIR]:
    if not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


LIPS_INDICES = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
LEFT_BROW_INDICES = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
RIGHT_BROW_INDICES = [336, 296, 334, 293, 300, 285, 295, 282, 283, 276]
LEFT_EYE_INDICES = [33, 133, 157, 158, 159, 160, 161, 246, 7, 163, 144, 145, 153, 154, 155, 173]
RIGHT_EYE_INDICES = [362, 263, 384, 385, 386, 387, 388, 466, 249, 390, 373, 374, 380, 381, 382, 398]
USER_ID_IN_NAME_RE = re.compile(r'(user_[A-Za-z0-9]+)')

ADMIN_USER_IDS = {
    item.strip() for item in os.environ.get('ADMIN_USER_IDS', '').split(',') if item.strip()
}

_TRUE_SET = {'1', 'true', 'yes', 'on'}
MODEL_PREFLIGHT_ON_BOOT = str(os.environ.get('MODEL_PREFLIGHT_ON_BOOT', '1')).strip().lower() in _TRUE_SET
MODEL_PREFLIGHT_STRICT = str(os.environ.get('MODEL_PREFLIGHT_STRICT', '0')).strip().lower() in _TRUE_SET

SEASON_COLOR_MAP: Dict[str, Dict[str, List[str]]] = {
    'Warm Spring': {
        'recommended': ['#F2A65A', '#E27D60', '#E8B04F'],
        'avoid': ['#9BA7C0', '#8FA1BF', '#6C7A89'],
    },
    'Warm Autumn': {
        'recommended': ['#C68642', '#8B4513', '#A0522D'],
        'avoid': ['#E6E6FA', '#87CEEB', '#B0C4DE'],
    },
    'Cool Summer': {
        'recommended': ['#7D8FB3', '#A58AB5', '#6D9DC5'],
        'avoid': ['#D8A47F', '#C97A63', '#B76E5D'],
    },
    'Cool Winter': {
        'recommended': ['#6A5ACD', '#8A2BE2', '#5F9EA0'],
        'avoid': ['#FFDAB9', '#F4A460', '#D2B48C'],
    },
}

# 轻量 PCA 投影配置（无需外部模型文件）
PCA_FEATURE_MEAN = np.array([66.0, 15.0, 20.0, 60.0, 16.0, 19.0], dtype=np.float32)
PCA_FEATURE_STD = np.array([12.0, 8.0, 10.0, 14.0, 9.0, 11.0], dtype=np.float32)
PCA_COMPONENTS = np.array(
    [
        [0.21, 0.55, 0.61, 0.14, 0.39, 0.33],
        [0.58, -0.25, 0.08, 0.66, -0.29, -0.20],
        [-0.43, 0.14, -0.10, 0.18, 0.72, -0.49],
    ],
    dtype=np.float32,
)

SEASON_PCA_CENTERS = {
    'Warm Spring': np.array([1.2, 0.8, 0.7], dtype=np.float32),
    'Warm Autumn': np.array([0.9, -0.6, 0.4], dtype=np.float32),
    'Cool Summer': np.array([-0.8, 0.5, -0.2], dtype=np.float32),
    'Cool Winter': np.array([-1.1, -0.7, -0.6], dtype=np.float32),
}


def _bootstrap_runtime_once() -> None:
    """进程内一次性初始化，避免 debug reloader 在导入阶段重复执行。"""
    global _runtime_bootstrapped
    if _runtime_bootstrapped:
        return

    with _runtime_bootstrap_lock:
        if _runtime_bootstrapped:
            return
        # 初始化数据库（SQLite）
        db_manager.init_db()
        _runtime_bootstrapped = True


@app.before_request
def _ensure_runtime_bootstrap():
    _bootstrap_runtime_once()


def _get_makeup_engine() -> Tuple[Optional[Any], Optional[str]]:
    global makeup_engine, _makeup_engine_error, _makeup_engine_attempted

    if makeup_engine is not None:
        return makeup_engine, None
    if _makeup_engine_attempted:
        return None, _makeup_engine_error

    with _makeup_engine_lock:
        if makeup_engine is not None:
            return makeup_engine, None
        if _makeup_engine_attempted:
            return None, _makeup_engine_error

        _makeup_engine_attempted = True
        try:
            from makeup_gan import MakeupGenerator

            app.logger.info('正在按需加载美妆生成模型...')
            makeup_engine = MakeupGenerator()
            _makeup_engine_error = None
            app.logger.info('美妆生成模型加载完成。')
        except Exception as e:
            makeup_engine = None
            _makeup_engine_error = str(e)
            app.logger.exception(f'美妆生成模型加载失败: {e}')

    return makeup_engine, _makeup_engine_error


def _startup_model_preflight() -> None:
    """启动预检：提前检测并加载模型，不执行业务渲染。"""
    if not MODEL_PREFLIGHT_ON_BOOT:
        app.logger.info('模型启动预检已关闭（MODEL_PREFLIGHT_ON_BOOT=0）。')
        return

    app.logger.info('启动预检：开始检测美妆模型可用性...')
    started = time.perf_counter()
    engine, err = _get_makeup_engine()
    elapsed = time.perf_counter() - started

    if engine is None:
        msg = f'启动预检失败：美妆模型不可用，原因：{err or "未知错误"}'
        if MODEL_PREFLIGHT_STRICT:
            raise RuntimeError(msg)
        app.logger.error(msg)
        return

    app.logger.info(f'启动预检通过：美妆模型可用，耗时 {elapsed:.2f}s。')


def _safe_json_loads(text: Any, fallback: Any):
    if text is None:
        return fallback
    if isinstance(text, (list, dict)):
        return text
    if not isinstance(text, str):
        return fallback
    try:
        return json.loads(text)
    except Exception:
        return fallback


def _build_canonical_applied_items(raw_items: Any) -> List[Dict[str, str]]:
    """规范化会话内已上妆列表：同一 category 仅保留一个 SKU（后写覆盖前写）。"""
    canonical: List[Dict[str, str]] = []
    category_to_index: Dict[str, int] = {}

    rows = _safe_json_loads(raw_items, [])
    if not isinstance(rows, list):
        return canonical

    for row in rows:
        if not isinstance(row, dict):
            continue

        product_id = str(row.get('product_id') or '').strip()
        if not product_id:
            continue

        category = str(row.get('category') or '').strip()
        if not category:
            product = db_manager.get_product_by_id(product_id) or {}
            category = str(product.get('category') or '').strip()
        if not category:
            continue

        if category in category_to_index:
            canonical[category_to_index[category]]['product_id'] = product_id
        else:
            category_to_index[category] = len(canonical)
            canonical.append({'product_id': product_id, 'category': category})

    return canonical


def _rebuild_makeup_chain(
    session_id: str,
    original_ref: str,
    selected_items: List[Dict[str, str]],
) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    """从 original_image 重建渲染链，保证会话结果由“最终 SKU 集合”唯一决定。"""
    current_ref = original_ref
    render_history = [original_ref]
    applied_products: List[Dict[str, Any]] = []

    for idx, item in enumerate(selected_items, start=1):
        product_id = str(item.get('product_id') or '').strip()
        if not product_id:
            continue

        product = db_manager.get_product_by_id(product_id)
        if not product:
            raise ValueError(f'PRODUCT_NOT_FOUND:{product_id}')

        category = str(product.get('category') or item.get('category') or '').strip()
        if not category:
            raise ValueError(f'CATEGORY_MISSING:{product_id}')

        input_path = _resolve_image_path(current_ref)
        if not input_path:
            raise FileNotFoundError('IMAGE_NOT_FOUND')

        output_filename = f'session_{session_id}_step{idx}_{product_id}_{uuid.uuid4().hex[:8]}.jpg'
        output_path = os.path.join(OUTPUTS_DIR, output_filename)

        _apply_color_render(input_path, output_path, product)

        current_ref = _output_url(output_filename)
        render_history.append(current_ref)
        applied_products.append({'product_id': product_id, 'step': idx, 'category': category})

    return current_ref, render_history, applied_products


def _get_session_lock(session_id: str) -> threading.Lock:
    with _session_locks_guard:
        lock = _session_locks.get(session_id)
        if lock is None:
            lock = threading.Lock()
            _session_locks[session_id] = lock
        return lock


def _cart_payload(user_id: str) -> Dict[str, Any]:
    items = db_manager.list_cart_items(user_id)
    total_quantity = sum([int(i.get('quantity') or 0) for i in items])
    total_amount = round(sum([float(i.get('line_total') or 0) for i in items]), 2)
    return {
        'user_id': user_id,
        'items': items,
        'summary': {
            'item_count': len(items),
            'total_quantity': total_quantity,
            'total_amount': total_amount,
        },
    }


def _extract_token(allow_query: bool = False) -> Optional[str]:
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth.replace('Bearer ', '', 1).strip()
    if allow_query:
        token_q = (request.args.get('token') or '').strip()
        if token_q:
            return token_q
    return None


def _require_user(allow_query_token: bool = False) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Any, int]]]:
    token = _extract_token(allow_query=allow_query_token)
    if not token:
        return None, _api_error('UNAUTHORIZED', '缺少 Authorization Bearer token', 401)
    user = db_manager.get_user_by_token(token)
    if not user:
        return None, _api_error('UNAUTHORIZED', '登录态无效或已过期', 401)
    return user, None


def _is_admin_user(user: Dict[str, Any]) -> bool:
    uid = str(user.get('user_id') or '').strip()
    username = str(user.get('username') or '').strip().lower()
    if uid and uid in ADMIN_USER_IDS:
        return True
    return username in {'admin', 'administrator'}


def _require_admin() -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Any, int]]]:
    user, err = _require_user()
    if err:
        return None, err
    if not _is_admin_user(user or {}):
        return None, _api_error('FORBIDDEN', '仅管理员可访问', 403)
    return user, None


def _api_success(data=None, message='ok', code=0, http_status=200):
    return jsonify({
        'code': code,
        'message': message,
        'data': data,
    }), http_status


def _api_error(error_code, message, http_status=400, data=None, code=None):
    return jsonify({
        'code': code if code is not None else http_status,
        'message': message,
        'data': data,
        'error_code': error_code,
    }), http_status


def _generate_mock_code(length: int = 6) -> str:
    return ''.join(str(np.random.randint(0, 10)) for _ in range(length))


def _send_verification_code_mock(target: str, biz_type: str, code: str) -> None:
    app.logger.info(f'[MOCK_SMS] target={target} biz_type={biz_type} code={code}')


def _send_verification_code(target: str, biz_type: str, code: str, channel: str = 'mock') -> None:
    if channel == 'mock':
        _send_verification_code_mock(target, biz_type, code)
        return
    raise NotImplementedError(f'Unsupported verification channel: {channel}')


def _output_url(filename: str) -> str:
    return f"{request.host_url.rstrip('/')}/images/output/{filename}"


def _upload_url(filename: str) -> str:
    return f"{request.host_url.rstrip('/')}/images/upload/{filename}"


def _basename(path_or_url: str) -> str:
    return os.path.basename(path_or_url.split('?')[0])


def _extract_user_id_from_filename(filename: str) -> Optional[str]:
    m = USER_ID_IN_NAME_RE.search(filename or '')
    return m.group(1) if m else None


def _extract_session_id_from_filename(filename: str) -> Optional[str]:
    base = _basename(filename)

    if base.startswith('session_original_'):
        tail = base[len('session_original_'):]
        return os.path.splitext(tail)[0]

    if base.startswith('session_'):
        tail = base[len('session_'):]
        marker = '_step'
        idx = tail.find(marker)
        if idx > 0:
            return tail[:idx]
    return None


def _infer_image_owner_user_id(filename: str) -> Optional[str]:
    base = _basename(filename)

    owner_from_name = _extract_user_id_from_filename(base)
    if owner_from_name:
        return owner_from_name

    session_id = _extract_session_id_from_filename(base)
    if session_id:
        return db_manager.get_makeup_session_owner(session_id)

    return None


def _user_can_access_image(user_id: str, filename: str) -> bool:
    base = _basename(filename)
    if not base or not user_id:
        return False

    owner_user_id = _infer_image_owner_user_id(base)
    if owner_user_id:
        return owner_user_id == user_id

    # 兜底：若文件在该用户任一会话历史中出现，也视为可访问
    return db_manager.user_owns_image_via_session(user_id, base)


def _resolve_image_path(image_ref: str) -> Optional[str]:
    if not image_ref:
        return None

    if os.path.exists(image_ref):
        return image_ref

    ref = image_ref.replace('\\', '/')
    filename = _basename(ref)

    if '/images/output/' in ref or ref.startswith('images/output/'):
        p = os.path.join(OUTPUTS_DIR, filename)
        return p if os.path.exists(p) else None

    if '/images/upload/' in ref or ref.startswith('images/upload/'):
        p = os.path.join(UPLOADS_DIR, filename)
        return p if os.path.exists(p) else None

    p1 = os.path.join(OUTPUTS_DIR, filename)
    if os.path.exists(p1):
        return p1
    p2 = os.path.join(UPLOADS_DIR, filename)
    if os.path.exists(p2):
        return p2

    return None


def _hex_to_bgr(color_hex: str) -> Tuple[int, int, int]:
    c = (color_hex or '#C68642').replace('#', '')
    if len(c) != 6:
        c = 'C68642'
    r = int(c[0:2], 16)
    g = int(c[2:4], 16)
    b = int(c[4:6], 16)
    return b, g, r


def _indices_to_points(landmarks: np.ndarray, indices: List[int]) -> np.ndarray:
    pts = [landmarks[i] for i in indices if i < len(landmarks)]
    if not pts:
        return np.empty((0, 2), dtype=np.int32)
    return np.array(pts, dtype=np.int32)


def _apply_color_render(input_path: str, output_path: str, product: Dict[str, Any]) -> None:
    image = cv2.imread(input_path)
    if image is None:
        raise ValueError('INPUT_IMAGE_NOT_FOUND')

    _, landmarks = face_detection.detect_face_landmarks_mediapipe(image)
    if landmarks is None:
        raise ValueError('NO_FACE_DETECTED')

    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    apply_area = (product.get('apply_area') or 'skin').lower()

    if apply_area == 'lips':
        lips = _indices_to_points(landmarks, LIPS_INDICES)
        if len(lips) < 3:
            raise ValueError('INVALID_LIPS_LANDMARKS')
        cv2.fillPoly(mask, [lips], 255)

    elif apply_area == 'brow':
        lb = _indices_to_points(landmarks, LEFT_BROW_INDICES)
        rb = _indices_to_points(landmarks, RIGHT_BROW_INDICES)
        if len(lb) >= 3:
            cv2.fillPoly(mask, [lb], 255)
        if len(rb) >= 3:
            cv2.fillPoly(mask, [rb], 255)

    elif apply_area == 'cheeks':
        if len(landmarks) < 455:
            raise ValueError('INVALID_FACE_LANDMARKS')
        left_center = tuple(map(int, landmarks[234]))
        right_center = tuple(map(int, landmarks[454]))
        face_width = int(np.linalg.norm(landmarks[234] - landmarks[454]))
        radius = max(14, int(face_width * 0.12))
        cv2.circle(mask, left_center, radius, 255, -1)
        cv2.circle(mask, right_center, radius, 255, -1)

    else:
        hull = cv2.convexHull(landmarks.astype(np.int32))
        cv2.fillConvexPoly(mask, hull, 180)

        # 避免大面积覆盖眼睛与嘴巴
        lips = _indices_to_points(landmarks, LIPS_INDICES)
        le = _indices_to_points(landmarks, LEFT_EYE_INDICES)
        re = _indices_to_points(landmarks, RIGHT_EYE_INDICES)
        if len(lips) >= 3:
            cv2.fillPoly(mask, [lips], 0)
        if len(le) >= 3:
            cv2.fillPoly(mask, [le], 0)
        if len(re) >= 3:
            cv2.fillPoly(mask, [re], 0)

    feather = int(product.get('feather') or 6)
    feather = max(1, feather)
    kernel = feather * 2 + 1
    if kernel % 2 == 0:
        kernel += 1
    soft_mask = cv2.GaussianBlur(mask, (kernel, kernel), 0)

    opacity = float(product.get('opacity') or 0.5)
    transparency_max = float(product.get('transparency_max') or opacity)
    alpha = min(max(opacity, 0.0), max(transparency_max, 0.0), 1.0)
    alpha_map = (soft_mask.astype(np.float32) / 255.0) * alpha

    bgr = _hex_to_bgr(product.get('render_hex') or product.get('color_hex') or '#C68642')
    color_layer = np.full_like(image, bgr, dtype=np.uint8)

    base = image.astype(np.float32)
    target = color_layer.astype(np.float32)
    render_mode = int(product.get('render_mode') or 0)
    if render_mode == 1:
        target = base * (target / 255.0)

    result = base * (1.0 - alpha_map[..., None]) + target * alpha_map[..., None]
    result = np.clip(result, 0, 255).astype(np.uint8)
    cv2.imwrite(output_path, result)


def _classify_season(image_bgr: np.ndarray, landmarks: np.ndarray) -> Dict[str, Any]:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    if brightness < 45:
        raise ValueError('TOO_DARK')

    hull = cv2.convexHull(landmarks.astype(np.int32))
    face_mask = np.zeros(gray.shape, dtype=np.uint8)
    cv2.fillConvexPoly(face_mask, hull, 255)

    # PCA 轻量特征：Lab 均值 + HSV 饱和度 + 色度波动
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

    valid_pixels = face_mask > 0
    if int(np.sum(valid_pixels)) < 50:
        raise ValueError('INVALID_FACE_MASK')

    l_vals = lab[:, :, 0][valid_pixels].astype(np.float32)
    a_vals = lab[:, :, 1][valid_pixels].astype(np.float32)
    b_vals = lab[:, :, 2][valid_pixels].astype(np.float32)
    s_vals = hsv[:, :, 1][valid_pixels].astype(np.float32)

    feature_vec = np.array(
        [
            float(np.mean(l_vals)),
            float(np.mean(a_vals)),
            float(np.mean(b_vals)),
            float(np.mean(s_vals)),
            float(np.std(a_vals)),
            float(np.std(b_vals)),
        ],
        dtype=np.float32,
    )

    normalized = (feature_vec - PCA_FEATURE_MEAN) / np.maximum(PCA_FEATURE_STD, 1e-6)
    pca_coord = PCA_COMPONENTS @ normalized

    distances: Dict[str, float] = {}
    for season_name, center in SEASON_PCA_CENTERS.items():
        distances[season_name] = float(np.linalg.norm(pca_coord - center))

    season_type = min(distances.keys(), key=lambda k: distances[k])
    tone = 'warm' if season_type.startswith('Warm') else 'cool'

    raw_logits = np.array([-distances[s] for s in SEASON_PCA_CENTERS.keys()], dtype=np.float32)
    raw_logits = raw_logits - np.max(raw_logits)
    probs = np.exp(raw_logits)
    probs = probs / max(float(np.sum(probs)), 1e-6)
    confidence = float(np.max(probs))

    season_rule = db_manager.get_season_rule(season_type)
    if season_rule:
        recommended_colors = season_rule.get('recommended_palette') or season_rule.get('lips_palette') or []
        avoid_colors = season_rule.get('avoid_palette') or []
        tone = season_rule.get('tone') or tone
    else:
        palette = SEASON_COLOR_MAP.get(season_type, SEASON_COLOR_MAP['Warm Autumn'])
        recommended_colors = palette['recommended']
        avoid_colors = palette['avoid']

    return {
        'season_type': season_type,
        'tone': tone,
        'recommended_colors': recommended_colors,
        'avoid_colors': avoid_colors,
        'confidence': round(confidence, 3),
        'model': 'pca-lite-v1',
    }


def _score_makeup_look(session: Dict[str, Any]) -> Dict[str, Any]:
    applied_products = _safe_json_loads(session.get('applied_products'), [])
    categories = {str(item.get('category') or '').strip() for item in applied_products if isinstance(item, dict)}
    categories.discard('')

    step_count = len(applied_products)
    diversity = len(categories)

    completeness_score = min(step_count, 5) / 5.0
    diversity_score = min(diversity, 5) / 5.0

    current_ref = str(session.get('current_image') or '').strip()
    original_ref = str(session.get('original_image') or '').strip()
    current_path = _resolve_image_path(current_ref) or _resolve_image_path(original_ref)

    clarity_score = 0.65
    if current_path and os.path.exists(current_path):
        try:
            image = cv2.imread(current_path)
            if image is not None:
                _, landmarks = face_detection.detect_face_landmarks_mediapipe(image)
                if landmarks is not None:
                    blur_result = blur_detection.detect_blur_with_landmarks(image, landmarks, threshold=100, debug_prefix='')
                    raw = float(blur_result.get('score') or 0)
                    clarity_score = min(max(raw / 120.0, 0.0), 1.0)
        except Exception:
            # 评分接口兜底：图像分析异常不应导致整体 500
            clarity_score = 0.65

    harmony_score = 0.5
    if step_count > 0:
        same_cat_penalty = max(0, step_count - diversity) * 0.08
        harmony_score = max(0.15, 0.85 - same_cat_penalty)

    weighted = (
        0.38 * completeness_score
        + 0.24 * diversity_score
        + 0.20 * clarity_score
        + 0.18 * harmony_score
    )

    final_score = int(round(weighted * 100))
    final_score = max(0, min(100, final_score))

    if final_score >= 85:
        level = 'excellent'
        tip = '整体妆效完成度和协调度都很好，可以直接作为日常方案使用。'
    elif final_score >= 70:
        level = 'good'
        tip = '妆效较稳定，可尝试补齐一个缺失部位（如眉或唇）进一步提升。'
    elif final_score >= 55:
        level = 'fair'
        tip = '建议继续叠加不同分类产品，并保持照片清晰度。'
    else:
        level = 'needs_improvement'
        tip = '当前步骤较少或图像质量不足，建议重新补齐关键步骤后再评分。'

    return {
        'score': final_score,
        'level': level,
        'dimensions': {
            'completeness': round(completeness_score, 3),
            'diversity': round(diversity_score, 3),
            'clarity': round(clarity_score, 3),
            'harmony': round(harmony_score, 3),
        },
        'step_count': step_count,
        'categories': sorted(list(categories)),
        'tip': tip,
    }


def _build_product_tags(product: Dict[str, Any], season: Optional[str] = None) -> List[str]:
    tags: List[str] = []
    season_tag = str(product.get('season_tag') or '').strip()
    category = str(product.get('category') or '').strip()
    price = float(product.get('price') or 0)

    if season and season_tag == season:
        tags.append('PCA推荐')
    if category in {'lip', 'brow'}:
        tags.append('新手友好')
    if price and price <= 220:
        tags.append('日常通勤')
    if category in {'eye', 'lip'}:
        tags.append('热门试妆')
    return tags[:2]


def _build_product_reason(product: Dict[str, Any], season: Optional[str] = None) -> str:
    name = str(product.get('name') or '该商品')
    season_tag = str(product.get('season_tag') or '').strip()
    category = str(product.get('category') or '').strip()
    if season and season_tag == season:
        return f'{name} 与你的 {season} 季型匹配，适合作为优先推荐商品。'
    if category == 'lip':
        return f'{name} 适合作为快速提气色的唇部推荐。'
    if category == 'brow':
        return f'{name} 适合作为入门级眉部推荐。'
    if category == 'contour':
        return f'{name} 适合增强面部轮廓层次。'
    return f'{name} 适合作为当前场景的推荐候选。'


def _recommended_style_templates(season: str) -> List[Dict[str, Any]]:
    season = str(season or '').strip() or 'Warm Autumn'
    if season == 'Cool Winter':
        return [
            {'template_id': 'interview_clean', 'name': '面试清爽', 'scene_tag': '面试清爽', 'categories': ['base', 'brow', 'lip']},
            {'template_id': 'business_stable', 'name': '商务稳重', 'scene_tag': '商务稳重', 'categories': ['base', 'brow', 'contour', 'lip']},
        ]
    return [
        {'template_id': 'daily_commute', 'name': '日常通勤', 'scene_tag': '日常通勤', 'categories': ['base', 'brow', 'lip']},
        {'template_id': 'date_vibe', 'name': '约会氛围', 'scene_tag': '约会氛围', 'categories': ['base', 'eye', 'lip']},
        {'template_id': 'business_stable', 'name': '商务稳重', 'scene_tag': '商务稳重', 'categories': ['base', 'brow', 'contour', 'lip']},
    ]


def _detect_face_occlusion(blur_result: Dict[str, Any]) -> bool:
    """基于眼部/口部 ROI 清晰度做轻量遮挡判断（墨镜/口罩）。"""
    try:
        left_eye = float(blur_result.get('left_eye_score') or 0)
        right_eye = float(blur_result.get('right_eye_score') or 0)
        mouth = float(blur_result.get('mouth_score') or 0)
    except Exception:
        return False

    # 经验阈值：
    # 1) 双眼同时极低，且口部相对正常，疑似墨镜
    eye_occluded = (left_eye < 10 and right_eye < 10 and mouth >= 18)
    # 2) 口部极低，且至少一只眼较清晰，疑似口罩
    mouth_occluded = (mouth < 8 and max(left_eye, right_eye) >= 18)

    return eye_occluded or mouth_occluded


@app.route('/health', methods=['GET'])
def health():
    return _api_success({'status': 'ok'}, message='health ok')


@app.route('/register', methods=['POST'])
def register():
    data = request.json or {}
    phone = (data.get('phone') or '').strip()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    code = (data.get('code') or '').strip()
    nickname = (data.get('nickname') or phone or username).strip()

    if not phone:
        return _api_error('INVALID_PARAMS', '缺少 phone', 400)
    if not password or len(password) < 6:
        return _api_error('INVALID_PARAMS', '密码长度至少6位', 400)
    if not code:
        return _api_error('INVALID_PARAMS', '缺少验证码 code', 400)

    ok, verify_result = db_manager.verify_code(phone, 'register', code)
    if not ok:
        return _api_error(verify_result, '验证码无效或已过期', 400)

    existed = db_manager.get_user_by_phone(phone)
    if existed:
        return _api_error('PHONE_EXISTS', '手机号已注册', 409)

    if username:
        existed_by_username = db_manager.get_user_by_username(username)
        if existed_by_username:
            return _api_error('USERNAME_EXISTS', '账号已存在', 409)

    try:
        user_id = db_manager.create_user_with_phone(phone=phone, username=username or None, password=password, nickname=nickname)
    except Exception as e:
        app.logger.exception(f'register failed: {e}')
        return _api_error('REGISTER_FAILED', str(e), 500)

    token = db_manager.create_auth_token(user_id=user_id)
    db_manager.update_user_last_login(user_id)
    return _api_success({'user_id': user_id, 'token': token, 'nickname': nickname, 'phone': phone}, message='注册成功', http_status=201)


@app.route('/auth/send-code', methods=['POST'])
def send_code():
    data = request.json or {}
    phone = (data.get('phone') or '').strip()
    biz_type = (data.get('type') or data.get('biz_type') or '').strip()

    if not phone:
        return _api_error('INVALID_PARAMS', '缺少 phone', 400)
    if biz_type not in {'register', 'login', 'reset_password'}:
        return _api_error('INVALID_PARAMS', 'type 必须是 register/login/reset_password', 400)

    code = _generate_mock_code()
    try:
        code_id = db_manager.create_verification_code(phone, biz_type, code, channel='mock', meta={'provider': 'console'})
        _send_verification_code(phone, biz_type, code, channel='mock')
    except Exception as e:
        app.logger.exception(f'send code failed: {e}')
        return _api_error('SEND_CODE_FAILED', str(e), 500)

    return _api_success({'code_id': code_id, 'mock': True, 'expires_in_seconds': 300}, message='验证码已发送')


@app.route('/auth/logout', methods=['POST'])
def logout():
    token = _extract_token()
    if not token:
        return _api_error('UNAUTHORIZED', '缺少 Authorization Bearer token', 401)
    db_manager.revoke_auth_token(token)
    return _api_success(None, message='退出登录成功')


@app.route('/auth/userInfo', methods=['GET'])
def user_info():
    user, err = _require_user()
    if err:
        return err

    history = db_manager.list_user_recent_history(user['user_id'], limit=5)
    latest = history[0] if history else None
    return _api_success(
        {
            'user_id': user.get('user_id'),
            'username': user.get('username'),
            'phone': user.get('phone'),
            'nickname': user.get('nickname'),
            'avatar': user.get('avatar'),
            'season_type': user.get('season_type'),
            'last_login_at': user.get('last_login_at'),
            'last_history': latest,
        },
        message='获取用户信息成功'
    )


@app.route('/auth/reset-password', methods=['POST'])
def reset_password():
    data = request.json or {}
    phone = (data.get('phone') or '').strip()
    code = (data.get('code') or '').strip()
    new_password = (data.get('newPassword') or '').strip()

    if not phone or not code or not new_password:
        return _api_error('INVALID_PARAMS', '缺少 phone/code/newPassword', 400)
    if len(new_password) < 6:
        return _api_error('INVALID_PARAMS', '新密码长度至少6位', 400)

    user_row = db_manager.get_user_by_phone(phone)
    if not user_row:
        return _api_error('USER_NOT_FOUND', '手机号未注册', 404)

    ok, verify_result = db_manager.verify_code(phone, 'reset_password', code)
    if not ok:
        return _api_error(verify_result, '验证码无效或已过期', 400)

    conn = db_manager.get_db_connection()
    conn.execute(
        'UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?',
        (db_manager.hash_password(new_password), db_manager.now_iso(), user_row['user_id'])
    )
    conn.commit()
    conn.close()

    return _api_success(None, message='密码重置成功')


@app.route('/user/profile', methods=['PUT'])
def update_user_profile_api():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    nickname = data.get('nickname')
    avatar = data.get('avatar')

    if nickname is None and avatar is None:
        return _api_error('INVALID_PARAMS', '至少提供 nickname 或 avatar 其中一个字段', 400)

    updated = db_manager.update_user_profile(user['user_id'], nickname=nickname, avatar=avatar)
    return _api_success(
        {
            'user_id': updated.get('user_id'),
            'nickname': updated.get('nickname'),
            'avatar': updated.get('avatar'),
            'phone': updated.get('phone'),
            'username': updated.get('username'),
            'season_type': updated.get('season_type'),
        },
        message='个人资料更新成功'
    )


@app.route('/user/history', methods=['GET'])
def user_history_api():
    user, err = _require_user()
    if err:
        return err

    limit = request.args.get('limit', '20').strip()
    history = db_manager.list_user_recent_history(user['user_id'], limit=limit)
    return _api_success({'items': history, 'count': len(history)}, message='获取历史记录成功')


@app.route('/user/preferences', methods=['GET', 'PUT'])
def user_preferences_api():
    user, err = _require_user()
    if err:
        return err

    user_id = str(user.get('user_id') or '').strip()
    if request.method == 'GET':
        profile = db_manager.get_user_preferences(user_id) or {
            'preferred_scenes': [],
            'preferred_categories': [],
            'preferred_finishes': [],
            'budget_min': 0,
            'budget_max': 0,
        }
        return _api_success(profile, message='获取偏好设置成功')

    data = request.json or {}
    profile = db_manager.upsert_user_preferences(
        user_id=user_id,
        preferred_scenes=data.get('preferred_scenes') or [],
        preferred_categories=data.get('preferred_categories') or [],
        preferred_finishes=data.get('preferred_finishes') or [],
        budget_min=data.get('budget_min') or 0,
        budget_max=data.get('budget_max') or 0,
    )
    return _api_success(profile, message='偏好设置更新成功')


@app.route('/api/pca/personalized_recommendations', methods=['GET'])
def personalized_recommendations():
    user, err = _require_user()
    if err:
        return err

    user_id = str(user.get('user_id') or '').strip()
    limit = request.args.get('limit', '10').strip()
    products = db_manager.get_personalized_recommendations(user_id, limit=limit)
    behavior = db_manager.list_user_behavior_events(user_id, limit=20)
    return _api_success({'products': products, 'behavior_snapshot': behavior}, message='获取个性化推荐成功')


@app.route('/api/recommend/pairs', methods=['GET'])
def pair_recommendations():
    _, err = _require_user()
    if err:
        return err

    source_sku_id = request.args.get('source_sku_id', '').strip()
    if not source_sku_id:
        return _api_error('INVALID_PARAMS', '缺少 source_sku_id', 400)
    items = db_manager.list_pair_recommendations(source_sku_id, limit=request.args.get('limit', '6').strip())
    return _api_success({'source_sku_id': source_sku_id, 'items': items}, message='获取搭配推荐成功')


@app.route('/user/membership', methods=['GET'])
def membership_profile():
    user, err = _require_user()
    if err:
        return err
    profile = db_manager.get_membership_profile(str(user.get('user_id') or '').strip())
    return _api_success(profile, message='获取会员信息成功')


@app.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    code = (data.get('code') or '').strip()
    phone = (data.get('phone') or '').strip()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    login_type = (data.get('loginType') or '').strip() or ('code' if code else 'password')

    if login_type == 'code':
        if not phone:
            return _api_error('INVALID_PARAMS', '验证码登录缺少 phone', 400)
        if not code:
            return _api_error('INVALID_PARAMS', '验证码登录缺少 code', 400)
        ok, verify_result = db_manager.verify_code(phone, 'login', code)
        if not ok:
            return _api_error(verify_result, '验证码无效或已过期', 400)
        user_row = db_manager.get_user_by_phone(phone)
        if not user_row:
            return _api_error('USER_NOT_FOUND', '手机号未注册，请先注册', 404)
    else:
        if not username:
            return _api_error('INVALID_PARAMS', '缺少 username', 400)
        if not password or len(password) < 6:
            return _api_error('INVALID_PARAMS', '密码长度至少6位', 400)

        user_row = db_manager.get_user_by_username(username)
        if not user_row:
            return _api_error('USER_NOT_FOUND', '账号不存在，请先注册', 404)

        if not db_manager.verify_password(password, user_row.get('password_hash') or ''):
            return _api_error('PASSWORD_INCORRECT', '密码错误', 401)

    token = db_manager.create_auth_token(user_id=user_row['user_id'])
    db_manager.update_user_last_login(user_row['user_id'])
    return _api_success({'user_id': user_row['user_id'], 'token': token, 'nickname': user_row.get('nickname') or username or phone, 'phone': user_row.get('phone')}, message='登录成功')


@app.route('/analyze_color_type', methods=['POST'])
def analyze_color_type():
    user, err = _require_user()
    if err:
        return err

    if 'image' not in request.files:
        return _api_error('INVALID_PARAMS', '请上传 image 文件', 400)

    file = request.files['image']
    token_user_id = (user.get('user_id') or '').strip()
    requested_user_id = (request.form.get('user_id') or '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)
    user_id = token_user_id
    if not user_id:
        return _api_error('INVALID_PARAMS', '缺少 user_id', 400)

    temp_dir = tempfile.gettempdir()
    ext = os.path.splitext(file.filename or '')[1].lower() or '.jpg'
    temp_input = os.path.join(temp_dir, f'color_{uuid.uuid4()}{ext}')
    file.save(temp_input)

    try:
        image = cv2.imread(temp_input)
        if image is None:
            return _api_error('INVALID_IMAGE', '图片无法读取', 400)

        file_size = os.path.getsize(temp_input) if os.path.exists(temp_input) else 0
        height, width = image.shape[:2]
        pca_image_id = db_manager.create_user_image(
            user_id=user_id,
            image_type='pca_input',
            stored_filename=os.path.basename(temp_input),
            file_path=temp_input,
            origin_filename=file.filename,
            mime_type=file.mimetype,
            file_size=file_size,
            width=width,
            height=height,
        )

        _, landmarks = face_detection.detect_face_landmarks_mediapipe(image)
        if landmarks is None:
            db_manager.create_image_quality_report(pca_image_id, has_face=False, raw_report={'reason': 'NO_FACE_DETECTED'})
            return _api_error('NO_FACE_DETECTED', '哎呀，没有检测到人脸，请调整角度再试~', 200)

        blur_result = blur_detection.detect_blur_with_landmarks(image, landmarks, threshold=100, debug_prefix='')
        db_manager.create_image_quality_report(
            pca_image_id,
            has_face=True,
            blur_score=blur_result.get('score'),
            left_eye_score=blur_result.get('left_eye_score'),
            right_eye_score=blur_result.get('right_eye_score'),
            mouth_score=blur_result.get('mouth_score'),
            occlusion_flag=_detect_face_occlusion(blur_result),
            raw_report=blur_result,
        )
        if blur_result.get('is_blurry'):
            return _api_error('BLURRY_IMAGE', '照片有点模糊，请重新上传一张清晰的~', 200)

        if _detect_face_occlusion(blur_result):
            return _api_error('FACE_OCCLUDED', '请摘下墨镜/口罩，露出完整面部哦', 200)

        try:
            analysis = _classify_season(image, landmarks)
        except ValueError as ve:
            if str(ve) == 'TOO_DARK':
                return _api_error('TOO_DARK', '光线太暗啦，请找个明亮的地方再试', 200)
            raise

        db_manager.update_user_season(user_id=user_id, season_type=analysis['season_type'])
        db_manager.create_pca_analysis_record(
            user_id=user_id,
            image_id=pca_image_id,
            season_type=analysis['season_type'],
            tone=analysis.get('tone'),
            confidence=analysis.get('confidence'),
            recommended_palette=analysis.get('recommended_colors'),
            avoid_palette=analysis.get('avoid_colors'),
            feature_vector=[],
            model_version=analysis.get('model'),
        )
        analysis['recommended_styles'] = _recommended_style_templates(analysis['season_type'])
        analysis['analysis_report'] = f"你更适合 {', '.join(analysis.get('recommended_colors', [])[:3])} 等色系，建议优先尝试自然感较强的底妆、眉部和唇部组合。"
        return _api_success(analysis, message='分析成功')

    except Exception as e:
        app.logger.exception(f'analyze_color_type failed: {e}')
        return _api_error('INTERNAL_ERROR', str(e), 500)
    finally:
        try:
            if os.path.exists(temp_input):
                os.remove(temp_input)
        except Exception:
            pass


@app.route('/recommend_products', methods=['GET'])
def recommend_products():
    user, err = _require_user()
    if err:
        return err

    token_user_id = str(user.get('user_id') or '').strip()
    requested_user_id = request.args.get('user_id', '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)

    season = request.args.get('season', '').strip()
    category = request.args.get('category', '').strip()
    limit = request.args.get('limit', '30').strip()

    if not season:
        user_row = db_manager.get_user_by_id(token_user_id)
        if user_row and user_row.get('season_type'):
            season = user_row['season_type']

    products = db_manager.get_products(season=season or None, category=category or None, limit=limit)
    enriched_products = []
    for product in products:
        row = dict(product)
        row['tags'] = _build_product_tags(row, season=season or None)
        row['recommend_reason'] = _build_product_reason(row, season=season or None)
        enriched_products.append(row)
    return _api_success({'season': season, 'category': category or None, 'products': enriched_products}, message='获取推荐商品成功')


@app.route('/bundle_recommend', methods=['GET'])
def bundle_recommend():
    user, err = _require_user()
    if err:
        return err

    token_user_id = str(user.get('user_id') or '').strip()
    requested_user_id = request.args.get('user_id', '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)

    user_id = token_user_id
    season = request.args.get('season', '').strip()
    current_product = request.args.get('current_product', '').strip() or None

    if not season and user_id:
        user = db_manager.get_user_by_id(user_id)
        if user and user.get('season_type'):
            season = user['season_type']

    if not season:
        season = 'Warm Autumn'

    selected = db_manager.get_bundle_recommend(season=season, current_product=current_product)
    products = [
        {
            'product_id': p['p_id'],
            'name': p['name'],
            'price': float(p.get('price') or 0),
            'category': p.get('category'),
        }
        for p in selected
    ]
    total_price = round(sum([p['price'] for p in products]), 2)
    discount_price = round(total_price * 0.84, 2)

    return _api_success({
        'bundle_name': '全套型男方案',
        'products': products,
        'total_price': total_price,
        'discount_price': discount_price,
        'season': season,
    }, message='获取套装推荐成功')


@app.route('/create_makeup_session', methods=['POST'])
def create_makeup_session():
    user, err = _require_user()
    if err:
        return err

    token_user_id = (user.get('user_id') or '').strip()
    requested_user_id = (request.form.get('user_id') or (request.json or {}).get('user_id') or '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)
    user_id = token_user_id
    if not user_id:
        return _api_error('INVALID_PARAMS', '缺少 user_id', 400)

    session_id = f'session_{uuid.uuid4().hex[:12]}'

    original_image_ref = ''
    original_image_path = None
    original_image_id = None

    if 'original_image' in request.files:
        file = request.files['original_image']
        ext = os.path.splitext(file.filename or '')[1].lower() or '.jpg'
        filename = f'session_original_{session_id}{ext}'
        save_path = os.path.join(OUTPUTS_DIR, filename)
        file.save(save_path)
        original_image_id = db_manager.create_user_image(
            user_id=user_id,
            image_type='session_original',
            stored_filename=filename,
            file_path=os.path.join('database', 'images', 'outputs', filename),
            origin_filename=file.filename,
            mime_type=file.mimetype,
            file_size=os.path.getsize(save_path) if os.path.exists(save_path) else 0,
            source_session_id=session_id,
        )
        original_image_ref = _output_url(filename)
        original_image_path = save_path
    else:
        data = request.json or {}
        original_image_ref = (data.get('original_image') or '').strip()
        if original_image_ref:
            ref_filename = _basename(original_image_ref)
            if not _user_can_access_image(user_id, ref_filename):
                return _api_error('FORBIDDEN', '无权限使用该原图', 403)
        original_image_path = _resolve_image_path(original_image_ref)
        if original_image_ref:
            ref_filename = _basename(original_image_ref)
            existing_image = db_manager.get_user_image_by_filename(user_id, ref_filename)
            original_image_id = existing_image.get('image_id') if existing_image else None

    if not original_image_path:
        return _api_error('INVALID_PARAMS', '请提供 original_image 文件或有效图片路径', 400)

    # 统一保存为可访问 URL
    filename = os.path.basename(original_image_path)
    original_url = _output_url(filename) if original_image_path.startswith(OUTPUTS_DIR) else _upload_url(filename)

    db_manager.create_makeup_session(
        session_id=session_id,
        user_id=user_id,
        original_image=original_url,
        current_image=original_url,
    )

    return _api_success({'session_id': session_id, 'original_image': original_url, 'current_image': original_url}, message='创建试妆会话成功')


@app.route('/apply_makeup', methods=['POST'])
def apply_makeup():
    """
    兼容两种调用：
    1) 旧接口：{ filename, style }
    2) PRD 会话接口：{ session_id, product_id, category }
    """
    data = request.json or {}

    # ===== 新会话接口分支 =====
    if data.get('session_id') and data.get('product_id'):
        user, err = _require_user()
        if err:
            return err

        session_id = str(data.get('session_id')).strip()
        product_id = str(data.get('product_id')).strip()
        category = str(data.get('category') or '').strip()

        lock = _get_session_lock(session_id)
        with lock:
            session = db_manager.get_makeup_session(session_id)
            if not session:
                return _api_error('SESSION_NOT_FOUND', '找不到试妆会话', 404)

            if session.get('user_id') != user.get('user_id'):
                return _api_error('FORBIDDEN', '无权限操作该会话', 403)

            if session.get('status') != 'active':
                return _api_error('SESSION_CLOSED', '会话已关闭', 400)

            product = db_manager.get_product_by_id(product_id)
            if not product:
                return _api_error('PRODUCT_NOT_FOUND', '找不到产品 SKU', 404)

            product_category = str(product.get('category') or '').strip()
            if category and product_category != category:
                return _api_error('CATEGORY_MISMATCH', 'category 与 product_id 不匹配', 400)
            if not product_category:
                return _api_error('INVALID_PRODUCT', '该商品缺少 category，无法试妆', 400)

            # 幂等与去重策略：同一 category 仅保留一个 SKU。
            # - 新分类：追加
            # - 已有分类：替换
            # - 分类内重复点同一 SKU：直接返回（幂等 no-op）
            canonical_items = _build_canonical_applied_items(session.get('applied_products'))
            changed = True
            matched = False
            for item in canonical_items:
                if item.get('category') != product_category:
                    continue
                matched = True
                if item.get('product_id') == product_id:
                    changed = False
                else:
                    item['product_id'] = product_id
                break

            if not matched:
                canonical_items.append({'product_id': product_id, 'category': product_category})

            if not changed:
                current_image = session.get('current_image') or session.get('original_image')
                applied_products = [
                    {'product_id': row.get('product_id'), 'step': i + 1, 'category': row.get('category')}
                    for i, row in enumerate(canonical_items)
                ]
                return _api_success(
                    {
                        'session_id': session_id,
                        'current_image': current_image,
                        'applied_products': applied_products,
                        'idempotent': True,
                    },
                    message='试妆结果未变化'
                )

            original_ref = str(session.get('original_image') or '').strip()
            if not original_ref:
                return _api_error('SESSION_BROKEN', '会话缺少 original_image，无法重建渲染链', 500)

            try:
                new_current, render_history, applied_products = _rebuild_makeup_chain(
                    session_id=session_id,
                    original_ref=original_ref,
                    selected_items=canonical_items,
                )
            except FileNotFoundError:
                return _api_error('IMAGE_NOT_FOUND', '会话图片不存在，无法重建渲染链', 404)
            except ValueError as ve:
                msg = str(ve)
                if msg == 'NO_FACE_DETECTED':
                    return _api_error('NO_FACE_DETECTED', '没有检测到人脸，无法渲染', 200)
                if msg.startswith('PRODUCT_NOT_FOUND:'):
                    return _api_error('PRODUCT_NOT_FOUND', '渲染链中存在无效 SKU，请刷新后重试', 404)
                return _api_error('RENDER_FAILED', msg, 400)
            except Exception as e:
                app.logger.exception(f'apply_makeup render failed: {e}')
                return _api_error('RENDER_FAILED', str(e), 500)

            db_manager.update_makeup_session_state(
                session_id=session_id,
                current_image=new_current,
                applied_products=applied_products,
                render_history=render_history,
                step=len(applied_products),
                status='active',
            )

            output_filename = _basename(new_current)
            output_rel_path = os.path.join('database', 'images', 'outputs', output_filename)
            output_abs_path = os.path.join(OUTPUTS_DIR, output_filename)
            output_image_id = db_manager.create_user_image(
                user_id=str(user.get('user_id') or '').strip(),
                image_type='session_render',
                stored_filename=output_filename,
                file_path=output_rel_path,
                origin_filename=output_filename,
                mime_type='image/jpeg',
                file_size=os.path.getsize(output_abs_path) if os.path.exists(output_abs_path) else 0,
                source_session_id=session_id,
            )

            latest_session_render = db_manager.get_latest_session_image(session_id, image_type='session_render')
            input_image_id = latest_session_render.get('image_id') if latest_session_render else original_image_id

            db_manager.create_makeup_session_step(
                session_id=session_id,
                step_no=len(applied_products),
                category=product_category,
                sku_id=product_id,
                input_image_id=input_image_id,
                output_image_id=output_image_id,
                render_params={'product_id': product_id, 'category': product_category, 'current_image': new_current},
            )

            return _api_success({'session_id': session_id, 'current_image': new_current, 'applied_products': applied_products, 'idempotent': False}, message='试妆成功')

    # ===== 旧风格接口分支 =====
    user, err = _require_user()
    if err:
        return err

    engine, _ = _get_makeup_engine()
    if not engine:
        return _api_error('MODEL_NOT_READY', 'Makeup model not loaded', 503)

    input_filename = data.get('filename')
    style = data.get('style', 'clean')
    if not input_filename:
        return _api_error('INVALID_PARAMS', '未提供文件名', 400)

    input_path = os.path.join(OUTPUTS_DIR, input_filename)
    if not os.path.exists(input_path):
        return _api_error('IMAGE_NOT_FOUND', '找不到输入图片', 404)

    token_user_id = str(user.get('user_id') or '').strip()
    if not _user_can_access_image(token_user_id, input_filename):
        return _api_error('FORBIDDEN', '无权限访问该输入图片', 403)

    output_filename = f'makeup_{token_user_id}_{style}_{uuid.uuid4().hex[:12]}.jpg'
    output_path = os.path.join(OUTPUTS_DIR, output_filename)

    try:
        from PIL import Image

        img = Image.open(input_path).convert('RGB')

        conn = db_manager.get_db_connection()
        row = conn.execute('SELECT group_id FROM corrected_images WHERE filename = ?', (input_filename,)).fetchone()
        if not row:
            row = conn.execute('SELECT group_id FROM uploads WHERE filename = ?', (input_filename,)).fetchone()
        group_id = row['group_id'] if row else 'unknown'
        conn.close()

        demo_mode = None
        if group_id.startswith('demo_lh_'):
            demo_mode = 'lh'
        elif group_id.startswith('demo_skb_'):
            demo_mode = 'skb'

        result_img = engine.process(img, style=style, demo_mode=demo_mode)
        result_img.save(output_path, quality=95)
        db_manager.insert_makeup(group_id, style, output_filename, output_path)

        return _api_success({'url': _output_url(output_filename), 'filename': output_filename}, message='Makeup generated successfully')
    except Exception as e:
        app.logger.exception(f'legacy apply_makeup failed: {e}')
        return _api_error('RENDER_FAILED', str(e), 500)


@app.route('/undo_makeup', methods=['POST'])
def undo_makeup():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    session_id = str(data.get('session_id') or '').strip()
    if not session_id:
        return _api_error('INVALID_PARAMS', '缺少 session_id', 400)

    lock = _get_session_lock(session_id)
    with lock:
        session = db_manager.get_makeup_session(session_id)
        if not session:
            return _api_error('SESSION_NOT_FOUND', '找不到试妆会话', 404)
        if session.get('user_id') != user.get('user_id'):
            return _api_error('FORBIDDEN', '无权限操作该会话', 403)

        applied_products = _safe_json_loads(session.get('applied_products'), [])
        render_history = _safe_json_loads(session.get('render_history'), [session.get('original_image')])

        if applied_products:
            applied_products.pop()
        if len(render_history) > 1:
            render_history.pop()

        current_image = render_history[-1]
        step = len(applied_products)

        db_manager.update_makeup_session_state(
            session_id=session_id,
            current_image=current_image,
            applied_products=applied_products,
            render_history=render_history,
            step=step,
            status='active',
        )

        return _api_success({'session_id': session_id, 'current_image': current_image, 'applied_products': applied_products}, message='撤销成功')


@app.route('/reset_makeup', methods=['POST'])
def reset_makeup():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    session_id = str(data.get('session_id') or '').strip()
    if not session_id:
        return _api_error('INVALID_PARAMS', '缺少 session_id', 400)

    lock = _get_session_lock(session_id)
    with lock:
        session = db_manager.get_makeup_session(session_id)
        if not session:
            return _api_error('SESSION_NOT_FOUND', '找不到试妆会话', 404)
        if session.get('user_id') != user.get('user_id'):
            return _api_error('FORBIDDEN', '无权限操作该会话', 403)

        original = session.get('original_image')
        render_history = [original]
        applied_products = []

        db_manager.update_makeup_session_state(
            session_id=session_id,
            current_image=original,
            applied_products=applied_products,
            render_history=render_history,
            step=0,
            status='active',
        )

        return _api_success({'session_id': session_id, 'current_image': original, 'applied_products': applied_products}, message='重置成功')


@app.route('/api/makeup/reset-part', methods=['POST'])
def reset_makeup_part():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    session_id = str(data.get('session_id') or '').strip()
    category = str(data.get('category') or '').strip()
    if not session_id or not category:
        return _api_error('INVALID_PARAMS', '缺少 session_id/category', 400)

    lock = _get_session_lock(session_id)
    with lock:
        session = db_manager.get_makeup_session(session_id)
        if not session:
            return _api_error('SESSION_NOT_FOUND', '找不到试妆会话', 404)
        if session.get('user_id') != user.get('user_id'):
            return _api_error('FORBIDDEN', '无权限操作该会话', 403)

        items = _build_canonical_applied_items(session.get('applied_products'))
        filtered = [item for item in items if str(item.get('category') or '').strip() != category]

        original_ref = str(session.get('original_image') or '').strip()
        try:
            new_current, render_history, applied_products = _rebuild_makeup_chain(
                session_id=session_id,
                original_ref=original_ref,
                selected_items=filtered,
            )
        except Exception as e:
            return _api_error('RENDER_FAILED', str(e), 500)

        db_manager.update_makeup_session_state(
            session_id=session_id,
            current_image=new_current,
            applied_products=applied_products,
            render_history=render_history,
            step=len(applied_products),
            status='active',
        )

        return _api_success(
            {
                'session_id': session_id,
                'current_image': new_current,
                'applied_products': applied_products,
                'reset_category': category,
            },
            message='局部重置成功'
        )


@app.route('/api/makeup/style-templates', methods=['GET'])
def style_templates():
    user, err = _require_user()
    if err:
        return err

    season = request.args.get('season', '').strip()
    if not season:
        user_row = db_manager.get_user_by_id(str(user.get('user_id') or '').strip()) or {}
        season = str(user_row.get('season_type') or 'Warm Autumn')

    return _api_success({'season': season, 'templates': _recommended_style_templates(season)}, message='获取风格模板成功')


@app.route('/save_makeup_scheme', methods=['POST'])
def save_makeup_scheme():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    session_id = str(data.get('session_id') or '').strip()
    scheme_name = str(data.get('scheme_name') or '').strip()
    token_user_id = str(user.get('user_id') or '').strip()
    requested_user_id = str(data.get('user_id') or '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)
    user_id = token_user_id

    if not session_id or not scheme_name or not user_id:
        return _api_error('INVALID_PARAMS', '缺少 session_id/scheme_name/user_id', 400)

    lock = _get_session_lock(session_id)
    with lock:
        session = db_manager.get_makeup_session(session_id)
        if not session:
            return _api_error('SESSION_NOT_FOUND', '找不到试妆会话', 404)
        if session.get('user_id') != token_user_id:
            return _api_error('FORBIDDEN', '无权限操作该会话', 403)

        user_row = db_manager.get_user_by_id(user_id) or {}
        season_type = user_row.get('season_type')
        product_list = _safe_json_loads(session.get('applied_products'), [])
        cover_image = session.get('current_image')

        scheme_id = f'scheme_{uuid.uuid4().hex[:12]}'
        db_manager.save_makeup_scheme(
            scheme_id=scheme_id,
            user_id=user_id,
            scheme_name=scheme_name,
            product_list=product_list,
            cover_image=cover_image,
            season_type=season_type,
        )

        return _api_success({'scheme_id': scheme_id, 'product_count': len(product_list)}, message='保存成功')


@app.route('/get_makeup_schemes', methods=['GET'])
def get_makeup_schemes():
    user, err = _require_user()
    if err:
        return err

    token_user_id = str(user.get('user_id') or '').strip()
    requested_user_id = request.args.get('user_id', '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)
    user_id = token_user_id
    limit = request.args.get('limit', '50').strip()
    if not user_id:
        return _api_error('INVALID_PARAMS', '缺少 user_id', 400)

    rows = db_manager.list_makeup_schemes(user_id, limit=limit)
    schemes = []
    for r in rows:
        schemes.append(
            {
                'scheme_id': r.get('scheme_id'),
                'user_id': r.get('user_id'),
                'scheme_name': r.get('scheme_name'),
                'product_list': _safe_json_loads(r.get('product_list'), []),
                'cover_image': r.get('cover_image'),
                'season_type': r.get('season_type'),
                'created_at': r.get('created_at'),
            }
        )

    return _api_success({'user_id': user_id, 'schemes': schemes}, message='获取方案列表成功')


@app.route('/delete_makeup_scheme', methods=['POST'])
def delete_makeup_scheme():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    scheme_id = str(data.get('scheme_id') or '').strip()
    if not scheme_id:
        return _api_error('INVALID_PARAMS', '缺少 scheme_id', 400)

    token_user_id = str(user.get('user_id') or '').strip()
    requested_user_id = str(data.get('user_id') or '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)

    deleted = db_manager.delete_makeup_scheme(scheme_id=scheme_id, user_id=token_user_id)
    if not deleted:
        return _api_error('SCHEME_NOT_FOUND', '方案不存在或无权限删除', 404)

    return _api_success({'scheme_id': scheme_id}, message='删除成功')


@app.route('/get_makeup_session', methods=['GET'])
def get_makeup_session_api():
    user, err = _require_user()
    if err:
        return err

    session_id = request.args.get('session_id', '').strip()
    if not session_id:
        return _api_error('INVALID_PARAMS', '缺少 session_id', 400)

    session = db_manager.get_makeup_session(session_id)
    if not session:
        return _api_error('SESSION_NOT_FOUND', '找不到试妆会话', 404)
    if session.get('user_id') != user.get('user_id'):
        return _api_error('FORBIDDEN', '无权限访问该会话', 403)

    return _api_success(
        {
            'session_id': session.get('session_id'),
            'user_id': session.get('user_id'),
            'original_image': session.get('original_image'),
            'current_image': session.get('current_image'),
            'applied_products': _safe_json_loads(session.get('applied_products'), []),
            'step': int(session.get('step') or 0),
            'status': session.get('status') or 'active',
            'updated_at': session.get('updated_at'),
        },
        message='获取试妆会话成功'
    )


@app.route('/score_look', methods=['POST'])
def score_look():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    session_id = str(data.get('session_id') or '').strip()
    if not session_id:
        return _api_error('INVALID_PARAMS', '缺少 session_id', 400)

    session = db_manager.get_makeup_session(session_id)
    if not session:
        return _api_error('SESSION_NOT_FOUND', '找不到试妆会话', 404)
    if session.get('user_id') != user.get('user_id'):
        return _api_error('FORBIDDEN', '无权限访问该会话', 403)

    try:
        score_payload = _score_makeup_look(session)
        return _api_success(
            {
                'session_id': session_id,
                'current_image': session.get('current_image'),
                **score_payload,
            },
            message='妆容评分成功'
        )
    except Exception as e:
        app.logger.exception(f'score_look failed: {e}')
        return _api_error('SCORE_FAILED', str(e), 500)


@app.route('/admin/products', methods=['GET', 'POST'])
def admin_products():
    _, err = _require_admin()
    if err:
        return err

    if request.method == 'GET':
        limit = request.args.get('limit', '200').strip()
        category = request.args.get('category', '').strip() or None
        keyword = request.args.get('keyword', '').strip() or None
        products = db_manager.admin_list_products(limit=limit, category=category, keyword=keyword)
        return _api_success({'products': products, 'count': len(products)}, message='获取商品列表成功')

    data = request.json or {}
    try:
        created = db_manager.admin_create_product(data)
    except ValueError as ve:
        msg = str(ve)
        if msg == 'MISSING_REQUIRED_FIELDS':
            return _api_error('INVALID_PARAMS', '缺少必要字段：p_id/name/category/apply_area/render_hex', 400)
        return _api_error('INVALID_PARAMS', msg, 400)
    except Exception as e:
        app.logger.exception(f'admin create product failed: {e}')
        return _api_error('CREATE_FAILED', str(e), 500)

    return _api_success({'product': created}, message='创建成功', http_status=201)


@app.route('/admin/products/<product_id>', methods=['GET', 'PUT', 'DELETE'])
def admin_product_detail(product_id):
    _, err = _require_admin()
    if err:
        return err

    product_id = str(product_id or '').strip()
    if not product_id:
        return _api_error('INVALID_PARAMS', '缺少 product_id', 400)

    if request.method == 'GET':
        row = db_manager.get_product_by_id(product_id)
        if not row:
            return _api_error('PRODUCT_NOT_FOUND', '找不到产品 SKU', 404)
        return _api_success({'product': row}, message='获取商品成功')

    if request.method == 'PUT':
        data = request.json or {}
        exists = db_manager.get_product_by_id(product_id)
        if not exists:
            return _api_error('PRODUCT_NOT_FOUND', '找不到产品 SKU', 404)
        try:
            updated = db_manager.admin_update_product(product_id, data)
        except ValueError as ve:
            msg = str(ve)
            if msg == 'NO_UPDATABLE_FIELDS':
                return _api_error('INVALID_PARAMS', '没有可更新字段', 400)
            return _api_error('INVALID_PARAMS', msg, 400)
        except Exception as e:
            app.logger.exception(f'admin update product failed: {e}')
            return _api_error('UPDATE_FAILED', str(e), 500)
        return _api_success({'product': updated}, message='更新成功')

    exists = db_manager.get_product_by_id(product_id)
    if not exists:
        return _api_error('PRODUCT_NOT_FOUND', '找不到产品 SKU', 404)
    try:
        db_manager.admin_delete_product(product_id)
    except Exception as e:
        app.logger.exception(f'admin delete product failed: {e}')
        return _api_error('DELETE_FAILED', str(e), 500)
    return _api_success({'product_id': product_id}, message='删除成功')


@app.route('/cart/list', methods=['GET'])
def cart_list():
    user, err = _require_user()
    if err:
        return err

    token_user_id = str(user.get('user_id') or '').strip()
    requested_user_id = request.args.get('user_id', '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)

    return _api_success(_cart_payload(token_user_id), message='获取购物车成功')


@app.route('/cart/add', methods=['POST'])
def cart_add():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    token_user_id = str(user.get('user_id') or '').strip()
    requested_user_id = str(data.get('user_id') or '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)

    product_id = str(data.get('product_id') or '').strip()
    quantity = data.get('quantity', 1)

    if not product_id:
        return _api_error('INVALID_PARAMS', '缺少 product_id', 400)

    try:
        quantity = int(quantity)
    except Exception:
        return _api_error('INVALID_PARAMS', 'quantity 必须是整数', 400)
    if quantity <= 0:
        return _api_error('INVALID_PARAMS', 'quantity 必须大于 0', 400)

    product = db_manager.get_product_by_id(product_id)
    if not product:
        return _api_error('PRODUCT_NOT_FOUND', '找不到产品 SKU', 404)

    db_manager.add_to_cart(token_user_id, product_id, quantity)
    return _api_success(_cart_payload(token_user_id), message='加入购物车成功')


@app.route('/cart/update', methods=['POST'])
def cart_update():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    token_user_id = str(user.get('user_id') or '').strip()
    requested_user_id = str(data.get('user_id') or '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)

    product_id = str(data.get('product_id') or '').strip()
    quantity = data.get('quantity', 0)

    if not product_id:
        return _api_error('INVALID_PARAMS', '缺少 product_id', 400)
    try:
        quantity = int(quantity)
    except Exception:
        return _api_error('INVALID_PARAMS', 'quantity 必须是整数', 400)

    if quantity > 0:
        product = db_manager.get_product_by_id(product_id)
        if not product:
            return _api_error('PRODUCT_NOT_FOUND', '找不到产品 SKU', 404)

    db_manager.update_cart_item(token_user_id, product_id, quantity)
    return _api_success(_cart_payload(token_user_id), message='更新购物车成功')


@app.route('/cart/remove', methods=['POST'])
def cart_remove():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    token_user_id = str(user.get('user_id') or '').strip()
    requested_user_id = str(data.get('user_id') or '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)

    product_id = str(data.get('product_id') or '').strip()
    if not product_id:
        return _api_error('INVALID_PARAMS', '缺少 product_id', 400)

    db_manager.remove_cart_item(token_user_id, product_id)
    return _api_success(_cart_payload(token_user_id), message='移除商品成功')


@app.route('/cart/clear', methods=['POST'])
def cart_clear():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    token_user_id = str(user.get('user_id') or '').strip()
    requested_user_id = str(data.get('user_id') or '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)

    db_manager.clear_cart(token_user_id)
    return _api_success(_cart_payload(token_user_id), message='清空购物车成功')


@app.route('/cart/add_bundle', methods=['POST'])
def cart_add_bundle():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    token_user_id = str(user.get('user_id') or '').strip()
    requested_user_id = str(data.get('user_id') or '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)

    product_ids = data.get('product_ids') or []
    bundle_id = str(data.get('bundle_id') or '').strip()
    if bundle_id and not product_ids:
        bundle = db_manager.get_bundle_by_id(bundle_id)
        if not bundle:
            return _api_error('BUNDLE_NOT_FOUND', '找不到指定套装', 404)
        product_ids = [item['product_id'] for item in bundle.get('items', [])]

    if not isinstance(product_ids, list) or not product_ids:
        return _api_error('INVALID_PARAMS', 'product_ids 必须是非空数组', 400)

    added = 0
    for pid in product_ids:
        product_id = str(pid or '').strip()
        if not product_id:
            continue
        product = db_manager.get_product_by_id(product_id)
        if not product:
            continue
        db_manager.add_to_cart(token_user_id, product_id, 1)
        added += 1

    payload = _cart_payload(token_user_id)
    payload['added'] = added
    if bundle_id:
        payload['bundle_id'] = bundle_id
    return _api_success(payload, message='批量加入购物车成功')


@app.route('/cart/set_bulk', methods=['POST'])
def cart_set_bulk():
    user, err = _require_user()
    if err:
        return err

    data = request.json or {}
    token_user_id = str(user.get('user_id') or '').strip()
    requested_user_id = str(data.get('user_id') or '').strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error('FORBIDDEN', 'user_id 与登录用户不一致', 403)

    items = data.get('items') or []
    if not isinstance(items, list):
        return _api_error('INVALID_PARAMS', 'items 必须是数组', 400)

    for row in items:
        if not isinstance(row, dict):
            continue
        product_id = str(row.get('product_id') or '').strip()
        if not product_id:
            continue

        quantity_raw = row.get('quantity', 0)
        try:
            quantity = int(quantity_raw)
        except Exception:
            continue

        if quantity <= 0:
            db_manager.remove_cart_item(token_user_id, product_id)
            continue

        product = db_manager.get_product_by_id(product_id)
        if not product:
            continue

        exists = db_manager.get_cart_item(token_user_id, product_id)
        if exists:
            db_manager.update_cart_item(token_user_id, product_id, quantity)
        else:
            db_manager.add_to_cart(token_user_id, product_id, quantity)

    return _api_success(_cart_payload(token_user_id), message='批量设置购物车成功')


@app.route('/compress', methods=['POST'])
def compress_image():
    _, err = _require_user()
    if err:
        return err

    if 'file' not in request.files:
        return _api_error('INVALID_PARAMS', 'No file part', 400)
    file = request.files['file']
    if file.filename == '':
        return _api_error('INVALID_PARAMS', 'No selected file', 400)

    temp_dir = tempfile.gettempdir()
    input_path = os.path.join(temp_dir, f"input_{uuid.uuid4()}.{file.filename.split('.')[-1]}")
    output_path = os.path.join(temp_dir, f'compressed_{uuid.uuid4()}.jpg')

    @after_this_request
    def remove_file(response):
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception as error:
            app.logger.error(f'Error removing cleanup files: {error}')
        return response

    try:
        file.save(input_path)
        success = compressor.compress(input_path, output_path, quality=50)
        if success and os.path.exists(output_path):
            return send_file(output_path, as_attachment=True, download_name=f'compressed_{file.filename}')
        return _api_error('COMPRESS_FAILED', 'Compression failed', 500)
    except Exception as e:
        return _api_error('COMPRESS_FAILED', str(e), 500)


@app.route('/process_upload', methods=['POST'])
def process_upload():
    user, err = _require_user()
    if err:
        return err

    token_user_id = str(user.get('user_id') or '').strip()
    if not token_user_id:
        return _api_error('INVALID_PARAMS', '缺少 user_id', 400)

    if 'file' not in request.files:
        return _api_error('INVALID_PARAMS', 'No file part', 400)

    file = request.files['file']
    if file.filename == '':
        return _api_error('INVALID_PARAMS', 'No selected file', 400)

    try:
        group_id = f'{token_user_id}_{uuid.uuid4().hex}'
        if file.filename == '实验1.jpg':
            group_id = f'demo_lh_{token_user_id}_{uuid.uuid4().hex}'
        elif file.filename == '实验2.jpg':
            group_id = f'demo_skb_{token_user_id}_{uuid.uuid4().hex}'

        original_ext = os.path.splitext(file.filename)[1].lower() or '.jpg'
        input_filename = f'upload_{group_id}{original_ext}'
        input_path = os.path.join(UPLOADS_DIR, input_filename)
        file.save(input_path)

        rel_upload_path = os.path.join('database', 'images', 'uploads', input_filename)
        db_manager.insert_upload(group_id, input_filename, rel_upload_path)

        image = cv2.imread(input_path)
        if image is None:
            return _api_error('INVALID_IMAGE', '无法读取图片', 400)

        height, width = image.shape[:2]
        upload_image_id = db_manager.create_user_image(
            user_id=token_user_id,
            group_id=group_id,
            image_type='upload',
            stored_filename=input_filename,
            file_path=rel_upload_path,
            origin_filename=file.filename,
            mime_type=file.mimetype,
            file_size=os.path.getsize(input_path) if os.path.exists(input_path) else 0,
            width=width,
            height=height,
        )

        face_rect, landmarks = face_detection.detect_face_landmarks_mediapipe(image)
        if face_rect is None:
            db_manager.create_image_quality_report(upload_image_id, has_face=False, raw_report={'reason': 'NO_FACE_DETECTED'})
            return _api_error('NO_FACE_DETECTED', '未检测到人脸，请重新上传正脸照片', 200)

        blur_result = blur_detection.detect_blur_with_landmarks(image, landmarks, threshold=100, debug_prefix=group_id)
        db_manager.create_image_quality_report(
            upload_image_id,
            has_face=True,
            blur_score=blur_result.get('score'),
            left_eye_score=blur_result.get('left_eye_score'),
            right_eye_score=blur_result.get('right_eye_score'),
            mouth_score=blur_result.get('mouth_score'),
            occlusion_flag=_detect_face_occlusion(blur_result),
            raw_report=blur_result,
        )
        if 'debug_paths' in blur_result:
            for debug_path in blur_result['debug_paths']:
                debug_filename = os.path.basename(debug_path)
                db_manager.insert_debug(group_id, debug_filename, debug_path, blur_score=blur_result.get('score'))

        if blur_result.get('is_blurry'):
            return _api_error('BLURRY_IMAGE', '照片过于模糊，请重新上传清晰照片', 200, data={'score': blur_result.get('score'), 'details': blur_result.get('details')})

        output_filename = f'corrected_{group_id}.jpg'
        correction_result = face_correction.face_correction_ultimate(
            input_path,
            output_dir=OUTPUTS_DIR,
            output_filename=output_filename,
        )

        if correction_result:
            actual_filename = correction_result.get('filename', output_filename)
            rel_output_path = os.path.join('database', 'images', 'outputs', actual_filename)
            db_manager.insert_corrected(
                group_id,
                actual_filename,
                rel_output_path,
                correction_angle=correction_result.get('angle'),
            )
            corrected_path = os.path.join(OUTPUTS_DIR, actual_filename)
            corrected_size = os.path.getsize(corrected_path) if os.path.exists(corrected_path) else 0
            db_manager.create_user_image(
                user_id=token_user_id,
                group_id=group_id,
                image_type='corrected',
                stored_filename=actual_filename,
                file_path=rel_output_path,
                origin_filename=file.filename,
                mime_type='image/jpeg',
                file_size=corrected_size,
                width=None,
                height=None,
            )

        result_url = _output_url(output_filename)
        return _api_success({'result_url': result_url, 'group_id': group_id}, message='处理成功')

    except Exception as e:
        app.logger.exception(f'process_upload failed: {e}')
        return _api_error('PROCESS_UPLOAD_FAILED', str(e), 500)


@app.route('/images/output/<filename>')
def serve_output_image(filename):
    user, err = _require_user(allow_query_token=True)
    if err:
        return err
    token_user_id = str(user.get('user_id') or '').strip()
    if not _user_can_access_image(token_user_id, filename):
        return _api_error('FORBIDDEN', '无权限访问该图片', 403)
    return send_from_directory(OUTPUTS_DIR, filename)


@app.route('/images/upload/<filename>')
def serve_upload_image(filename):
    user, err = _require_user(allow_query_token=True)
    if err:
        return err
    token_user_id = str(user.get('user_id') or '').strip()
    if not _user_can_access_image(token_user_id, filename):
        return _api_error('FORBIDDEN', '无权限访问该图片', 403)
    return send_from_directory(UPLOADS_DIR, filename)


@app.route('/images/<filename>')
def serve_image(filename):
    user, err = _require_user(allow_query_token=True)
    if err:
        return err
    token_user_id = str(user.get('user_id') or '').strip()
    if not _user_can_access_image(token_user_id, filename):
        return _api_error('FORBIDDEN', '无权限访问该图片', 403)
    return send_from_directory(UPLOADS_DIR, filename)


if __name__ == '__main__':
    app.logger.info('Starting Flask server for Face Processing...')
    _bootstrap_runtime_once()
    _startup_model_preflight()
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)

