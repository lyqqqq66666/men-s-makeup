import json
import logging
import multiprocessing
import hashlib
import os
import re
import shutil
import tempfile
import threading
import time
import uuid
from urllib.parse import quote
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Query, Request, Security, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field

# [兼容性修复]
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["GLOG_minloglevel"] = "2"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
os.environ["ABSL_LOG_MIN_LEVEL"] = "2"

try:
    multiprocessing.set_start_method("spawn", force=True)
except RuntimeError:
    pass

from image_compressor import ImageCompressor

import blur_detection
import db_manager
import face_correction
import face_detection


app = FastAPI(
    title="智颜方正后端 API",
    version="2.1.0",
    description=(
        "基于 FastAPI 的独立业务版本，补充了更完整的 OpenAPI/Apipost 示例。\n\n"
        "- 认证接口提供 JSON 示例\n"
        "- 试妆/购物车/管理接口提供请求示例\n"
        "- 使用标准 Bearer Token 安全方案，便于 Apipost 导入后直接配置鉴权"
    ),
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.logger = logging.getLogger("fastapi_app")

makeup_engine = None
_makeup_engine_error: Optional[str] = None
_makeup_engine_attempted = False
_makeup_engine_lock = threading.Lock()

compressor = ImageCompressor()
bearer_scheme = HTTPBearer(auto_error=False)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "database", "images", "uploads")
OUTPUTS_DIR = os.path.join(BASE_DIR, "database", "images", "outputs")
AVATARS_DIR = os.path.join(BASE_DIR, "database", "images", "avatar")
TEMP_UPLOADS_DIR = os.path.join(BASE_DIR, "database", "images", "temp", "uploads")
TEMP_OUTPUTS_DIR = os.path.join(BASE_DIR, "database", "images", "temp", "outputs")

_session_locks: Dict[str, threading.Lock] = {}
_session_locks_guard = threading.Lock()
_runtime_bootstrapped = False
_runtime_bootstrap_lock = threading.Lock()
_style_render_cache: Dict[str, Dict[str, str]] = {}
_style_render_cache_lock = threading.Lock()

for d in [UPLOADS_DIR, OUTPUTS_DIR, AVATARS_DIR, TEMP_UPLOADS_DIR, TEMP_OUTPUTS_DIR]:
    os.makedirs(d, exist_ok=True)

LIPS_INDICES = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 409, 270, 269, 267, 0, 37, 39, 40, 185]
LEFT_BROW_INDICES = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
RIGHT_BROW_INDICES = [336, 296, 334, 293, 300, 285, 295, 282, 283, 276]
LEFT_EYE_INDICES = [33, 133, 157, 158, 159, 160, 161, 246, 7, 163, 144, 145, 153, 154, 155, 173]
RIGHT_EYE_INDICES = [362, 263, 384, 385, 386, 387, 388, 466, 249, 390, 373, 374, 380, 381, 382, 398]
LEFT_EYE_SOCKET_INDICES = [33, 246, 161, 160, 159, 158, 157, 173, 133, 155, 154, 153, 145, 144, 163, 7]
RIGHT_EYE_SOCKET_INDICES = [362, 466, 388, 387, 386, 385, 384, 398, 263, 382, 381, 380, 374, 373, 390, 249]
LEFT_CONTOUR_INDICES = [234, 93, 132, 58, 172, 136, 150, 149]
RIGHT_CONTOUR_INDICES = [454, 323, 361, 288, 397, 365, 379, 378]
USER_ID_IN_NAME_RE = re.compile(r"(user_[A-Za-z0-9]+)")

ADMIN_USER_IDS = {item.strip() for item in os.environ.get("ADMIN_USER_IDS", "").split(",") if item.strip()}
_TRUE_SET = {"1", "true", "yes", "on"}
MODEL_PREFLIGHT_ON_BOOT = str(os.environ.get("MODEL_PREFLIGHT_ON_BOOT", "1")).strip().lower() in _TRUE_SET
MODEL_PREFLIGHT_STRICT = str(os.environ.get("MODEL_PREFLIGHT_STRICT", "0")).strip().lower() in _TRUE_SET
MAKEUP_SESSION_TTL_HOURS = int(str(os.environ.get("MAKEUP_SESSION_TTL_HOURS", "24")).strip() or "24")

SEASON_COLOR_MAP: Dict[str, Dict[str, List[str]]] = {
    "Warm Spring": {"recommended": ["#F2A65A", "#E27D60", "#E8B04F"], "avoid": ["#9BA7C0", "#8FA1BF", "#6C7A89"]},
    "Warm Autumn": {"recommended": ["#C68642", "#8B4513", "#A0522D"], "avoid": ["#E6E6FA", "#87CEEB", "#B0C4DE"]},
    "Cool Summer": {"recommended": ["#7D8FB3", "#A58AB5", "#6D9DC5"], "avoid": ["#D8A47F", "#C97A63", "#B76E5D"]},
    "Cool Winter": {"recommended": ["#6A5ACD", "#8A2BE2", "#5F9EA0"], "avoid": ["#FFDAB9", "#F4A460", "#D2B48C"]},
}

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
    "Warm Spring": np.array([1.2, 0.8, 0.7], dtype=np.float32),
    "Warm Autumn": np.array([0.9, -0.6, 0.4], dtype=np.float32),
    "Cool Summer": np.array([-0.8, 0.5, -0.2], dtype=np.float32),
    "Cool Winter": np.array([-1.1, -0.7, -0.6], dtype=np.float32),
}

_request_var: ContextVar[Optional[Request]] = ContextVar("_request_var", default=None)


class _GreenFormatter(logging.Formatter):
    GREEN = "\033[92m"
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        return f"{self.GREEN}{base}{self.RESET}"


def _setup_green_logs() -> None:
    formatter = _GreenFormatter("[%(asctime)s] %(levelname)s %(message)s")
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


@app.middleware("http")
async def bind_request_context(request: Request, call_next):
    token = _request_var.set(request)
    try:
        _bootstrap_runtime_once()
        return await call_next(request)
    finally:
        _request_var.reset(token)


def _current_request() -> Request:
    req = _request_var.get()
    if req is None:
        raise RuntimeError("request context not bound")
    return req


@app.on_event("startup")
def on_startup():
    _bootstrap_runtime_once()
    try:
        _startup_model_preflight()
    except Exception as e:
        app.logger.exception(f"startup preflight failed: {e}")
        if MODEL_PREFLIGHT_STRICT:
            raise


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        detail = str(exc.detail.get("message") or "HTTP_ERROR")
        error_code = str(exc.detail.get("error_code") or "HTTP_ERROR")
        code = exc.detail.get("code") or exc.status_code
        data = exc.detail.get("data")
    else:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        error_code = detail if detail.isupper() else "HTTP_ERROR"
        code = exc.status_code
        data = None
    return JSONResponse(status_code=exc.status_code, content={"code": code, "message": detail, "data": data, "error_code": error_code})


@app.exception_handler(Exception)
async def common_exception_handler(_: Request, exc: Exception):
    app.logger.exception(f"unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"code": 500, "message": str(exc), "data": None, "error_code": "INTERNAL_ERROR"})


def ok(data: Any = None, message: str = "success"):
    return {"code": 0, "message": message, "data": data}


def api_error(status_code: int, error_code: str, message: str, data: Any = None, code: Optional[int] = None) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error_code": error_code, "message": message, "data": data, "code": code or status_code})


def _api_success(data=None, message="ok", code=0, http_status=200):
    return JSONResponse(status_code=http_status, content={"code": code, "message": message, "data": data})


def _api_error(error_code, message, http_status=400, data=None, code=None):
    return JSONResponse(status_code=http_status, content={"code": code if code is not None else http_status, "message": message, "data": data, "error_code": error_code})


def _bootstrap_runtime_once() -> None:
    global _runtime_bootstrapped
    if _runtime_bootstrapped:
        return
    with _runtime_bootstrap_lock:
        if _runtime_bootstrapped:
            return
        db_manager.init_db()
        _cleanup_expired_makeup_temp_files()
        _runtime_bootstrapped = True


def _cleanup_expired_makeup_temp_files() -> None:
    expire_before = (datetime.utcnow() - timedelta(hours=max(1, MAKEUP_SESSION_TTL_HOURS))).isoformat(timespec='seconds')
    for session in db_manager.list_expired_makeup_sessions(expire_before):
        session_id = str(session.get('session_id') or '').strip()
        if not session_id:
            continue
        for image in db_manager.list_session_images(session_id):
            file_path = str(image.get('file_path') or '').replace('\\', '/')
            if '/temp/' not in file_path:
                continue
            abs_path = _resolve_image_path(file_path)
            if abs_path and os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass
        db_manager.close_makeup_session(session_id)


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
            app.logger.info("正在按需加载美妆生成模型...")
            makeup_engine = MakeupGenerator()
            _makeup_engine_error = None
            app.logger.info("美妆生成模型加载完成。")
        except Exception as e:
            makeup_engine = None
            _makeup_engine_error = str(e)
            app.logger.exception(f"美妆生成模型加载失败: {e}")
    return makeup_engine, _makeup_engine_error


def _startup_model_preflight() -> None:
    if not MODEL_PREFLIGHT_ON_BOOT:
        app.logger.info("模型启动预检已关闭（MODEL_PREFLIGHT_ON_BOOT=0）。")
        return
    app.logger.info("启动预检：开始检测美妆模型可用性...")
    started = time.perf_counter()
    engine, err = _get_makeup_engine()
    elapsed = time.perf_counter() - started
    if engine is None:
        msg = f"启动预检失败：美妆模型不可用，原因：{err or '未知错误'}"
        if MODEL_PREFLIGHT_STRICT:
            raise RuntimeError(msg)
        app.logger.error(msg)
        return
    app.logger.info(f"启动预检通过：美妆模型可用，耗时 {elapsed:.2f}s。")


def _safe_json_loads(text: Any, fallback: Any):
    if text is None:
        return fallback
    if isinstance(text, (list, dict)):
        return text
    try:
        return json.loads(text)
    except Exception:
        return fallback


_UTC_PLUS_8 = timezone(timedelta(hours=8))


def _format_cn_datetime(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_UTC_PLUS_8).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return text


def _format_history_item_times(item: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not item:
        return item
    result = dict(item)
    for field in ["created_at", "updated_at", "upload_created_at", "corrected_created_at"]:
        if field in result:
            result[field] = _format_cn_datetime(result.get(field))
    return result


def _format_payload_times(value: Any) -> Any:
    if isinstance(value, list):
        return [_format_payload_times(item) for item in value]
    if isinstance(value, dict):
        result = {}
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                result[k] = _format_payload_times(v)
            elif k.endswith("_at") or k in {"expires_at", "verified_at", "finished_at"}:
                result[k] = _format_cn_datetime(v)
            else:
                result[k] = v
        return result
    return value


def _build_canonical_applied_items(applied_products: Any) -> List[Dict[str, Any]]:
    rows = _safe_json_loads(applied_products, [])
    canonical: List[Dict[str, Any]] = []
    seen_categories = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        product_id = str(row.get("product_id") or row.get("sku_id") or "").strip()
        category = str(row.get("category") or "").strip()
        if not product_id:
            continue
        if not category:
            product = db_manager.get_product_by_id(product_id)
            if product:
                category = str(product.get("category") or "").strip()
        if not category or category in seen_categories:
            continue
        canonical.append({"product_id": product_id, "category": category})
        seen_categories.add(category)
    return canonical


def _rebuild_makeup_chain(session_id: str, original_ref: str, selected_items: List[Dict[str, Any]]) -> Tuple[str, List[str], List[Dict[str, Any]]]:
    current_ref = original_ref
    render_history = [original_ref] if original_ref else []
    applied_products: List[Dict[str, Any]] = []

    for item in selected_items:
        product_id = str(item.get("product_id") or "").strip()
        category = str(item.get("category") or "").strip()
        if not product_id or not category:
            continue

        product = db_manager.get_product_by_id(product_id)
        if not product:
            raise ValueError(f"产品不存在: {product_id}")

        base_path = _resolve_image_path(current_ref)
        if not base_path or not os.path.exists(base_path):
            raise FileNotFoundError(f"基础图片不存在: {current_ref}")

        image = cv2.imread(base_path)
        if image is None:
            raise ValueError(f"无法读取基础图片: {base_path}")

        landmarks_result = face_detection.detect_face_landmarks_mediapipe(image)
        _, landmarks = landmarks_result if isinstance(landmarks_result, tuple) else (None, None)
        if landmarks is None:
            raise ValueError("未检测到人脸关键点，无法叠妆")

        output_path, output_relative_path, output_filename = _build_output_media_path(
            biz_type="session_render",
            user_id=_extract_user_id_from_filename(_basename(original_ref)) or db_manager.get_makeup_session_owner(session_id) or "unknown_user",
            filename_stem=f"session_{session_id}_{len(applied_products) + 1}_{category}",
            ext=".jpg",
        )
        render_hex = str(product.get("render_hex") or "").strip()

        if render_hex:
            _apply_color_render(
                image,
                landmarks,
                category=category,
                color_hex=render_hex,
                output_path=output_path,
                apply_area=str(product.get("apply_area") or category),
                opacity=product.get("opacity"),
                feather=product.get("feather"),
                render_mode=product.get("render_mode"),
                transparency_max=product.get("transparency_max"),
            )
        else:
            cv2.imwrite(output_path, image)

        current_ref = _output_url(output_relative_path.replace(os.sep, "/"))
        render_history.append(current_ref)
        applied_products.append({"product_id": product_id, "category": category})

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
    total_quantity = sum(int(i.get("quantity") or 0) for i in items)
    total_amount = round(sum(float(i.get("line_total") or 0) for i in items), 2)
    return {"user_id": user_id, "items": items, "summary": {"item_count": len(items), "total_quantity": total_quantity, "total_amount": total_amount}}


def _extract_token(allow_query: bool = False) -> Optional[str]:
    req = _current_request()
    auth = req.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.replace("Bearer ", "", 1).strip()
    if allow_query:
        token_q = (req.query_params.get("token") or "").strip()
        if token_q:
            return token_q
    return None


def _require_user(allow_query_token: bool = False) -> Tuple[Optional[Dict[str, Any]], Optional[JSONResponse]]:
    token = _extract_token(allow_query=allow_query_token)
    if not token:
        return None, _api_error("UNAUTHORIZED", "缺少 Authorization Bearer token", 401)
    user = db_manager.get_user_by_token(token)
    if not user:
        return None, _api_error("UNAUTHORIZED", "登录态无效或已过期", 401)
    return user, None


def _is_admin_user(user: Dict[str, Any]) -> bool:
    uid = str(user.get("user_id") or "").strip()
    role = str(user.get("role") or "").strip().lower()
    if uid and uid in ADMIN_USER_IDS:
        return True
    return role == "admin"


def _generate_mock_code(length: int = 6) -> str:
    return "".join(str(np.random.randint(0, 10)) for _ in range(length))


def _send_verification_code_mock(target: str, biz_type: str, code: str) -> None:
    app.logger.info(f"[MOCK_SMS] target={target} biz_type={biz_type} code={code}")


def _send_verification_code(target: str, biz_type: str, code: str, channel: str = "mock") -> None:
    if channel == "mock":
        _send_verification_code_mock(target, biz_type, code)
        return
    raise NotImplementedError(f"Unsupported verification channel: {channel}")


def _output_url(filename: str) -> str:
    req = _current_request()
    url = f"{str(req.base_url).rstrip('/')}/api/media/images/output/{filename}"
    token = _extract_token(allow_query=True)
    return f"{url}?token={quote(token)}" if token else url


def _upload_url(filename: str) -> str:
    req = _current_request()
    url = f"{str(req.base_url).rstrip('/')}/api/media/images/upload/{filename}"
    token = _extract_token(allow_query=True)
    return f"{url}?token={quote(token)}" if token else url


def _avatar_url(relative_path: str) -> str:
    req = _current_request()
    url = f"{str(req.base_url).rstrip('/')}/api/media/images/avatar/{relative_path.replace(os.sep, '/')}"
    token = _extract_token(allow_query=True)
    return f"{url}?token={quote(token)}" if token else url


def _default_avatar_url() -> str:
    return _avatar_url("defaults/avatar-default.png")


def _basename(path_or_url: str) -> str:
    return os.path.basename(str(path_or_url).split("?")[0])


def _extract_user_id_from_filename(filename: str) -> Optional[str]:
    m = USER_ID_IN_NAME_RE.search(filename or "")
    return m.group(1) if m else None


def _extract_session_id_from_filename(filename: str) -> Optional[str]:
    base = _basename(filename)
    if base.startswith("session_original_"):
        tail = base[len("session_original_"):]
        return os.path.splitext(tail)[0]
    if base.startswith("session_"):
        parts = os.path.splitext(base)[0].split("_")
        if len(parts) >= 4:
            return "_".join(parts[:3])
    return None


def _infer_image_owner_user_id(filename: str) -> Optional[str]:
    filename = _basename(filename)
    user_id = _extract_user_id_from_filename(filename)
    if user_id:
        return user_id
    session_id = _extract_session_id_from_filename(filename)
    if session_id:
        session = db_manager.get_makeup_session(session_id)
        if session:
            return str(session.get("user_id") or "").strip() or None
    return None


def _user_can_access_image(token_user_id: str, filename: str) -> bool:
    image_ref = str(filename or "")
    if not image_ref or not token_user_id:
        return False
    if _extract_user_id_from_filename(image_ref) == token_user_id:
        return True
    owner = _infer_image_owner_user_id(image_ref)
    if owner and owner == token_user_id:
        return True
    return False


def _resolve_image_path(path_or_url: str) -> Optional[str]:
    if not path_or_url:
        return None
    if os.path.isabs(path_or_url) and os.path.exists(path_or_url):
        return path_or_url
    normalized = str(path_or_url).split("?", 1)[0].replace("\\", "/")
    for marker, roots in [
        ("/api/media/images/output/", [OUTPUTS_DIR, TEMP_OUTPUTS_DIR]),
        ("/api/media/images/upload/", [UPLOADS_DIR, TEMP_UPLOADS_DIR]),
        ("/api/media/images/avatar/", [AVATARS_DIR]),
        ("database/images/outputs/", [OUTPUTS_DIR]),
        ("database/images/temp/outputs/", [TEMP_OUTPUTS_DIR]),
        ("database/images/uploads/", [UPLOADS_DIR]),
        ("database/images/temp/uploads/", [TEMP_UPLOADS_DIR]),
        ("database/images/avatar/", [AVATARS_DIR]),
    ]:
        if marker in normalized:
            relative = normalized.split(marker, 1)[1].lstrip("/")
            for root in roots:
                candidate = os.path.join(root, relative.replace("/", os.sep))
                if os.path.exists(candidate):
                    return candidate
    base = _basename(path_or_url)
    for root in [OUTPUTS_DIR, TEMP_OUTPUTS_DIR, UPLOADS_DIR, TEMP_UPLOADS_DIR, AVATARS_DIR]:
        candidate = os.path.join(root, base)
        if os.path.exists(candidate):
            return candidate
    if os.path.exists(path_or_url):
        return path_or_url
    return None


def _build_media_subdir(biz_type: str, user_id: str) -> str:
    now = datetime.now(_UTC_PLUS_8)
    return os.path.join(biz_type, user_id, now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"))


def _is_temporary_biz_type(biz_type: str) -> bool:
    return biz_type in {"corrected", "session_original", "session_render", "pca_input", "pca_result", "debug", "plan_cover"}


def _save_media_file(file: UploadFile, *, biz_type: str, user_id: str) -> Tuple[str, str, int]:
    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    subdir = _build_media_subdir(biz_type, user_id)
    if biz_type == "avatar":
        root_dir = AVATARS_DIR
    else:
        root_dir = TEMP_UPLOADS_DIR if _is_temporary_biz_type(biz_type) else UPLOADS_DIR
    abs_dir = os.path.join(root_dir, subdir)
    os.makedirs(abs_dir, exist_ok=True)
    filename = f"{biz_type}_{user_id}_{uuid.uuid4().hex[:16]}{ext}"
    abs_path = os.path.join(abs_dir, filename)
    relative_path = os.path.join(subdir, filename)
    return abs_path, relative_path, 0


def _build_output_media_path(*, biz_type: str, user_id: str, filename_stem: str, ext: str = ".jpg") -> Tuple[str, str, str]:
    subdir = _build_media_subdir(biz_type, user_id)
    output_root = TEMP_OUTPUTS_DIR if _is_temporary_biz_type(biz_type) else OUTPUTS_DIR
    abs_dir = os.path.join(output_root, subdir)
    os.makedirs(abs_dir, exist_ok=True)
    filename = f"{filename_stem}_{uuid.uuid4().hex[:12]}{ext}"
    relative_path = os.path.join(subdir, filename)
    abs_path = os.path.join(abs_dir, filename)
    return abs_path, relative_path, filename


def _promote_temp_output_file(*, user_id: str, biz_type: str, relative_path: str) -> Tuple[str, str, str]:
    relative_path = str(relative_path or "").replace("/", os.sep)
    src_abs_path = os.path.join(TEMP_OUTPUTS_DIR, relative_path)
    ext = os.path.splitext(relative_path)[1].lower() or ".jpg"
    stem = os.path.splitext(os.path.basename(relative_path))[0]
    dst_abs_path, dst_relative_path, dst_filename = _build_output_media_path(
        biz_type=biz_type,
        user_id=user_id,
        filename_stem=stem,
        ext=ext,
    )
    if os.path.exists(src_abs_path):
        os.makedirs(os.path.dirname(dst_abs_path), exist_ok=True)
        shutil.move(src_abs_path, dst_abs_path)
    return dst_abs_path, dst_relative_path, dst_filename


def _promote_session_temp_images(*, user_id: str, session_id: str) -> List[Dict[str, str]]:
    moved: List[Dict[str, str]] = []
    for row in db_manager.list_session_images(session_id):
        image_id = str(row.get("image_id") or "").strip()
        image_type = str(row.get("image_type") or "").strip()
        stored_filename = str(row.get("stored_filename") or "").strip()
        file_path = str(row.get("file_path") or "").replace("\\", "/")
        if not image_id or not image_type or not stored_filename:
            continue
        if image_type not in {"session_original", "session_render", "plan_cover", "corrected"}:
            continue
        if "/temp/outputs/" not in file_path:
            continue
        relative_path = file_path.split("database/images/temp/outputs/", 1)[1]
        _, promoted_relative, promoted_filename = _promote_temp_output_file(
            user_id=user_id,
            biz_type=image_type,
            relative_path=relative_path,
        )
        db_manager.update_user_image_storage(
            image_id,
            stored_filename=promoted_filename,
            file_path=os.path.join("database", "images", "outputs", promoted_relative),
        )
        moved.append({
            "image_id": image_id,
            "image_type": image_type,
            "from": file_path,
            "to": os.path.join("database", "images", "outputs", promoted_relative).replace("\\", "/"),
        })
    return moved


def _infer_demo_mode_from_session(session_id: str) -> Optional[str]:
    session_image = db_manager.get_latest_session_image(session_id, image_type="session_original") or {}
    group_id = str(session_image.get("group_id") or "")
    if group_id.startswith("demo_lh_"):
        return "lh"
    if group_id.startswith("demo_skb_"):
        return "skb"
    return None


async def _persist_upload_file(file: UploadFile, *, biz_type: str, user_id: str) -> Tuple[str, str, int]:
    abs_path, relative_path, _ = _save_media_file(file, biz_type=biz_type, user_id=user_id)
    content = await file.read()
    with open(abs_path, "wb") as f:
        f.write(content)
    return abs_path, relative_path, len(content)


def _hex_to_bgr(color_hex: str) -> Tuple[int, int, int]:
    value = str(color_hex or "").strip().lstrip("#")
    if len(value) != 6:
        raise ValueError("invalid color hex")
    return int(value[4:6], 16), int(value[2:4], 16), int(value[0:2], 16)


def _image_difference_score(image_a: np.ndarray, image_b: np.ndarray) -> float:
    if image_a is None or image_b is None:
        return 0.0
    if image_a.shape[:2] != image_b.shape[:2]:
        image_b = cv2.resize(image_b, (image_a.shape[1], image_a.shape[0]), interpolation=cv2.INTER_LINEAR)
    diff = cv2.absdiff(image_a, image_b)
    return float(np.mean(diff))


def _indices_to_points(landmarks: List[Any], indices: List[int], width: int, height: int) -> np.ndarray:
    points = []
    for idx in indices:
        if idx >= len(landmarks):
            continue
        lm = landmarks[idx]
        if hasattr(lm, 'x') and hasattr(lm, 'y'):
            x = float(lm.x)
            y = float(lm.y)
        elif isinstance(lm, (list, tuple, np.ndarray)) and len(lm) >= 2:
            x = float(lm[0])
            y = float(lm[1])
        else:
            continue

        if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
            px = int(x * width)
            py = int(y * height)
        else:
            px = int(x)
            py = int(y)

        px = max(0, min(width - 1, px))
        py = max(0, min(height - 1, py))
        points.append([px, py])
    return np.array(points, dtype=np.int32)


def _apply_color_render(
    image: np.ndarray,
    landmarks: List[Any],
    category: str,
    color_hex: str,
    output_path: str,
    apply_area: Optional[str] = None,
    opacity: Optional[float] = None,
    feather: Optional[int] = None,
    render_mode: Optional[int] = None,
    transparency_max: Optional[float] = None,
) -> None:
    height, width = image.shape[:2]
    color = _hex_to_bgr(color_hex)
    mask = np.zeros((height, width), dtype=np.uint8)
    category_norm = str(category or "").strip().lower()
    apply_area_norm = str(apply_area or "").strip().lower()
    if category_norm in {"lip", "brow", "eye", "contour", "base"}:
        area = category_norm
    else:
        area = apply_area_norm or category_norm

    def fill_polygon(indices: List[int], value: int = 255) -> None:
        pts = _indices_to_points(landmarks, indices, width, height)
        if len(pts) >= 3:
            cv2.fillPoly(mask, [pts], value)

    def fill_expanded_eye(indices: List[int], value: int = 255, expand_ratio_x: float = 0.18, expand_ratio_y: float = 0.35) -> None:
        pts = _indices_to_points(landmarks, indices, width, height)
        if len(pts) < 3:
            return
        center = np.mean(pts, axis=0)
        expanded = []
        for px, py in pts:
            dx = px - center[0]
            dy = py - center[1]
            ex = int(center[0] + dx * (1.0 + expand_ratio_x))
            ey = int(center[1] + dy * (1.0 + expand_ratio_y))
            expanded.append([max(0, min(width - 1, ex)), max(0, min(height - 1, ey))])
        expanded_pts = np.array(expanded, dtype=np.int32)
        hull = cv2.convexHull(expanded_pts)
        cv2.fillConvexPoly(mask, hull, value)

    def fill_contour_patch(side: str, value: int = 255) -> None:
        if len(landmarks) < 455:
            return
        nose = np.array(landmarks[4] if len(landmarks) > 4 else [width // 2, height // 2], dtype=np.float32)
        chin = np.array(landmarks[152] if len(landmarks) > 152 else [width // 2, int(height * 0.82)], dtype=np.float32)
        if side == "left":
            nose_side_top = np.array(landmarks[117] if len(landmarks) > 117 else landmarks[49], dtype=np.float32)
            nose_side_mid = np.array(landmarks[118] if len(landmarks) > 118 else landmarks[50], dtype=np.float32)
            jaw_outer = np.array(landmarks[172], dtype=np.float32)
            jaw_inner = np.array(landmarks[150] if len(landmarks) > 150 else landmarks[149], dtype=np.float32)
        else:
            nose_side_top = np.array(landmarks[346] if len(landmarks) > 346 else landmarks[279], dtype=np.float32)
            nose_side_mid = np.array(landmarks[347] if len(landmarks) > 347 else landmarks[280], dtype=np.float32)
            jaw_outer = np.array(landmarks[397], dtype=np.float32)
            jaw_inner = np.array(landmarks[379] if len(landmarks) > 379 else landmarks[378], dtype=np.float32)

        nose_patch = np.array([
            nose_side_top * 0.80 + nose * 0.20,
            nose_side_top * 0.55 + nose * 0.45,
            nose_side_mid * 0.45 + nose * 0.55,
            nose_side_mid * 0.72 + chin * 0.28,
        ], dtype=np.int32)
        jaw_patch = np.array([
            jaw_outer * 0.78 + chin * 0.22,
            jaw_inner * 0.72 + chin * 0.28,
            jaw_inner * 0.58 + chin * 0.42,
            jaw_outer * 0.62 + chin * 0.38,
        ], dtype=np.int32)
        cv2.fillConvexPoly(mask, nose_patch, value)
        cv2.fillConvexPoly(mask, jaw_patch, value)

    def face_hull_points() -> np.ndarray:
        pts: List[List[int]] = []
        for lm in landmarks:
            if hasattr(lm, 'x') and hasattr(lm, 'y'):
                x = float(lm.x)
                y = float(lm.y)
            elif isinstance(lm, (list, tuple, np.ndarray)) and len(lm) >= 2:
                x = float(lm[0])
                y = float(lm[1])
            else:
                continue
            if 0 <= x <= 1 and 0 <= y <= 1:
                px = int(x * width)
                py = int(y * height)
            else:
                px = int(x)
                py = int(y)
            px = max(0, min(width - 1, px))
            py = max(0, min(height - 1, py))
            pts.append([px, py])
        return np.array(pts, dtype=np.int32)

    final_opacity = float(opacity if opacity is not None else 0.45)
    final_feather = int(feather if feather is not None else 7)
    final_render_mode = int(render_mode if render_mode is not None else 0)

    if area in {"lip", "lips"}:
        fill_polygon(LIPS_INDICES)
        final_opacity = float(opacity if opacity is not None else 0.78)
        final_feather = int(feather if feather is not None else 5)
    elif area in {"brow", "eyebrow", "eyebrows"}:
        fill_polygon(LEFT_BROW_INDICES)
        fill_polygon(RIGHT_BROW_INDICES)
        final_opacity = float(opacity if opacity is not None else 0.62)
        final_feather = int(feather if feather is not None else 3)
    elif area in {"eye", "eyes"}:
        fill_expanded_eye(LEFT_EYE_SOCKET_INDICES)
        fill_expanded_eye(RIGHT_EYE_SOCKET_INDICES)
        fill_polygon(LEFT_EYE_INDICES, 0)
        fill_polygon(RIGHT_EYE_INDICES, 0)
        final_opacity = float(opacity if opacity is not None else 0.48)
        final_feather = int(feather if feather is not None else 8)
        final_render_mode = int(render_mode if render_mode is not None else 1)
    elif area in {"contour", "cheek", "cheeks"}:
        if len(landmarks) >= 455:
            fill_contour_patch("left")
            fill_contour_patch("right")
        else:
            fill_polygon(LEFT_CONTOUR_INDICES)
            fill_polygon(RIGHT_CONTOUR_INDICES)
        final_opacity = float(opacity if opacity is not None else 0.15)
        final_feather = int(feather if feather is not None else 20)
    else:
        hull_pts = face_hull_points()
        if len(hull_pts) >= 3:
            hull = cv2.convexHull(hull_pts)
            cv2.fillConvexPoly(mask, hull, 180)
        fill_polygon(LIPS_INDICES, 0)
        fill_polygon(LEFT_EYE_INDICES, 0)
        fill_polygon(RIGHT_EYE_INDICES, 0)
        final_opacity = float(opacity if opacity is not None else 0.30)
        final_feather = int(feather if feather is not None else 15)

    final_feather = max(1, final_feather)
    alpha_cap = float(transparency_max if transparency_max is not None else final_opacity)
    alpha_value = min(max(final_opacity, 0.0), max(alpha_cap, 0.0), 1.0)

    kernel = final_feather * 2 + 1
    if kernel % 2 == 0:
        kernel += 1
    soft_mask = cv2.GaussianBlur(mask, (kernel, kernel), 0)
    alpha_map = (soft_mask.astype(np.float32) / 255.0) * alpha_value

    base = image.astype(np.float32)
    color_layer = np.full_like(image, color, dtype=np.uint8).astype(np.float32)
    if final_render_mode == 1:
        color_layer = base * (color_layer / 255.0)

    result = base * (1.0 - alpha_map[..., None]) + color_layer * alpha_map[..., None]
    result = np.clip(result, 0, 255).astype(np.uint8)
    cv2.imwrite(output_path, result)


def _apply_style_render(image: np.ndarray, style: str, output_path: str) -> None:
    render = image.copy()
    landmarks_result = face_detection.detect_face_landmarks_mediapipe(image)
    _, landmarks = landmarks_result if isinstance(landmarks_result, tuple) else (None, None)

    def apply_step(base_image: np.ndarray, category: str, color_hex: str) -> np.ndarray:
        _apply_color_render(base_image, landmarks, category=category, color_hex=color_hex, output_path=output_path)
        next_render = cv2.imread(output_path)
        return next_render if next_render is not None else base_image

    if style == "clean":
        render = cv2.bilateralFilter(render, 9, 45, 45)
        render = cv2.convertScaleAbs(render, alpha=1.06, beta=6)
        hsv = cv2.cvtColor(render, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 0.96, 0, 255).astype(np.uint8)
        render = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        if landmarks is not None:
            render = apply_step(render, "base", "#F3D7C3")
            render = apply_step(render, "brow", "#5C4033")
            render = apply_step(render, "lip", "#D98C8C")
            cv2.imwrite(output_path, render)
            return
    elif style == "business":
        render = cv2.bilateralFilter(render, 11, 55, 55)
        render = cv2.convertScaleAbs(render, alpha=1.02, beta=2)
        hsv = cv2.cvtColor(render, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 0.88, 0, 255).astype(np.uint8)
        render = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        if landmarks is not None:
            render = apply_step(render, "base", "#E7C6AE")
            render = apply_step(render, "contour", "#9C6B4E")
            render = apply_step(render, "brow", "#4A342A")
            render = apply_step(render, "lip", "#B97070")
            cv2.imwrite(output_path, render)
            return
    elif style == "idol":
        render = cv2.bilateralFilter(render, 13, 70, 70)
        render = cv2.convertScaleAbs(render, alpha=1.10, beta=12)
        hsv = cv2.cvtColor(render, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.08, 0, 255).astype(np.uint8)
        render = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        if landmarks is not None:
            render = apply_step(render, "base", "#F1D2CE")
            render = apply_step(render, "eye", "#C08AA8")
            render = apply_step(render, "brow", "#5B3A32")
            render = apply_step(render, "lip", "#D45F7A")
            render = apply_step(render, "contour", "#A86852")
            cv2.imwrite(output_path, render)
            return
    cv2.imwrite(output_path, render)


def _render_style_image(image_bgr: np.ndarray, style: str, output_path: str, session_id: str) -> str:
    normalized_style = str(style or "").strip().lower()
    engine, err = _get_makeup_engine()
    if engine is None:
        raise RuntimeError(err or "Makeup model not loaded")

    from PIL import Image

    result_img = engine.process(
        Image.fromarray(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)),
        style=normalized_style,
        demo_mode=_infer_demo_mode_from_session(session_id),
    )
    result_img.save(output_path, quality=95)
    return "gan"


def _build_style_cache_key(*, base_path: str, style: str, session_id: str) -> str:
    try:
        stat = os.stat(base_path)
        fingerprint = f"{base_path}|{stat.st_size}|{int(stat.st_mtime)}|{style}|{session_id}"
    except Exception:
        fingerprint = f"{base_path}|{style}|{session_id}"
    return hashlib.md5(fingerprint.encode("utf-8")).hexdigest()


def _get_cached_style_render(cache_key: str) -> Optional[str]:
    with _style_render_cache_lock:
        payload = _style_render_cache.get(cache_key)
    if not payload:
        return None
    abs_path = payload.get("abs_path") or ""
    image_url = payload.get("image_url") or ""
    if abs_path and image_url and os.path.exists(abs_path):
        return image_url
    return None


def _set_cached_style_render(cache_key: str, *, abs_path: str, image_url: str) -> None:
    with _style_render_cache_lock:
        _style_render_cache[cache_key] = {"abs_path": abs_path, "image_url": image_url}
        if len(_style_render_cache) > 64:
            oldest_key = next(iter(_style_render_cache))
            if oldest_key != cache_key:
                _style_render_cache.pop(oldest_key, None)


def _classify_season(image: np.ndarray, landmarks: List[Any]) -> Dict[str, Any]:
    h, w = image.shape[:2]
    xs = [int(lm.x * w) for lm in landmarks if 0 <= lm.x <= 1]
    ys = [int(lm.y * h) for lm in landmarks if 0 <= lm.y <= 1]
    if not xs or not ys:
        raise ValueError("NO_FACE_LANDMARKS")
    x1, x2 = max(0, min(xs)), min(w, max(xs))
    y1, y2 = max(0, min(ys)), min(h, max(ys))
    face = image[y1:y2, x1:x2]
    if face.size == 0:
        raise ValueError("NO_FACE")
    lab = cv2.cvtColor(face, cv2.COLOR_BGR2LAB)
    l_mean = float(np.mean(lab[:, :, 0]))
    a_mean = float(np.mean(lab[:, :, 1]) - 128.0)
    b_mean = float(np.mean(lab[:, :, 2]) - 128.0)
    hsv = cv2.cvtColor(face, cv2.COLOR_BGR2HSV)
    s_mean = float(np.mean(hsv[:, :, 1]))
    v_mean = float(np.mean(hsv[:, :, 2]))
    std_l = float(np.std(lab[:, :, 0]))

    if v_mean < 40:
        raise ValueError("TOO_DARK")

    feats = np.array([l_mean, a_mean, b_mean, v_mean, s_mean, std_l], dtype=np.float32)
    z = (feats - PCA_FEATURE_MEAN) / np.maximum(PCA_FEATURE_STD, 1e-6)
    pca = PCA_COMPONENTS.dot(z)

    season_type = "Warm Autumn"
    best_dist = None
    for season, center in SEASON_PCA_CENTERS.items():
        dist = float(np.linalg.norm(pca - center))
        if best_dist is None or dist < best_dist:
            best_dist = dist
            season_type = season

    tone = "warm" if b_mean >= 0 else "cool"
    confidence = round(float(max(0.55, min(0.96, 1.0 / (1.0 + (best_dist or 0.5) * 0.35)))), 4)

    return {
        "season_type": season_type,
        "tone": tone,
        "confidence": confidence,
        "recommended_colors": SEASON_COLOR_MAP[season_type]["recommended"],
        "avoid_colors": SEASON_COLOR_MAP[season_type]["avoid"],
        "model": "builtin_pca_rule_v1",
        "features": {"lab_l": l_mean, "lab_a": a_mean, "lab_b": b_mean, "hsv_s": s_mean, "hsv_v": v_mean, "lab_std_l": std_l},
    }


def _score_makeup_look(session: Dict[str, Any]) -> Dict[str, Any]:
    applied = _build_canonical_applied_items(session.get("applied_products"))
    season = None
    user_row = db_manager.get_user_by_id(str(session.get("user_id") or "").strip()) or {}
    if user_row and user_row.get("season_type"):
        season = str(user_row.get("season_type"))
    color_score = 68.0
    completeness_score = min(100.0, 55.0 + len(applied) * 11.0)
    match_bonus = 0.0
    matched_products = []
    for item in applied:
        product = db_manager.get_product_by_id(str(item.get("product_id") or "").strip())
        if not product:
            continue
        season_tag = str(product.get("season_tag") or "").strip()
        if season and season_tag == season:
            match_bonus += 6.0
            matched_products.append(product.get("name"))
    total = min(98.0, round((color_score + completeness_score) / 2.0 + match_bonus, 2))
    feedback = []
    if matched_products:
        feedback.append("当前妆容与个人季型匹配度较高。")
    if len(applied) < 2:
        feedback.append("可继续补充眉部/唇部等关键步骤提升完整度。")
    else:
        feedback.append("妆面完整度不错，适合继续微调细节。")
    return {"score": total, "sub_scores": {"color": round(color_score, 2), "completeness": round(completeness_score, 2), "match_bonus": round(match_bonus, 2)}, "feedback": feedback}


def _build_product_tags(product: Dict[str, Any], season: Optional[str] = None) -> List[str]:
    tags: List[str] = []
    season_tag = str(product.get("season_tag") or "").strip()
    category = str(product.get("category") or "").strip()
    price = float(product.get("price") or 0)
    if season and season_tag == season:
        tags.append("PCA推荐")
    if category in {"lip", "brow"}:
        tags.append("新手友好")
    if price and price <= 220:
        tags.append("日常通勤")
    if category in {"eye", "lip"}:
        tags.append("热门试妆")
    return tags[:2]


def _build_product_reason(product: Dict[str, Any], season: Optional[str] = None) -> str:
    name = str(product.get("name") or "该商品")
    season_tag = str(product.get("season_tag") or "").strip()
    category = str(product.get("category") or "").strip()
    if season and season_tag == season:
        return f"{name} 与你的 {season} 季型匹配，适合作为优先推荐商品。"
    if category == "lip":
        return f"{name} 适合作为快速提气色的唇部推荐。"
    if category == "brow":
        return f"{name} 适合作为入门级眉部推荐。"
    if category == "contour":
        return f"{name} 适合增强面部轮廓层次。"
    return f"{name} 适合作为当前场景的推荐候选。"


def _recommended_style_templates(season: str) -> List[Dict[str, Any]]:
    season = str(season or "").strip() or "Warm Autumn"
    if season == "Cool Winter":
        return [
            {"template_id": "interview_clean", "name": "面试清爽", "scene_tag": "面试清爽", "categories": ["base", "brow", "lip"]},
            {"template_id": "business_stable", "name": "商务稳重", "scene_tag": "商务稳重", "categories": ["base", "brow", "contour", "lip"]},
        ]
    return [
        {"template_id": "daily_commute", "name": "日常通勤", "scene_tag": "日常通勤", "categories": ["base", "brow", "lip"]},
        {"template_id": "date_vibe", "name": "约会氛围", "scene_tag": "约会氛围", "categories": ["base", "eye", "lip"]},
        {"template_id": "business_stable", "name": "商务稳重", "scene_tag": "商务稳重", "categories": ["base", "brow", "contour", "lip"]},
    ]


def _detect_face_occlusion(blur_result: Dict[str, Any]) -> bool:
    try:
        left_eye = float(blur_result.get("left_eye_score") or 0)
        right_eye = float(blur_result.get("right_eye_score") or 0)
        mouth = float(blur_result.get("mouth_score") or 0)
    except Exception:
        return False
    eye_occluded = left_eye < 10 and right_eye < 10 and mouth >= 18
    mouth_occluded = mouth < 8 and max(left_eye, right_eye) >= 18
    return eye_occluded or mouth_occluded


class SendCodeRequest(BaseModel):
    phone: str = Field(..., examples=["13800138000"])
    type: str = Field(..., description="register | login | reset_password", examples=["register"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"phone": "13800138000", "type": "register"},
                {"phone": "13800138000", "type": "login"},
            ]
        }
    }


class RegisterRequest(BaseModel):
    phone: str = Field(..., examples=["13800138000"])
    password: str = Field(..., examples=["123456"])
    confirmPassword: str = Field(..., examples=["123456"])
    code: str = Field(..., examples=["123456"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"phone": "13800138000", "password": "123456", "confirmPassword": "123456", "code": "123456"}
            ]
        }
    }


class LoginRequest(BaseModel):
    phone: str = Field(..., examples=["13800138000"])
    password: Optional[str] = Field(None, examples=["123456"])
    code: Optional[str] = Field(None, examples=["123456"])
    loginType: str = Field("password", examples=["password"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"phone": "13800138000", "password": "123456", "loginType": "password"},
                {"phone": "13800138000", "code": "123456", "loginType": "code"},
            ]
        }
    }


class ResetPasswordRequest(BaseModel):
    phone: str = Field(..., examples=["13800138000"])
    code: str = Field(..., examples=["123456"])
    newPassword: str = Field(..., examples=["654321"])

    model_config = {
        "json_schema_extra": {
            "examples": [{"phone": "13800138000", "code": "123456", "newPassword": "654321"}]
        }
    }


class UpdateProfileRequest(BaseModel):
    avatar: Optional[str] = Field(None, examples=["https://example.com/avatar.jpg"])

    model_config = {
        "json_schema_extra": {
            "examples": [{"avatar": "https://example.com/avatar.jpg"}]
        }
    }


class UpdateNicknameRequest(BaseModel):
    nickname: str = Field(..., examples=["新昵称"])

    model_config = {
        "json_schema_extra": {
            "examples": [{"nickname": "新昵称"}]
        }
    }


class UpdateAvatarRequest(BaseModel):
    avatar: str = Field(..., examples=["https://example.com/avatar.jpg"])


class MediaUploadResponse(BaseModel):
    file_url: str
    relative_path: str
    biz_type: str


class PreferenceRequest(BaseModel):
    preferred_scenes: List[str] = Field(default_factory=list, examples=[["日常通勤", "约会氛围"]])
    preferred_categories: List[str] = Field(default_factory=list, examples=[["lip", "brow"]])
    preferred_finishes: List[str] = Field(default_factory=list, examples=[["natural", "matte"]])
    budget_min: float = Field(0, examples=[99])
    budget_max: float = Field(0, examples=[299])

    model_config = {
        "json_schema_extra": {
            "examples": [{"preferred_scenes": ["日常通勤", "约会氛围"], "preferred_categories": ["lip", "brow"], "preferred_finishes": ["natural", "matte"], "budget_min": 99, "budget_max": 299}]
        }
    }


class SessionRequest(BaseModel):
    session_id: str = Field(..., examples=["session_abcd1234ef56"])


class ResetPartRequest(BaseModel):
    session_id: str = Field(..., examples=["session_abcd1234ef56"])
    category: str = Field(..., examples=["lip"])

    model_config = {"json_schema_extra": {"examples": [{"session_id": "session_abcd1234ef56", "category": "lip"}]}}


class CartItemRequest(BaseModel):
    product_id: str = Field(..., examples=["lip_001"])
    quantity: int = Field(1, examples=[2])
    user_id: Optional[str] = Field(None, examples=["user_xxx"])

    model_config = {"json_schema_extra": {"examples": [{"product_id": "lip_001", "quantity": 2}]}}


class CartBundleRequest(BaseModel):
    bundle_id: Optional[str] = Field(None, examples=["bundle_autumn_001"])
    product_ids: List[str] = Field(default_factory=list, examples=[["lip_001", "brow_001", "base_001"]])
    user_id: Optional[str] = Field(None, examples=["user_xxx"])

    model_config = {"json_schema_extra": {"examples": [{"bundle_id": "bundle_autumn_001", "product_ids": []}, {"product_ids": ["lip_001", "brow_001", "base_001"]}]}}


class CartBulkItem(BaseModel):
    product_id: str = Field(..., examples=["lip_001"])
    quantity: int = Field(0, examples=[2])


class CartSetBulkRequest(BaseModel):
    items: List[CartBulkItem] = Field(default_factory=list)
    user_id: Optional[str] = Field(None, examples=["user_xxx"])

    model_config = {"json_schema_extra": {"examples": [{"items": [{"product_id": "lip_001", "quantity": 2}, {"product_id": "brow_001", "quantity": 1}]}]}}


class SaveSchemeRequest(BaseModel):
    session_id: str = Field(..., examples=["session_abcd1234ef56"])
    scheme_name: str = Field(..., examples=["通勤妆方案"])
    user_id: Optional[str] = Field(None, examples=["user_xxx"])

    model_config = {"json_schema_extra": {"examples": [{"session_id": "session_abcd1234ef56", "scheme_name": "通勤妆方案"}]}}


class DeleteSchemeRequest(BaseModel):
    scheme_id: str = Field(..., examples=["scheme_1234567890ab"])
    user_id: Optional[str] = Field(None, examples=["user_xxx"])

    model_config = {"json_schema_extra": {"examples": [{"scheme_id": "scheme_1234567890ab"}]}}


class SchemeDetailRequest(BaseModel):
    scheme_id: str = Field(..., examples=["scheme_1234567890ab"])


class AdminProductRequest(BaseModel):
    p_id: Optional[str] = Field(None, examples=["lip_001"])
    name: Optional[str] = Field(None, examples=["柔雾唇釉 01"])
    category: Optional[str] = Field(None, examples=["lip"])
    apply_area: Optional[str] = Field(None, examples=["lips"])
    render_hex: Optional[str] = Field(None, examples=["#B14A5A"])

    model_config = {"json_schema_extra": {"examples": [{"p_id": "lip_001", "name": "柔雾唇釉 01", "category": "lip", "apply_area": "lips", "render_hex": "#B14A5A"}]}}


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)) -> Dict[str, Any]:
    if not credentials or not credentials.credentials:
        raise api_error(401, "UNAUTHORIZED", "缺少 Authorization Bearer token")
    token = credentials.credentials.strip()
    user = db_manager.get_user_by_token(token)
    if not user:
        raise api_error(401, "UNAUTHORIZED", "登录态无效或已过期")
    return user


def get_admin_user(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if not _is_admin_user(user):
        raise api_error(403, "FORBIDDEN", "仅管理员可访问")
    return user


@app.get("/health", tags=["system"], summary="健康检查")
def health():
    return ok({"status": "ok"}, "health ok")


@app.post("/api/auth/send-code", tags=["auth"], summary="发送验证码")
def send_code(
    payload: SendCodeRequest = Body(
        ...,
        examples={
            "register": {"summary": "注册验证码", "value": {"phone": "13800138000", "type": "register"}},
            "login": {"summary": "登录验证码", "value": {"phone": "13800138000", "type": "login"}},
        },
    ),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
):
    phone = str(payload.phone or "").strip()
    if not phone:
        raise api_error(400, "INVALID_PARAMS", "缺少 phone")
    if payload.type not in {"register", "login", "reset_password"}:
        raise api_error(400, "INVALID_PARAMS", "type 必须是 register/login/reset_password")
    existing_user = db_manager.get_user_by_phone(phone)
    if payload.type == "register" and existing_user:
        raise api_error(409, "PHONE_EXISTS", "手机号已注册")
    if payload.type in {"login", "reset_password"} and not existing_user:
        raise api_error(404, "USER_NOT_FOUND", "手机号未注册")
    if payload.type == "reset_password":
        if not credentials or not credentials.credentials:
            raise api_error(401, "UNAUTHORIZED", "重置密码发送验证码需要先登录")
        token = credentials.credentials.strip()
        user = db_manager.get_user_by_token(token)
        if not user:
            raise api_error(401, "UNAUTHORIZED", "登录态无效或已过期")
        token_phone = str(user.get("phone") or "").strip()
        if not token_phone:
            raise api_error(400, "INVALID_USER_STATE", "当前登录用户未绑定手机号")
        if token_phone != phone:
            raise api_error(403, "FORBIDDEN", "仅允许给当前登录手机号发送重置验证码")
    code = _generate_mock_code()
    try:
        code_id = db_manager.create_verification_code(phone, payload.type, code, channel="mock", meta={"provider": "console"})
        _send_verification_code(phone, payload.type, code, channel="mock")
    except Exception as e:
        app.logger.exception(f"send code failed: {e}")
        raise api_error(500, "SEND_CODE_FAILED", str(e))
    return ok({"code_id": code_id, "mock": True, "expires_in_seconds": 300}, "验证码已发送")


@app.post("/api/auth/register", tags=["auth"], summary="注册")
def register(
    payload: RegisterRequest = Body(
        ...,
        examples={
            "default": {"summary": "注册示例", "value": {"phone": "13800138000", "password": "123456", "confirmPassword": "123456", "code": "123456"}}
        },
    )
):
    phone = (payload.phone or "").strip()
    password = (payload.password or "").strip()
    confirm_password = (payload.confirmPassword or "").strip()
    code = (payload.code or "").strip()
    if not phone:
        raise api_error(400, "INVALID_PARAMS", "缺少 phone")
    if not password or len(password) < 6:
        raise api_error(400, "INVALID_PARAMS", "密码长度至少6位")
    if not confirm_password:
        raise api_error(400, "INVALID_PARAMS", "缺少确认密码 confirmPassword")
    if password != confirm_password:
        raise api_error(400, "PASSWORD_CONFIRM_MISMATCH", "两次输入的密码不一致")
    if not code:
        raise api_error(400, "INVALID_PARAMS", "缺少验证码 code")
    if db_manager.get_user_by_phone(phone):
        raise api_error(409, "PHONE_EXISTS", "手机号已注册")
    ok_flag, verify_result = db_manager.check_verification_code(phone, "register", code)
    if not ok_flag:
        raise api_error(400, str(verify_result), "验证码无效或已过期")
    try:
        user_id = db_manager.create_user_with_phone(phone=phone, password=password, nickname="", avatar=_default_avatar_url())
        db_manager.mark_verification_code_used(verify_result["code_id"], status="used")
    except Exception as e:
        app.logger.exception(f"register failed: {e}")
        raise api_error(500, "REGISTER_FAILED", str(e))
    token = db_manager.create_auth_token(user_id=user_id)
    db_manager.update_user_last_login(user_id)
    created_user = db_manager.get_user_by_id(user_id) or {}
    payload = {
        "user_id": user_id,
        "token": token,
        "nickname": created_user.get("nickname"),
        "phone": phone,
        "user": {
            "id": user_id,
            "phone": phone,
            "avatar": created_user.get("avatar"),
            "nickname": created_user.get("nickname"),
        },
    }
    return JSONResponse(status_code=201, content=ok(payload, "注册成功"))


@app.post("/api/auth/login", tags=["auth"], summary="登录")
def login(
    payload: LoginRequest = Body(
        ...,
        examples={
            "password_login": {"summary": "密码登录", "value": {"phone": "13800138000", "password": "123456", "loginType": "password"}},
            "code_login": {"summary": "验证码登录", "value": {"phone": "13800138000", "code": "123456", "loginType": "code"}},
        },
    )
):
    code = (payload.code or "").strip()
    phone = (payload.phone or "").strip()
    password = (payload.password or "").strip()
    login_type = (payload.loginType or "").strip() or ("code" if code else "password")
    if not phone:
        raise api_error(400, "INVALID_PARAMS", "缺少 phone")
    if login_type == "code":
        if not code:
            raise api_error(400, "INVALID_PARAMS", "验证码登录缺少 code")
        ok_flag, verify_result = db_manager.verify_code(phone, "login", code)
        if not ok_flag:
            raise api_error(400, str(verify_result), "验证码无效或已过期")
        user_row = db_manager.get_user_by_phone(phone)
        if not user_row:
            raise api_error(404, "USER_NOT_FOUND", "手机号未注册，请先注册")
    else:
        if not password or len(password) < 6:
            raise api_error(400, "INVALID_PARAMS", "密码长度至少6位")
        user_row = db_manager.get_user_by_phone(phone)
        if not user_row:
            raise api_error(404, "USER_NOT_FOUND", "手机号未注册，请先注册")
        if not db_manager.verify_password(password, user_row.get("password_hash") or ""):
            raise api_error(401, "PASSWORD_INCORRECT", "密码错误")
    token = db_manager.create_auth_token(user_id=user_row["user_id"])
    db_manager.update_user_last_login(user_row["user_id"])
    payload = {
        "user_id": user_row["user_id"],
        "token": token,
        "nickname": user_row.get("nickname") or phone,
        "phone": user_row.get("phone"),
        "user": {
            "id": user_row["user_id"],
            "phone": user_row.get("phone"),
            "avatar": user_row.get("avatar"),
            "nickname": user_row.get("nickname") or phone,
        },
    }
    return ok(payload, "登录成功")


@app.post("/api/auth/logout", tags=["auth"], summary="退出登录")
def logout(request: Request, _: Dict[str, Any] = Depends(get_current_user)):
    token = _extract_token()
    if not token:
        raise api_error(401, "UNAUTHORIZED", "缺少 Authorization Bearer token")
    db_manager.revoke_auth_token(token)
    return ok(None, "退出登录成功")


@app.post("/api/auth/reset-password", tags=["auth"], summary="重置密码")
def reset_password(
    payload: ResetPasswordRequest = Body(
        ...,
        examples={"default": {"summary": "重置密码示例", "value": {"phone": "13800138000", "code": "123456", "newPassword": "654321"}}},
    ),
    user: Dict[str, Any] = Depends(get_current_user),
):
    phone = (payload.phone or "").strip()
    code = (payload.code or "").strip()
    new_password = (payload.newPassword or "").strip()
    if not phone or not code or not new_password:
        raise api_error(400, "INVALID_PARAMS", "缺少 phone/code/newPassword")
    if len(new_password) < 6:
        raise api_error(400, "INVALID_PARAMS", "新密码长度至少6位")
    token_phone = str(user.get("phone") or "").strip()
    if not token_phone:
        raise api_error(400, "INVALID_USER_STATE", "当前登录用户未绑定手机号")
    if phone != token_phone:
        raise api_error(403, "FORBIDDEN", "仅允许重置当前登录手机号的密码")
    user_row = db_manager.get_user_by_phone(phone)
    if not user_row:
        raise api_error(404, "USER_NOT_FOUND", "手机号未注册")
    ok_flag, verify_result = db_manager.verify_code(phone, "reset_password", code)
    if not ok_flag:
        raise api_error(400, str(verify_result), "验证码无效或已过期")
    conn = db_manager.get_db_connection()
    conn.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ?", (db_manager.hash_password(new_password), db_manager.now_iso(), user_row["user_id"]))
    conn.commit()
    conn.close()
    return ok(None, "密码重置成功")


@app.get("/api/user/info", tags=["user"], summary="获取当前用户信息")
def user_info(user: Dict[str, Any] = Depends(get_current_user)):
    history = db_manager.list_user_recent_history(user["user_id"], limit=5)
    latest = _format_history_item_times(history[0]) if history else None
    payload = {"user_id": user.get("user_id"), "phone": user.get("phone"), "nickname": user.get("nickname"), "avatar": user.get("avatar"), "season_type": user.get("season_type"), "last_login_at": _format_cn_datetime(user.get("last_login_at")), "last_history": latest, "user": {"id": user.get("user_id"), "phone": user.get("phone"), "avatar": user.get("avatar"), "nickname": user.get("nickname")}}
    return ok(payload, "获取用户信息成功")


@app.put("/api/user/profile", tags=["user"], summary="更新用户资料")
def update_profile(
    payload: UpdateProfileRequest = Body(..., examples={"default": {"summary": "头像资料更新示例", "value": {"avatar": "https://example.com/avatar.jpg"}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    if payload.avatar is None:
        raise api_error(400, "INVALID_PARAMS", "至少提供 avatar 字段")
    updated = db_manager.update_user_profile(user["user_id"], avatar=payload.avatar)
    return ok({"user_id": updated.get("user_id"), "nickname": updated.get("nickname"), "avatar": updated.get("avatar"), "phone": updated.get("phone"), "season_type": updated.get("season_type")}, "个人资料更新成功")


@app.put("/api/user/nickname", tags=["user"], summary="单独修改昵称")
def update_nickname(
    payload: UpdateNicknameRequest = Body(..., examples={"default": {"summary": "修改昵称", "value": {"nickname": "新昵称"}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    nickname = str(payload.nickname or "").strip()
    if not nickname:
        raise api_error(400, "INVALID_PARAMS", "nickname 不能为空")
    try:
        updated = db_manager.update_user_nickname(user["user_id"], nickname)
    except ValueError as e:
        raise api_error(400, "INVALID_PARAMS", str(e))
    return ok({"user_id": updated.get("user_id"), "nickname": updated.get("nickname"), "avatar": updated.get("avatar")}, "昵称修改成功")


@app.post("/api/user/avatar/upload", tags=["user"], summary="上传用户头像")
async def upload_user_avatar(file: UploadFile = File(..., description="头像图片文件"), user: Dict[str, Any] = Depends(get_current_user)):
    user_id = str(user.get("user_id") or "").strip()
    if not user_id:
        raise api_error(400, "INVALID_USER_STATE", "当前登录用户不存在")
    if not file.filename:
        raise api_error(400, "INVALID_PARAMS", "缺少头像文件")
    mime_type = str(file.content_type or "").lower()
    if mime_type and not mime_type.startswith("image/"):
        raise api_error(400, "INVALID_IMAGE", "头像文件必须是图片")
    abs_path, relative_path, file_size = await _persist_upload_file(file, biz_type="avatar", user_id=user_id)
    avatar_url = _avatar_url(relative_path)
    updated = db_manager.update_user_avatar(user_id, avatar_url)
    db_manager.create_user_image(
        user_id=user_id,
        image_type="upload",
        stored_filename=os.path.basename(abs_path),
        file_path=os.path.join("database", "images", "avatar", relative_path),
        origin_filename=file.filename,
        mime_type=file.content_type,
        file_size=file_size,
        width=None,
        height=None,
    )
    return _api_success({"user_id": updated.get("user_id"), "avatar": updated.get("avatar"), "biz_type": "avatar", "relative_path": relative_path}, message="头像上传成功")


@app.get("/api/user/history", tags=["user"], summary="获取用户历史")
def user_history(limit: int = Query(default=20), user: Dict[str, Any] = Depends(get_current_user)):
    history = db_manager.list_user_recent_history(user["user_id"], limit=limit)
    return ok({"items": [_format_history_item_times(item) for item in history], "count": len(history)}, "获取历史记录成功")


@app.get("/api/user/images", tags=["user"], summary="获取用户图片列表")
def user_images(limit: int = Query(default=50), user: Dict[str, Any] = Depends(get_current_user)):
    rows = db_manager.list_user_images(str(user.get("user_id") or "").strip(), limit=limit)
    items = []
    for row in rows:
        item = dict(row)
        file_path = str(item.get("file_path") or "")
        image_type = str(item.get("image_type") or "")
        if file_path:
            normalized = file_path.replace("\\", "/")
            if "database/images/outputs/" in normalized:
                relative = normalized.split("database/images/outputs/", 1)[1]
                item["url"] = _output_url(relative)
            elif "database/images/uploads/" in normalized:
                relative = normalized.split("database/images/uploads/", 1)[1]
                item["url"] = _upload_url(relative)
            elif "database/images/avatar/" in normalized:
                relative = normalized.split("database/images/avatar/", 1)[1]
                item["url"] = _avatar_url(relative)
            else:
                stored_filename = str(item.get("stored_filename") or "")
                item["url"] = _output_url(stored_filename) if image_type == "corrected" else _upload_url(stored_filename)
        else:
            stored_filename = str(item.get("stored_filename") or "")
            item["url"] = _output_url(stored_filename) if image_type == "corrected" else _upload_url(stored_filename)
        items.append(_format_payload_times(item))
    return ok({"items": items, "count": len(items)}, "获取图片列表成功")


@app.delete("/api/user/images/{image_id}", tags=["user"], summary="删除用户图片")
def delete_user_image(image_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    user_id = str(user.get("user_id") or "").strip()
    row = db_manager.get_user_image(image_id, user_id)
    if not row:
        return _api_error("IMAGE_NOT_FOUND", "找不到图片", 404)
    file_path = str(row.get("file_path") or "")
    abs_path = _resolve_image_path(file_path)
    deleted = db_manager.delete_user_image(image_id, user_id)
    if not deleted:
        return _api_error("DELETE_FAILED", "删除图片失败", 500)
    if abs_path and os.path.exists(abs_path):
        try:
            os.remove(abs_path)
        except Exception:
            pass
    return _api_success({"image_id": image_id}, message="删除图片成功")


@app.get("/api/user/images/latest", tags=["user"], summary="获取用户最近一张可用图片")
def get_latest_user_image(user: Dict[str, Any] = Depends(get_current_user)):
    user_id = str(user.get("user_id") or "").strip()
    row = db_manager.get_latest_user_image(user_id, image_type="corrected") or db_manager.get_latest_user_image(user_id, image_type="upload")
    if not row:
        return _api_error("IMAGE_NOT_FOUND", "未找到可用图片", 404)
    filename = str(row.get("stored_filename") or "")
    image_type = str(row.get("image_type") or "")
    image_url = _output_url(filename) if image_type == "corrected" else _upload_url(filename)
    payload = {
        "image_id": row.get("image_id"),
        "image_type": image_type,
        "filename": filename,
        "file_path": row.get("file_path"),
        "url": image_url,
        "created_at": _format_cn_datetime(row.get("created_at")),
    }
    return _api_success(payload, message="获取最近图片成功")


@app.get("/api/user/preferences", tags=["user"], summary="获取用户偏好")
def get_preferences(user: Dict[str, Any] = Depends(get_current_user)):
    profile = db_manager.get_user_preferences(user["user_id"]) or {"preferred_scenes": [], "preferred_categories": [], "preferred_finishes": [], "budget_min": 0, "budget_max": 0}
    return ok(_format_payload_times(profile), "获取偏好设置成功")


@app.put("/api/user/preferences", tags=["user"], summary="更新用户偏好")
def put_preferences(
    payload: PreferenceRequest = Body(..., examples={"default": {"summary": "偏好更新示例", "value": {"preferred_scenes": ["日常通勤", "约会氛围"], "preferred_categories": ["lip", "brow"], "preferred_finishes": ["natural", "matte"], "budget_min": 99, "budget_max": 299}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    profile = db_manager.upsert_user_preferences(user_id=user["user_id"], preferred_scenes=payload.preferred_scenes or [], preferred_categories=payload.preferred_categories or [], preferred_finishes=payload.preferred_finishes or [], budget_min=payload.budget_min or 0, budget_max=payload.budget_max or 0)
    return ok(_format_payload_times(profile), "偏好设置更新成功")


@app.get("/api/pca/personalized_recommendations", tags=["recommend"], summary="个性化推荐")
def personalized_recommendations(limit: int = Query(default=10), user: Dict[str, Any] = Depends(get_current_user)):
    products = db_manager.get_personalized_recommendations(user["user_id"], limit=limit)
    behavior = db_manager.list_user_behavior_events(user["user_id"], limit=20)
    return ok(_format_payload_times({"products": products, "behavior_snapshot": behavior}), "获取个性化推荐成功")


@app.get("/api/recommend/pairs", tags=["recommend"], summary="搭配推荐")
def pair_recommendations(source_sku_id: str = Query(..., examples=["lip_001"]), limit: int = Query(default=6), _: Dict[str, Any] = Depends(get_current_user)):
    items = db_manager.list_pair_recommendations(source_sku_id, limit=limit)
    return ok(_format_payload_times({"source_sku_id": source_sku_id, "items": items}), "获取搭配推荐成功")


@app.get("/api/user/membership", tags=["user"], summary="获取会员信息")
def membership_profile(user: Dict[str, Any] = Depends(get_current_user)):
    profile = db_manager.get_membership_profile(str(user.get("user_id") or "").strip())
    return ok(_format_payload_times(profile), "获取会员信息成功")


@app.post("/api/pca/analyze", tags=["analysis"], summary="分析个人季型", description="multipart/form-data：image 为文件，user_id 可选；通常与当前登录用户一致。")
async def analyze_color_type(
    request: Request,
    image: UploadFile = File(..., description="待分析的人脸照片文件，例如 face.jpg"),
    user_id: Optional[str] = Form(default=None, description="可选，通常不传；若传入需与 Bearer Token 对应用户一致"),
    user: Dict[str, Any] = Depends(get_current_user),
):
    token_user_id = (user.get("user_id") or "").strip()
    requested_user_id = (user_id or "").strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    if not token_user_id:
        return _api_error("INVALID_PARAMS", "缺少 user_id", 400)

    temp_dir = tempfile.gettempdir()
    ext = os.path.splitext(image.filename or "")[1].lower() or ".jpg"
    temp_input = os.path.join(temp_dir, f"color_{uuid.uuid4()}{ext}")
    content = await image.read()
    with open(temp_input, "wb") as f:
        f.write(content)

    try:
        img = cv2.imread(temp_input)
        if img is None:
            return _api_error("INVALID_IMAGE", "图片无法读取", 400)

        file_size = os.path.getsize(temp_input) if os.path.exists(temp_input) else 0
        height, width = img.shape[:2]
        pca_image_id = db_manager.create_user_image(user_id=token_user_id, image_type="pca_input", stored_filename=os.path.basename(temp_input), file_path=temp_input, origin_filename=image.filename, mime_type=image.content_type, file_size=file_size, width=width, height=height)

        _, landmarks = face_detection.detect_face_landmarks_mediapipe(img)
        if landmarks is None:
            db_manager.create_image_quality_report(pca_image_id, has_face=False, raw_report={"reason": "NO_FACE_DETECTED"})
            return _api_error("NO_FACE_DETECTED", "哎呀，没有检测到人脸，请调整角度再试~", 200)

        blur_result = blur_detection.detect_blur_with_landmarks(img, landmarks, threshold=100, debug_prefix="")
        db_manager.create_image_quality_report(pca_image_id, has_face=True, blur_score=blur_result.get("score"), left_eye_score=blur_result.get("left_eye_score"), right_eye_score=blur_result.get("right_eye_score"), mouth_score=blur_result.get("mouth_score"), occlusion_flag=_detect_face_occlusion(blur_result), raw_report=blur_result)
        if blur_result.get("is_blurry"):
            return _api_error("BLURRY_IMAGE", "照片有点模糊，请重新上传一张清晰的~", 200)
        if _detect_face_occlusion(blur_result):
            return _api_error("FACE_OCCLUDED", "请摘下墨镜/口罩，露出完整面部哦", 200)

        try:
            analysis = _classify_season(img, landmarks)
        except ValueError as ve:
            if str(ve) == "TOO_DARK":
                return _api_error("TOO_DARK", "光线太暗啦，请找个明亮的地方再试", 200)
            raise

        db_manager.update_user_season(user_id=token_user_id, season_type=analysis["season_type"])
        db_manager.create_pca_analysis_record(user_id=token_user_id, image_id=pca_image_id, season_type=analysis["season_type"], tone=analysis.get("tone"), confidence=analysis.get("confidence"), recommended_palette=analysis.get("recommended_colors"), avoid_palette=analysis.get("avoid_colors"), feature_vector=[], model_version=analysis.get("model"))
        analysis["recommended_styles"] = _recommended_style_templates(analysis["season_type"])
        analysis["analysis_report"] = f"你更适合 {', '.join(analysis.get('recommended_colors', [])[:3])} 等色系，建议优先尝试自然感较强的底妆、眉部和唇部组合。"
        return _api_success(analysis, message="分析成功")
    except Exception as e:
        app.logger.exception(f"analyze_color_type failed: {e}")
        return _api_error("INTERNAL_ERROR", str(e), 500)
    finally:
        try:
            if os.path.exists(temp_input):
                os.remove(temp_input)
        except Exception:
            pass


@app.get("/api/recommend/products", tags=["recommend"], summary="推荐商品")
def recommend_products(season: str = Query(default="", examples=["Warm Autumn"]), category: str = Query(default="", examples=["lip"]), limit: int = Query(default=30), user_id: str = Query(default=""), user: Dict[str, Any] = Depends(get_current_user)):
    token_user_id = str(user.get("user_id") or "").strip()
    if user_id and user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    if not season:
        user_row = db_manager.get_user_by_id(token_user_id)
        if user_row and user_row.get("season_type"):
            season = user_row["season_type"]
    products = db_manager.get_products(season=season or None, category=category or None, limit=limit)
    enriched_products = []
    for product in products:
        row = dict(product)
        row["tags"] = _build_product_tags(row, season=season or None)
        row["recommend_reason"] = _build_product_reason(row, season=season or None)
        enriched_products.append(row)
    return _api_success({"season": season, "category": category or None, "products": enriched_products}, message="获取推荐商品成功")


@app.get("/api/recommend/bundles", tags=["recommend"], summary="套装推荐")
def bundle_recommend(season: str = Query(default="", examples=["Warm Autumn"]), current_product: str = Query(default="", examples=["lip_001"]), user_id: str = Query(default=""), user: Dict[str, Any] = Depends(get_current_user)):
    token_user_id = str(user.get("user_id") or "").strip()
    if user_id and user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    if not season:
        user_row = db_manager.get_user_by_id(token_user_id)
        if user_row and user_row.get("season_type"):
            season = user_row["season_type"]
    if not season:
        season = "Warm Autumn"
    selected = db_manager.get_bundle_recommend(season=season, current_product=current_product or None)
    products = [{"product_id": p["p_id"], "name": p["name"], "price": float(p.get("price") or 0), "category": p.get("category")} for p in selected]
    total_price = round(sum(p["price"] for p in products), 2)
    discount_price = round(total_price * 0.84, 2)
    return _api_success({"bundle_name": "全套型男方案", "products": products, "total_price": total_price, "discount_price": discount_price, "season": season}, message="获取套装推荐成功")


@app.post("/api/makeup/session", tags=["makeup"], summary="创建试妆会话", description="支持两种请求：1）multipart/form-data 上传 original_image 文件；2）application/json 传 original_image 图片 URL。")
async def create_makeup_session(
    request: Request,
    original_image: Optional[UploadFile] = File(default=None, description="multipart 模式下上传原始图片文件"),
    user_id_form: Optional[str] = Form(default=None, description="可选，若传入需与当前登录用户一致"),
    user: Dict[str, Any] = Depends(get_current_user),
):
    token_user_id = str(user.get("user_id") or "").strip()
    payload = {}
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
    requested_user_id = str(user_id_form or payload.get("user_id") or "").strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    if not token_user_id:
        return _api_error("INVALID_PARAMS", "缺少 user_id", 400)

    session_id = f"session_{uuid.uuid4().hex[:12]}"
    original_image_ref = ""
    original_image_id = None

    if original_image is not None:
        ext = os.path.splitext(original_image.filename or "")[1].lower() or ".jpg"
        save_path, relative_path, filename = _build_output_media_path(biz_type="session_original", user_id=token_user_id, filename_stem=f"session_original_{session_id}", ext=ext)
        content = await original_image.read()
        with open(save_path, "wb") as f:
            f.write(content)
        file_size = os.path.getsize(save_path) if os.path.exists(save_path) else 0
        original_image_id = db_manager.create_user_image(user_id=token_user_id, image_type="session_original", stored_filename=filename, file_path=os.path.join("database", "images", "outputs", relative_path), origin_filename=original_image.filename, mime_type=original_image.content_type, file_size=file_size, source_session_id=session_id)
        original_image_ref = _output_url(relative_path.replace(os.sep, "/"))
    else:
        original_image_ref = str(payload.get("original_image") or "").strip()

    if not original_image_ref:
        return _api_error("INVALID_PARAMS", "缺少 original_image", 400)

    db_manager.create_makeup_session(session_id=session_id, user_id=token_user_id, original_image=original_image_ref, current_image=original_image_ref, original_image_id=original_image_id)
    return _api_success({"session_id": session_id, "original_image": original_image_ref, "current_image": original_image_ref, "applied_products": [], "step": 0, "status": "active"}, message="创建试妆会话成功")


@app.post("/api/makeup/apply", tags=["makeup"], summary="应用试妆", description="新版试妆链路：session_id + product_id (+ category)。")
async def apply_makeup(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            data = await request.json()
        else:
            form = await request.form()
            data = dict(form)
    except Exception:
        data = {}

    session_id = str(data.get("session_id") or data.get("image_id") or "").strip()
    product_id = str(data.get("product_id") or "").strip()
    category = str(data.get("category") or "").strip()
    style = str(data.get("style") or "").strip()
    if not session_id:
        return _api_error("INVALID_PARAMS", "缺少 session_id", 400)

    lock = _get_session_lock(session_id)
    with lock:
        session = db_manager.get_makeup_session(session_id)
        if not session:
            return _api_error("SESSION_NOT_FOUND", "找不到试妆会话", 404)
        if session.get("user_id") != user.get("user_id"):
            return _api_error("FORBIDDEN", "无权限操作该会话", 403)

        if style and not product_id:
            base_path = _resolve_image_path(str(session.get("original_image") or session.get("current_image") or ""))
            if not base_path or not os.path.exists(base_path):
                return _api_error("IMAGE_NOT_FOUND", "找不到当前试妆图片", 404)
            cache_key = _build_style_cache_key(base_path=base_path, style=style, session_id=session_id)
            cached_image = _get_cached_style_render(cache_key)
            if cached_image:
                applied_products = _safe_json_loads(session.get("applied_products"), [])
                db_manager.update_makeup_session_state(session_id=session_id, current_image=cached_image, applied_products=applied_products, render_history=_safe_json_loads(session.get("render_history"), []), step=len(applied_products), status="active")
                return _api_success({"session_id": session_id, "current_image": cached_image, "applied_products": applied_products, "style": style, "render_backend": "gan", "cache_hit": True}, message="风格试妆成功")
            image_bgr = cv2.imread(base_path)
            if image_bgr is None:
                return _api_error("INVALID_IMAGE", "无法读取当前试妆图片", 400)
            output_path, output_relative_path, output_filename = _build_output_media_path(
                biz_type="session_render",
                user_id=str(user.get("user_id") or "").strip(),
                filename_stem=f"session_style_{session_id}_{style}",
                ext=".jpg",
            )
            try:
                started = time.perf_counter()
                render_backend = _render_style_image(image_bgr, style, output_path, session_id)
                elapsed = time.perf_counter() - started
                app.logger.info(f"style render done: session_id={session_id} style={style} backend={render_backend} elapsed={elapsed:.2f}s")
            except Exception as style_err:
                app.logger.exception(f"style render failed: {style_err}")
                return _api_error("STYLE_RENDER_FAILED", f"风格渲染失败: {style_err}", 500)
            new_current = _output_url(output_relative_path.replace(os.sep, "/"))
            _set_cached_style_render(cache_key, abs_path=output_path, image_url=new_current)
            render_history = [str(session.get("original_image") or "").strip(), new_current]
            applied_products = []
            db_manager.update_makeup_session_state(session_id=session_id, current_image=new_current, applied_products=applied_products, render_history=render_history, step=0, status="active")
            db_manager.create_user_image(user_id=str(user.get("user_id") or "").strip(), image_type="session_render", stored_filename=output_filename, file_path=os.path.join("database", "images", "temp", "outputs", output_relative_path), origin_filename=output_filename, mime_type="image/jpeg", file_size=os.path.getsize(output_path) if os.path.exists(output_path) else 0, source_session_id=session_id)
            return _api_success({"session_id": session_id, "current_image": new_current, "applied_products": applied_products, "style": style, "render_backend": render_backend}, message="风格试妆成功")

        if not product_id:
            return _api_error("INVALID_PARAMS", "缺少 product_id", 400)

        product = db_manager.get_product_by_id(product_id)
        if not product:
            return _api_error("PRODUCT_NOT_FOUND", "找不到产品 SKU", 404)

        product_category = category or str(product.get("category") or "").strip()
        canonical_items = _build_canonical_applied_items(session.get("applied_products"))
        changed = True
        matched = False
        for item in canonical_items:
            if item.get("category") != product_category:
                continue
            matched = True
            if item.get("product_id") == product_id:
                changed = False
            else:
                item["product_id"] = product_id
            break
        if not matched:
            canonical_items.append({"product_id": product_id, "category": product_category})

        if not changed:
            current_image = session.get("current_image") or session.get("original_image")
            applied_products = _safe_json_loads(session.get("applied_products"), [])
            return _api_success({"session_id": session_id, "current_image": current_image, "applied_products": applied_products, "idempotent": True}, message="试妆结果未变化")

        original_ref = str(session.get("original_image") or "").strip()
        try:
            new_current, render_history, applied_products = _rebuild_makeup_chain(session_id=session_id, original_ref=original_ref, selected_items=canonical_items)
        except Exception as e:
            app.logger.exception(f"session render failed, fallback to single-step render: {e}")
            base_ref = str(session.get("current_image") or session.get("original_image") or original_ref).strip()
            base_path = _resolve_image_path(base_ref)
            if not base_path or not os.path.exists(base_path):
                return _api_error("RENDER_FAILED", str(e), 500)
            image = cv2.imread(base_path)
            if image is None:
                return _api_error("RENDER_FAILED", str(e), 500)
            landmarks_result = face_detection.detect_face_landmarks_mediapipe(image)
            _, landmarks = landmarks_result if isinstance(landmarks_result, tuple) else (None, None)
            if landmarks is None:
                return _api_error("RENDER_FAILED", str(e), 500)
            fallback_abs_path, fallback_relative_path, fallback_filename = _build_output_media_path(
                biz_type="session_render",
                user_id=str(user.get("user_id") or "").strip(),
                filename_stem=f"session_{session_id}_fallback_{product_category}",
                ext=".jpg",
            )
            _apply_color_render(
                image,
                landmarks,
                category=product_category,
                color_hex=str(product.get("render_hex") or "#C68642"),
                output_path=fallback_abs_path,
                apply_area=str(product.get("apply_area") or product_category),
                opacity=product.get("opacity"),
                feather=product.get("feather"),
                render_mode=product.get("render_mode"),
                transparency_max=product.get("transparency_max"),
            )
            new_current = _output_url(fallback_relative_path.replace(os.sep, "/"))
            render_history = _safe_json_loads(session.get("render_history"), [])
            render_history.append(new_current)
            applied_products = canonical_items

        db_manager.update_makeup_session_state(session_id=session_id, current_image=new_current, applied_products=applied_products, render_history=render_history, step=len(applied_products), status="active")

        output_relative = new_current.split("/api/media/images/output/", 1)[-1].split("?", 1)[0].replace("/", os.sep)
        output_filename = os.path.basename(output_relative)
        output_rel_path = os.path.join("database", "images", "outputs", output_relative)
        output_abs_path = os.path.join(OUTPUTS_DIR, output_relative)
        output_image_id = db_manager.create_user_image(user_id=str(user.get("user_id") or "").strip(), image_type="session_render", stored_filename=output_filename, file_path=output_rel_path, origin_filename=output_filename, mime_type="image/jpeg", file_size=os.path.getsize(output_abs_path) if os.path.exists(output_abs_path) else 0, source_session_id=session_id)
        latest_session_render = db_manager.get_latest_session_image(session_id, image_type="session_render")
        input_image_id = latest_session_render.get("image_id") if latest_session_render else None
        db_manager.create_makeup_session_step(session_id=session_id, step_no=len(applied_products), category=product_category, sku_id=product_id, input_image_id=input_image_id, output_image_id=output_image_id, render_params={"product_id": product_id, "category": product_category, "current_image": new_current})

        return _api_success({"session_id": session_id, "current_image": new_current, "applied_products": applied_products, "idempotent": False}, message="试妆成功")


@app.post("/api/makeup/undo", tags=["makeup"], summary="撤销一步试妆")
def undo_makeup(
    payload: SessionRequest = Body(..., examples={"default": {"summary": "撤销一步", "value": {"session_id": "session_abcd1234ef56"}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    session_id = str(payload.session_id or "").strip()
    if not session_id:
        return _api_error("INVALID_PARAMS", "缺少 session_id", 400)
    lock = _get_session_lock(session_id)
    with lock:
        session = db_manager.get_makeup_session(session_id)
        if not session:
            return _api_error("SESSION_NOT_FOUND", "找不到试妆会话", 404)
        if session.get("user_id") != user.get("user_id"):
            return _api_error("FORBIDDEN", "无权限操作该会话", 403)
        applied_products = _build_canonical_applied_items(session.get("applied_products"))
        if applied_products:
            applied_products = applied_products[:-1]
        original_ref = str(session.get("original_image") or "").strip()
        try:
            current_image, render_history, applied_products = _rebuild_makeup_chain(session_id=session_id, original_ref=original_ref, selected_items=applied_products)
        except Exception as e:
            return _api_error("RENDER_FAILED", str(e), 500)
        step = len(applied_products)
        db_manager.update_makeup_session_state(session_id=session_id, current_image=current_image, applied_products=applied_products, render_history=render_history, step=step, status="active")
        return _api_success({"session_id": session_id, "current_image": current_image, "applied_products": applied_products}, message="撤销成功")


@app.post("/api/makeup/reset", tags=["makeup"], summary="重置整个试妆")
def reset_makeup(
    payload: SessionRequest = Body(..., examples={"default": {"summary": "重置会话", "value": {"session_id": "session_abcd1234ef56"}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    session_id = str(payload.session_id or "").strip()
    if not session_id:
        return _api_error("INVALID_PARAMS", "缺少 session_id", 400)
    lock = _get_session_lock(session_id)
    with lock:
        session = db_manager.get_makeup_session(session_id)
        if not session:
            return _api_error("SESSION_NOT_FOUND", "找不到试妆会话", 404)
        if session.get("user_id") != user.get("user_id"):
            return _api_error("FORBIDDEN", "无权限操作该会话", 403)
        original = session.get("original_image")
        render_history = [original]
        applied_products: List[Dict[str, Any]] = []
        db_manager.update_makeup_session_state(session_id=session_id, current_image=original, applied_products=applied_products, render_history=render_history, step=0, status="active")
        return _api_success({"session_id": session_id, "current_image": original, "applied_products": applied_products}, message="重置成功")


@app.post("/api/makeup/reset-part", tags=["makeup"], summary="局部重置试妆")
def reset_makeup_part(
    payload: ResetPartRequest = Body(..., examples={"default": {"summary": "重置唇部", "value": {"session_id": "session_abcd1234ef56", "category": "lip"}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    session_id = str(payload.session_id or "").strip()
    category = str(payload.category or "").strip()
    if not session_id or not category:
        return _api_error("INVALID_PARAMS", "缺少 session_id/category", 400)
    lock = _get_session_lock(session_id)
    with lock:
        session = db_manager.get_makeup_session(session_id)
        if not session:
            return _api_error("SESSION_NOT_FOUND", "找不到试妆会话", 404)
        if session.get("user_id") != user.get("user_id"):
            return _api_error("FORBIDDEN", "无权限操作该会话", 403)
        items = _build_canonical_applied_items(session.get("applied_products"))
        filtered = [item for item in items if str(item.get("category") or "").strip() != category]
        original_ref = str(session.get("original_image") or "").strip()
        try:
            new_current, render_history, applied_products = _rebuild_makeup_chain(session_id=session_id, original_ref=original_ref, selected_items=filtered)
        except Exception as e:
            return _api_error("RENDER_FAILED", str(e), 500)
        db_manager.update_makeup_session_state(session_id=session_id, current_image=new_current, applied_products=applied_products, render_history=render_history, step=len(applied_products), status="active")
        return _api_success({"session_id": session_id, "current_image": new_current, "applied_products": applied_products, "reset_category": category}, message="局部重置成功")


@app.get("/api/makeup/style-templates", tags=["makeup"], summary="获取妆容模板")
def style_templates(season: str = Query(default="", examples=["Warm Autumn"]), user: Dict[str, Any] = Depends(get_current_user)):
    if not season:
        user_row = db_manager.get_user_by_id(str(user.get("user_id") or "").strip()) or {}
        season = str(user_row.get("season_type") or "Warm Autumn")
    return _api_success({"season": season, "templates": _recommended_style_templates(season)}, message="获取风格模板成功")


@app.post("/api/makeup/schemes", tags=["makeup"], summary="保存妆容方案")
def save_makeup_scheme(
    payload: SaveSchemeRequest = Body(..., examples={"default": {"summary": "保存方案", "value": {"session_id": "session_abcd1234ef56", "scheme_name": "通勤妆方案"}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    token_user_id = str(user.get("user_id") or "").strip()
    requested_user_id = str(payload.user_id or "").strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    session_id = str(payload.session_id or "").strip()
    scheme_name = str(payload.scheme_name or "").strip()
    if not session_id or not scheme_name or not token_user_id:
        return _api_error("INVALID_PARAMS", "缺少 session_id/scheme_name/user_id", 400)
    lock = _get_session_lock(session_id)
    with lock:
        session = db_manager.get_makeup_session(session_id)
        if not session:
            return _api_error("SESSION_NOT_FOUND", "找不到试妆会话", 404)
        if session.get("user_id") != token_user_id:
            return _api_error("FORBIDDEN", "无权限操作该会话", 403)
        user_row = db_manager.get_user_by_id(token_user_id) or {}
        season_type = user_row.get("season_type")
        product_list = _safe_json_loads(session.get("applied_products"), [])
        cover_image = session.get("current_image")
        if cover_image and "/api/media/images/output/" in str(cover_image):
            relative_cover = str(cover_image).split("/api/media/images/output/", 1)[1].split("?", 1)[0]
            if os.path.exists(os.path.join(TEMP_OUTPUTS_DIR, relative_cover.replace("/", os.sep))):
                _, promoted_cover_relative, promoted_cover_filename = _promote_temp_output_file(
                    user_id=token_user_id,
                    biz_type="plan_cover",
                    relative_path=relative_cover,
                )
                cover_image = _output_url(promoted_cover_relative.replace(os.sep, "/"))
                row = db_manager.get_user_image_by_filename(token_user_id, os.path.basename(relative_cover))
                if row:
                    db_manager.update_user_image_storage(
                        row["image_id"],
                        stored_filename=promoted_cover_filename,
                        file_path=os.path.join("database", "images", "outputs", promoted_cover_relative),
                    )
        promoted_images = _promote_session_temp_images(user_id=token_user_id, session_id=session_id)
        scheme_id = f"scheme_{uuid.uuid4().hex[:12]}"
        db_manager.save_makeup_scheme(scheme_id=scheme_id, user_id=token_user_id, scheme_name=scheme_name, product_list=product_list, cover_image=cover_image, season_type=season_type)
        return _api_success({"scheme_id": scheme_id, "product_count": len(product_list), "promoted_images": promoted_images}, message="保存成功")


@app.get("/api/makeup/schemes", tags=["makeup"], summary="获取妆容方案列表")
def get_makeup_schemes(limit: int = Query(default=50), user_id: str = Query(default=""), user: Dict[str, Any] = Depends(get_current_user)):
    token_user_id = str(user.get("user_id") or "").strip()
    if user_id and user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    rows = db_manager.list_makeup_schemes(token_user_id, limit=limit)
    schemes = [{"scheme_id": r.get("scheme_id"), "user_id": r.get("user_id"), "scheme_name": r.get("scheme_name"), "product_list": _safe_json_loads(r.get("product_list"), []), "cover_image": r.get("cover_image"), "season_type": r.get("season_type"), "created_at": _format_cn_datetime(r.get("created_at"))} for r in rows]
    return _api_success({"user_id": token_user_id, "schemes": schemes}, message="获取方案列表成功")


@app.get("/api/makeup/schemes/{scheme_id}", tags=["makeup"], summary="获取单个妆容方案详情")
def get_makeup_scheme_detail(scheme_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    token_user_id = str(user.get("user_id") or "").strip()
    detail = db_manager.get_makeup_scheme_detail(scheme_id=scheme_id, user_id=token_user_id)
    if not detail:
        return _api_error("SCHEME_NOT_FOUND", "方案不存在或无权限访问", 404)
    payload = {
        "scheme_id": detail.get("scheme_id"),
        "user_id": detail.get("user_id"),
        "scheme_name": detail.get("scheme_name"),
        "product_list": _safe_json_loads(detail.get("product_list"), []),
        "cover_image": detail.get("cover_image"),
        "season_type": detail.get("season_type"),
        "created_at": _format_cn_datetime(detail.get("created_at")),
        "items": detail.get("items") or [],
    }
    return _api_success(_format_payload_times(payload), message="获取方案详情成功")


@app.delete("/api/makeup/schemes/{scheme_id}", tags=["makeup"], summary="删除妆容方案")
def delete_makeup_scheme(
    scheme_id: str = "",
    payload: Optional[DeleteSchemeRequest] = Body(default=None, examples={"default": {"summary": "删除方案", "value": {"scheme_id": "scheme_1234567890ab"}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    scheme_id = str(scheme_id or (payload.scheme_id if payload else "") or "").strip()
    if not scheme_id:
        return _api_error("INVALID_PARAMS", "缺少 scheme_id", 400)
    token_user_id = str(user.get("user_id") or "").strip()
    requested_user_id = str((payload.user_id if payload else "") or "").strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    deleted = db_manager.delete_makeup_scheme(scheme_id=scheme_id, user_id=token_user_id)
    if not deleted:
        return _api_error("SCHEME_NOT_FOUND", "方案不存在或无权限删除", 404)
    return _api_success({"scheme_id": scheme_id}, message="删除成功")


@app.get("/api/makeup/session/{session_id}", tags=["makeup"], summary="获取试妆会话")
def get_makeup_session(session_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    session = db_manager.get_makeup_session(session_id)
    if not session:
        return _api_error("SESSION_NOT_FOUND", "找不到试妆会话", 404)
    if session.get("user_id") != user.get("user_id"):
        return _api_error("FORBIDDEN", "无权限访问该会话", 403)
    return _api_success(_format_payload_times({"session_id": session.get("session_id"), "user_id": session.get("user_id"), "original_image": session.get("original_image"), "current_image": session.get("current_image"), "applied_products": _safe_json_loads(session.get("applied_products"), []), "step": int(session.get("step") or 0), "status": session.get("status") or "active", "updated_at": session.get("updated_at")}), message="获取试妆会话成功")


@app.post("/api/makeup/score", tags=["makeup"], summary="妆容评分")
def score_look(
    payload: SessionRequest = Body(..., examples={"default": {"summary": "妆容评分", "value": {"session_id": "session_abcd1234ef56"}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    session_id = str(payload.session_id or "").strip()
    if not session_id:
        return _api_error("INVALID_PARAMS", "缺少 session_id", 400)
    session = db_manager.get_makeup_session(session_id)
    if not session:
        return _api_error("SESSION_NOT_FOUND", "找不到试妆会话", 404)
    if session.get("user_id") != user.get("user_id"):
        return _api_error("FORBIDDEN", "无权限访问该会话", 403)
    try:
        score_payload = _score_makeup_look(session)
        return _api_success({"session_id": session_id, "current_image": session.get("current_image"), **score_payload}, message="妆容评分成功")
    except Exception as e:
        app.logger.exception(f"score_look failed: {e}")
        return _api_error("SCORE_FAILED", str(e), 500)


@app.get("/api/admin/products", tags=["admin"], summary="管理员获取商品列表")
def admin_products(limit: int = Query(default=200), category: str = Query(default="", examples=["lip"]), keyword: str = Query(default="", examples=["柔雾"]), _: Dict[str, Any] = Depends(get_admin_user)):
    products = db_manager.admin_list_products(limit=limit, category=category or None, keyword=keyword or None)
    return _api_success(_format_payload_times({"products": products, "count": len(products)}), message="获取商品列表成功")


@app.post("/api/admin/products", tags=["admin"], summary="管理员创建商品")
def admin_create_product(
    payload: AdminProductRequest = Body(..., examples={"default": {"summary": "创建商品", "value": {"p_id": "lip_001", "name": "柔雾唇釉 01", "category": "lip", "apply_area": "lips", "render_hex": "#B14A5A"}}}),
    _: Dict[str, Any] = Depends(get_admin_user),
):
    try:
        created = db_manager.admin_create_product(payload.model_dump(exclude_none=True))
    except Exception as e:
        return _api_error("INVALID_PARAMS", str(e), 400)
    return _api_success({"product": created}, message="创建成功")


@app.get("/api/admin/products/{product_id}", tags=["admin"], summary="管理员获取单个商品")
def admin_get_product(product_id: str, _: Dict[str, Any] = Depends(get_admin_user)):
    row = db_manager.get_product_by_id(product_id)
    if not row:
        return _api_error("PRODUCT_NOT_FOUND", "找不到产品 SKU", 404)
    return _api_success({"product": row}, message="获取商品成功")


@app.put("/api/admin/products/{product_id}", tags=["admin"], summary="管理员更新商品")
def admin_put_product(
    product_id: str,
    payload: AdminProductRequest = Body(..., examples={"default": {"summary": "更新商品", "value": {"name": "柔雾唇釉 01 升级版", "render_hex": "#A84558"}}}),
    _: Dict[str, Any] = Depends(get_admin_user),
):
    exists = db_manager.get_product_by_id(product_id)
    if not exists:
        return _api_error("PRODUCT_NOT_FOUND", "找不到产品 SKU", 404)
    try:
        updated = db_manager.admin_update_product(product_id, payload.model_dump(exclude_none=True))
    except Exception as e:
        return _api_error("INVALID_PARAMS", str(e), 400)
    return _api_success({"product": updated}, message="更新成功")


@app.delete("/api/admin/products/{product_id}", tags=["admin"], summary="管理员删除商品")
def admin_delete_product(product_id: str, _: Dict[str, Any] = Depends(get_admin_user)):
    exists = db_manager.get_product_by_id(product_id)
    if not exists:
        return _api_error("PRODUCT_NOT_FOUND", "找不到产品 SKU", 404)
    db_manager.admin_delete_product(product_id)
    return _api_success({"product_id": product_id}, message="删除成功")


@app.get("/api/cart", tags=["cart"], summary="获取购物车")
def cart_list(user_id: str = Query(default=""), user: Dict[str, Any] = Depends(get_current_user)):
    token_user_id = str(user.get("user_id") or "").strip()
    if user_id and user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    return _api_success(_cart_payload(token_user_id), message="获取购物车成功")


@app.post("/api/cart/items", tags=["cart"], summary="加入购物车")
def cart_add(
    payload: CartItemRequest = Body(..., examples={"default": {"summary": "加入购物车", "value": {"product_id": "lip_001", "quantity": 2}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    token_user_id = str(user.get("user_id") or "").strip()
    requested_user_id = str(payload.user_id or "").strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    product_id = str(payload.product_id or "").strip()
    quantity = int(payload.quantity or 1)
    if not product_id:
        return _api_error("INVALID_PARAMS", "缺少 product_id", 400)
    product = db_manager.get_product_by_id(product_id)
    if not product:
        return _api_error("PRODUCT_NOT_FOUND", "找不到产品 SKU", 404)
    db_manager.add_to_cart(token_user_id, product_id, quantity)
    return _api_success(_cart_payload(token_user_id), message="加入购物车成功")


@app.put("/api/cart/items", tags=["cart"], summary="更新购物车商品数量")
def cart_update(
    payload: CartItemRequest = Body(..., examples={"default": {"summary": "更新数量", "value": {"product_id": "lip_001", "quantity": 3}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    token_user_id = str(user.get("user_id") or "").strip()
    requested_user_id = str(payload.user_id or "").strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    product_id = str(payload.product_id or "").strip()
    quantity = int(payload.quantity or 0)
    if not product_id:
        return _api_error("INVALID_PARAMS", "缺少 product_id", 400)
    if quantity <= 0:
        db_manager.remove_cart_item(token_user_id, product_id)
    else:
        db_manager.update_cart_item(token_user_id, product_id, quantity)
    return _api_success(_cart_payload(token_user_id), message="更新购物车成功")


@app.delete("/api/cart/items/{product_id}", tags=["cart"], summary="移除购物车商品")
def cart_remove(
    product_id: str = "",
    payload: Optional[CartItemRequest] = Body(default=None, examples={"default": {"summary": "移除商品", "value": {"product_id": "lip_001", "quantity": 0}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    token_user_id = str(user.get("user_id") or "").strip()
    requested_user_id = str((payload.user_id if payload else "") or "").strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    product_id = str(product_id or (payload.product_id if payload else "") or "").strip()
    if not product_id:
        return _api_error("INVALID_PARAMS", "缺少 product_id", 400)
    db_manager.remove_cart_item(token_user_id, product_id)
    return _api_success(_cart_payload(token_user_id), message="移除购物车成功")


@app.post("/api/cart/clear", tags=["cart"], summary="清空购物车")
def cart_clear(user: Dict[str, Any] = Depends(get_current_user)):
    token_user_id = str(user.get("user_id") or "").strip()
    db_manager.clear_cart(token_user_id)
    return _api_success(_cart_payload(token_user_id), message="清空购物车成功")


@app.post("/api/cart/bundles", tags=["cart"], summary="批量加入套装到购物车")
def cart_add_bundle(
    payload: CartBundleRequest = Body(..., examples={"by_bundle": {"summary": "通过 bundle_id", "value": {"bundle_id": "bundle_autumn_001", "product_ids": []}}, "by_products": {"summary": "直接传 product_ids", "value": {"product_ids": ["lip_001", "brow_001", "base_001"]}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    token_user_id = str(user.get("user_id") or "").strip()
    requested_user_id = str(payload.user_id or "").strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    bundle_id = str(payload.bundle_id or "").strip()
    product_ids = payload.product_ids or []
    if bundle_id:
        bundle = db_manager.get_bundle_by_id(bundle_id)
        if not bundle:
            return _api_error("BUNDLE_NOT_FOUND", "找不到指定套装", 404)
        product_ids = [item["product_id"] for item in bundle.get("items", [])]
    if not isinstance(product_ids, list) or not product_ids:
        return _api_error("INVALID_PARAMS", "product_ids 必须是非空数组", 400)
    added = 0
    for pid in product_ids:
        product_id = str(pid or "").strip()
        if not product_id:
            continue
        product = db_manager.get_product_by_id(product_id)
        if not product:
            continue
        db_manager.add_to_cart(token_user_id, product_id, 1)
        added += 1
    payload_resp = _cart_payload(token_user_id)
    payload_resp["added"] = added
    if bundle_id:
        payload_resp["bundle_id"] = bundle_id
    return _api_success(payload_resp, message="批量加入购物车成功")


@app.post("/api/cart/items/bulk", tags=["cart"], summary="批量设置购物车")
def cart_set_bulk(
    payload: CartSetBulkRequest = Body(..., examples={"default": {"summary": "批量设置数量", "value": {"items": [{"product_id": "lip_001", "quantity": 2}, {"product_id": "brow_001", "quantity": 1}]}}}),
    user: Dict[str, Any] = Depends(get_current_user),
):
    token_user_id = str(user.get("user_id") or "").strip()
    requested_user_id = str(payload.user_id or "").strip()
    if requested_user_id and requested_user_id != token_user_id:
        return _api_error("FORBIDDEN", "user_id 与登录用户不一致", 403)
    items = payload.items or []
    if not isinstance(items, list):
        return _api_error("INVALID_PARAMS", "items 必须是数组", 400)
    for row in items:
        product_id = str(row.product_id or "").strip()
        if not product_id:
            continue
        quantity = int(row.quantity or 0)
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
    return _api_success(_cart_payload(token_user_id), message="批量设置购物车成功")


@app.post("/api/media/compress", tags=["tool"], summary="压缩图片", description="multipart/form-data：file 为待压缩图片。")
async def compress_image(file: UploadFile = File(..., description="待压缩图片文件"), _: Dict[str, Any] = Depends(get_current_user)):
    if not file.filename:
        return _api_error("INVALID_PARAMS", "No selected file", 400)
    temp_dir = tempfile.gettempdir()
    suffix = os.path.splitext(file.filename)[1] or ".jpg"
    input_path = os.path.join(temp_dir, f"input_{uuid.uuid4()}{suffix}")
    output_path = os.path.join(temp_dir, f"compressed_{uuid.uuid4()}.jpg")
    try:
        content = await file.read()
        with open(input_path, "wb") as f:
            f.write(content)
        success = compressor.compress(input_path, output_path, quality=50)
        if success and os.path.exists(output_path):
            return FileResponse(output_path, filename=f"compressed_{file.filename}")
        return _api_error("COMPRESS_FAILED", "Compression failed", 500)
    except Exception as e:
        return _api_error("COMPRESS_FAILED", str(e), 500)


@app.post("/api/media/process-upload", tags=["tool"], summary="上传并预处理图片", description="multipart/form-data：file 为待上传图片，返回矫正后的结果地址。")
async def process_upload(file: UploadFile = File(..., description="待上传图片文件"), user: Dict[str, Any] = Depends(get_current_user)):
    token_user_id = str(user.get("user_id") or "").strip()
    if not token_user_id:
        return _api_error("INVALID_PARAMS", "缺少 user_id", 400)
    if not file.filename:
        return _api_error("INVALID_PARAMS", "No selected file", 400)

    try:
        group_id = f"{token_user_id}_{uuid.uuid4().hex}"
        if file.filename == "实验1.jpg":
            group_id = f"demo_lh_{token_user_id}_{uuid.uuid4().hex}"
        elif file.filename == "实验2.jpg":
            group_id = f"demo_skb_{token_user_id}_{uuid.uuid4().hex}"

        input_path, relative_path, file_size = await _persist_upload_file(file, biz_type="makeup_input", user_id=token_user_id)
        input_filename = os.path.basename(input_path)
        rel_upload_path = os.path.join("database", "images", "uploads", relative_path)

        image = cv2.imread(input_path)
        if image is None:
            return _api_error("INVALID_IMAGE", "无法读取图片", 400)

        height, width = image.shape[:2]
        upload_image_id = db_manager.create_user_image(user_id=token_user_id, group_id=group_id, image_type="upload", stored_filename=input_filename, file_path=rel_upload_path, origin_filename=file.filename, mime_type=file.content_type, file_size=file_size, width=width, height=height)

        face_rect, landmarks = face_detection.detect_face_landmarks_mediapipe(image)
        if face_rect is None:
            db_manager.create_image_quality_report(upload_image_id, has_face=False, raw_report={"reason": "NO_FACE_DETECTED"})
            return _api_error("NO_FACE_DETECTED", "未检测到人脸，请重新上传正脸照片", 200)

        blur_result = blur_detection.detect_blur_with_landmarks(image, landmarks, threshold=100, debug_prefix=group_id)
        db_manager.create_image_quality_report(upload_image_id, has_face=True, blur_score=blur_result.get("score"), left_eye_score=blur_result.get("left_eye_score"), right_eye_score=blur_result.get("right_eye_score"), mouth_score=blur_result.get("mouth_score"), occlusion_flag=_detect_face_occlusion(blur_result), raw_report=blur_result)
        if "debug_paths" in blur_result:
            for debug_path in blur_result["debug_paths"]:
                debug_filename = os.path.basename(debug_path)
                try:
                    debug_size = os.path.getsize(debug_path) if os.path.exists(debug_path) else 0
                    db_manager.create_user_image(user_id=token_user_id, group_id=group_id, image_type="debug", stored_filename=debug_filename, file_path=debug_path, origin_filename=debug_filename, mime_type="image/jpeg", file_size=debug_size, width=None, height=None)
                except Exception:
                    pass

        if blur_result.get("is_blurry"):
            return _api_error("BLURRY_IMAGE", "照片过于模糊，请重新上传清晰照片", 200, data={"score": blur_result.get("score"), "details": blur_result.get("details")})

        output_abs_path, output_relative_path, output_filename = _build_output_media_path(biz_type="corrected", user_id=token_user_id, filename_stem=f"corrected_{group_id}", ext=".jpg")
        correction_result = face_correction.face_correction_ultimate(input_path, output_dir=os.path.dirname(output_abs_path), output_filename=output_filename)
        if correction_result:
            actual_filename = correction_result.get("filename", output_filename)
            actual_relative_path = os.path.join(os.path.dirname(output_relative_path), actual_filename) if os.path.dirname(output_relative_path) else actual_filename
            rel_output_path = os.path.join("database", "images", "outputs", actual_relative_path)
            corrected_path = os.path.join(OUTPUTS_DIR, actual_relative_path)
            corrected_size = os.path.getsize(corrected_path) if os.path.exists(corrected_path) else 0
            db_manager.create_user_image(user_id=token_user_id, group_id=group_id, image_type="corrected", stored_filename=actual_filename, file_path=rel_output_path, origin_filename=file.filename, mime_type="image/jpeg", file_size=corrected_size, width=None, height=None)

        result_url = _output_url((actual_relative_path if correction_result else output_relative_path).replace(os.sep, "/"))
        return _api_success({"result_url": result_url, "group_id": group_id}, message="处理成功")
    except Exception as e:
        app.logger.exception(f"process_upload failed: {e}")
        return _api_error("PROCESS_UPLOAD_FAILED", str(e), 500)


def _get_current_user_allow_query(request: Request) -> Dict[str, Any]:
    auth = request.headers.get("Authorization", "")
    token = None
    if auth.startswith("Bearer "):
        token = auth.replace("Bearer ", "", 1).strip()
    if not token:
        token = (request.query_params.get("token") or "").strip()
    if not token:
        raise api_error(401, "UNAUTHORIZED", "缺少 Authorization Bearer token")
    user = db_manager.get_user_by_token(token)
    if not user:
        raise api_error(401, "UNAUTHORIZED", "登录态无效或已过期")
    return user


@app.get("/api/media/images/output/{filename:path}", tags=["images"], summary="访问输出图片")
def serve_output_image(filename: str, request: Request):
    user = _get_current_user_allow_query(request)
    token_user_id = str(user.get("user_id") or "").strip()
    if not _user_can_access_image(token_user_id, filename):
        return _api_error("FORBIDDEN", "无权限访问该图片", 403)
    path = _resolve_image_path(f"/api/media/images/output/{filename}")
    if not path or not os.path.exists(path):
        return _api_error("IMAGE_NOT_FOUND", "文件不存在", 404)
    return FileResponse(path)


@app.get("/api/media/images/upload/{filename:path}", tags=["images"], summary="访问上传图片")
def serve_upload_image(filename: str, request: Request):
    user = _get_current_user_allow_query(request)
    token_user_id = str(user.get("user_id") or "").strip()
    if not _user_can_access_image(token_user_id, filename):
        return _api_error("FORBIDDEN", "无权限访问该图片", 403)
    path = _resolve_image_path(f"/api/media/images/upload/{filename}")
    if not path or not os.path.exists(path):
        return _api_error("IMAGE_NOT_FOUND", "文件不存在", 404)
    return FileResponse(path)


@app.get("/api/media/images/avatar/{filename:path}", tags=["images"], summary="访问头像图片")
def serve_avatar_image(filename: str, request: Request):
    user = _get_current_user_allow_query(request)
    token_user_id = str(user.get("user_id") or "").strip()
    if not _user_can_access_image(token_user_id, filename):
        return _api_error("FORBIDDEN", "无权限访问该图片", 403)
    path = os.path.join(AVATARS_DIR, filename)
    if not os.path.exists(path):
        return _api_error("IMAGE_NOT_FOUND", "文件不存在", 404)
    return FileResponse(path)


_OPENAPI_PROTECTED = {
    "/api/auth/logout": ["post"],
    "/api/auth/reset-password": ["post"],
    "/api/user/info": ["get"],
    "/api/user/profile": ["put"],
    "/api/user/nickname": ["put"],
    "/api/user/avatar/upload": ["post"],
    "/api/user/history": ["get"],
    "/api/user/images": ["get"],
    "/api/user/images/latest": ["get"],
    "/api/user/preferences": ["get", "put"],
    "/api/user/membership": ["get"],
    "/api/pca/personalized_recommendations": ["get"],
    "/api/recommend/pairs": ["get"],
    "/api/pca/analyze": ["post"],
    "/api/recommend/products": ["get"],
    "/api/recommend/bundles": ["get"],
    "/api/makeup/session": ["post"],
    "/api/makeup/apply": ["post"],
    "/api/makeup/undo": ["post"],
    "/api/makeup/reset": ["post"],
    "/api/makeup/reset-part": ["post"],
    "/api/makeup/style-templates": ["get"],
    "/api/makeup/schemes": ["post", "get"],
    "/api/makeup/schemes/{scheme_id}": ["get", "delete"],
    "/api/makeup/session/{session_id}": ["get"],
    "/api/makeup/score": ["post"],
    "/api/admin/products": ["get", "post"],
    "/api/admin/products/{product_id}": ["get", "put", "delete"],
    "/api/cart": ["get"],
    "/api/cart/items": ["post", "put"],
    "/api/cart/items/{product_id}": ["delete"],
    "/api/cart/clear": ["post"],
    "/api/cart/bundles": ["post"],
    "/api/cart/items/bulk": ["post"],
    "/api/media/compress": ["post"],
    "/api/media/process-upload": ["post"],
    "/api/media/images/output/{filename}": ["get"],
    "/api/media/images/upload/{filename}": ["get"],
    "/api/media/images/avatar/{filename}": ["get"],
}


def _json_resp(description: str, example: Any) -> Dict[str, Any]:
    return {"description": description, "content": {"application/json": {"example": example}}}


def _json_resp_examples(description: str, examples: Dict[str, Any]) -> Dict[str, Any]:
    return {"description": description, "content": {"application/json": {"examples": examples}}}


def _binary_resp(description: str, media_type: str = "image/jpeg") -> Dict[str, Any]:
    return {"description": description, "content": {media_type: {"example": "<binary file>"}}}

_OPENAPI_REQUEST_PATCHES: Dict[Tuple[str, str], Dict[str, Any]] = {
    ("/api/user/info", "get"): {
        "description": "获取当前登录用户的基础信息、最近历史摘要。适用于个人中心头部资料回显。",
        "responses": {
            "200": _json_resp("获取用户信息成功", {"code": 0, "message": "获取用户信息成功", "data": {"user_id": "user_xxx", "phone": "13800138000", "nickname": "智颜体验官", "avatar": "http://127.0.0.1:5001/api/media/images/avatar/defaults/avatar-default.png?token={{token}}", "season_type": "Warm Autumn"}})
        },
    },
    ("/api/user/images", "get"): {
        "description": "获取个人中心照片库。返回 upload/corrected 类型图片，适合前端照片库回显。",
        "parameters": [
            {"name": "limit", "in": "query", "required": False, "description": "返回条数，默认 50，最大 200", "schema": {"type": "integer", "default": 50, "example": 20}}
        ],
        "responses": {
            "200": _json_resp("获取图片列表成功", {"code": 0, "message": "获取图片列表成功", "data": {"items": [{"image_id": "img_xxx", "image_type": "corrected", "file_path": "database/images/outputs/corrected/user_xxx/2026/03/18/demo.jpg", "url": "http://127.0.0.1:5001/api/media/images/output/corrected/user_xxx/2026/03/18/demo.jpg?token={{token}}"}], "count": 1}})
        },
    },
    ("/api/user/images/{image_id}", "delete"): {
        "description": "删除当前用户自己的图片记录及其关联分析/步骤记录。需要鉴权。",
        "parameters": [
            {"name": "image_id", "in": "path", "required": True, "description": "图片主键", "schema": {"type": "string", "example": "img_92ff7f4de8024662"}}
        ],
        "responses": {
            "200": _json_resp("删除图片成功", {"code": 0, "message": "删除图片成功", "data": {"image_id": "img_92ff7f4de8024662"}}),
            "404": _json_resp("找不到图片", {"code": 404, "message": "找不到图片", "data": None, "error_code": "IMAGE_NOT_FOUND"})
        },
    },
    ("/api/makeup/schemes", "get"): {
        "description": "获取当前用户保存的个人形象方案库列表。",
        "parameters": [
            {"name": "limit", "in": "query", "required": False, "description": "返回条数，默认 50", "schema": {"type": "integer", "default": 50, "example": 20}}
        ],
        "responses": {
            "200": _json_resp("获取方案列表成功", {"code": 0, "message": "获取方案列表成功", "data": {"schemes": [{"scheme_id": "scheme_1234567890ab", "scheme_name": "通勤妆方案", "cover_image": "http://127.0.0.1:5001/api/media/images/output/plan_cover/user_xxx/2026/03/18/demo.jpg?token={{token}}"}]}})
        },
    },
    ("/api/makeup/schemes/{scheme_id}", "delete"): {
        "description": "删除当前用户自己的方案。若无权限或不存在则返回错误。",
        "parameters": [
            {"name": "scheme_id", "in": "path", "required": True, "description": "方案主键", "schema": {"type": "string", "example": "scheme_1234567890ab"}}
        ],
        "responses": {
            "200": _json_resp("删除成功", {"code": 0, "message": "删除成功", "data": {"scheme_id": "scheme_1234567890ab"}}),
            "404": _json_resp("方案不存在", {"code": 404, "message": "方案不存在", "data": None, "error_code": "SCHEME_NOT_FOUND"})
        },
    },
    ("/api/cart", "get"): {
        "description": "获取当前用户购物车。个人中心与商城均可使用。",
        "responses": {
            "200": _json_resp("获取购物车成功", {"code": 0, "message": "获取购物车成功", "data": {"user_id": "user_xxx", "items": [{"product_id": "brow_001_brown", "name": "深棕立体眉笔", "quantity": 2, "price": 89.0}], "summary": {"item_count": 1, "total_quantity": 2, "total_amount": 178.0}}})
        },
    },
    ("/api/cart/items/{product_id}", "delete"): {
        "description": "从当前用户购物车移除指定商品。",
        "parameters": [
            {"name": "product_id", "in": "path", "required": True, "description": "SKU / product_id", "schema": {"type": "string", "example": "brow_001_brown"}}
        ],
        "responses": {
            "200": _json_resp("移除购物车商品成功", {"code": 0, "message": "移除购物车商品成功", "data": {"product_id": "brow_001_brown"}})
        },
    },
    ("/api/pca/personalized_recommendations", "get"): {
        "description": "获取个性化推荐商品，可作为个人中心“种草单品”数据源。",
        "parameters": [
            {"name": "limit", "in": "query", "required": False, "description": "返回推荐条数，默认 10", "schema": {"type": "integer", "default": 10, "example": 20}}
        ],
        "responses": {
            "200": _json_resp("获取个性化推荐成功", {"code": 0, "message": "获取个性化推荐成功", "data": {"products": [{"product_id": "brow_001_brown", "name": "深棕立体眉笔", "category": "brow", "price": 89.0}]}})
        },
    },
    ("/api/recommend/products", "get"): {
        "description": "根据季型、分类和当前登录用户信息返回推荐商品列表。适合商城列表页、试妆页右侧候选商品区使用。",
        "parameters": [
            {"name": "season", "in": "query", "required": False, "description": "季型，例如 Warm Autumn；为空时优先回退当前用户 season_type", "schema": {"type": "string", "example": "Warm Autumn"}},
            {"name": "category", "in": "query", "required": False, "description": "商品分类：base/brow/eye/contour/lip", "schema": {"type": "string", "example": "lip"}},
            {"name": "limit", "in": "query", "required": False, "description": "返回条数，默认 30", "schema": {"type": "integer", "default": 30, "example": 20}},
            {"name": "user_id", "in": "query", "required": False, "description": "若传入，必须与当前登录用户一致", "schema": {"type": "string", "example": "user_xxx"}}
        ],
        "responses": {
            "200": _json_resp("获取推荐商品成功", {"code": 0, "message": "获取推荐商品成功", "data": {"season": "Warm Autumn", "category": "lip", "products": [{"product_id": "lip_001_amber", "name": "琥珀暖棕唇膏", "category": "lip", "render_hex": "#A35A3A", "price": 159.0}]}})
        },
    },
    ("/api/recommend/bundles", "get"): {
        "description": "根据季型和当前商品返回整套推荐。适用于“智能推荐套装 / 一键购齐 / 一键渲染”场景。",
        "responses": {
            "200": _json_resp("获取套装推荐成功", {"code": 0, "message": "获取套装推荐成功", "data": {"bundle_name": "全套型男方案", "products": [{"product_id": "lip_001_amber", "name": "琥珀暖棕唇膏", "price": 159.0, "category": "lip"}], "total_price": 159.0, "discount_price": 133.56, "season": "Warm Autumn"}})
        },
    },
    ("/api/recommend/pairs", "get"): {
        "description": "获取某个源商品的搭配商品推荐，用于商品详情页、方案联动推荐。",
        "responses": {
            "200": _json_resp("获取搭配推荐成功", {"code": 0, "message": "获取搭配推荐成功", "data": {"source_sku_id": "lip_001_amber", "items": [{"target_sku_id": "brow_001_brown", "reason": "暖调搭配更协调", "score": 0.92}]}})
        },
    },
    ("/api/makeup/session", "post"): {
        "description": "创建试妆会话。支持上传原图文件或直接传原图 URL，返回 `session_id` 与当前试妆状态。",
        "responses": {
            "200": _json_resp("创建试妆会话成功", {"code": 0, "message": "创建试妆会话成功", "data": {"session_id": "session_abcd1234ef56", "original_image": "http://127.0.0.1:5001/api/media/images/output/corrected/user_xxx/2026/03/18/demo.jpg?token={{token}}", "current_image": "http://127.0.0.1:5001/api/media/images/output/corrected/user_xxx/2026/03/18/demo.jpg?token={{token}}", "applied_products": [], "step": 0, "status": "active"}})
        },
    },
    ("/api/makeup/apply", "post"): {
        "description": "应用试妆。支持两种模式：1）`session_id + style` 的整脸风格试妆；2）`session_id + product_id + category` 的局部试妆。局部试妆同一分类仅保留一个 SKU，后选覆盖前选。",
        "responses": {
            "200": _json_resp_examples("试妆成功", {
                "style": {"summary": "风格试妆成功", "value": {"code": 0, "message": "风格试妆成功", "data": {"session_id": "session_abcd1234ef56", "current_image": "http://127.0.0.1:5001/api/media/images/output/session_render/user_xxx/2026/03/18/demo.jpg?token={{token}}", "applied_products": [], "style": "clean", "render_backend": "gan"}}},
                "partial": {"summary": "局部试妆成功", "value": {"code": 0, "message": "试妆成功", "data": {"session_id": "session_abcd1234ef56", "current_image": "http://127.0.0.1:5001/api/media/images/output/session_render/user_xxx/2026/03/18/demo.jpg?token={{token}}", "applied_products": [{"product_id": "lip_002_rose", "category": "lip"}], "idempotent": False}}}
            })
        },
    },
    ("/api/makeup/undo", "post"): {
        "description": "撤销上一步试妆。后端会基于原图和剩余商品重新重建渲染链。",
        "responses": {
            "200": _json_resp("撤销成功", {"code": 0, "message": "撤销成功", "data": {"session_id": "session_abcd1234ef56", "current_image": "http://127.0.0.1:5001/api/media/images/output/corrected/user_xxx/2026/03/18/demo.jpg?token={{token}}", "applied_products": []}})
        },
    },
    ("/api/makeup/reset", "post"): {
        "description": "重置整个试妆，清空所有已上脸商品，恢复到会话原始图。",
        "responses": {
            "200": _json_resp("重置成功", {"code": 0, "message": "重置成功", "data": {"session_id": "session_abcd1234ef56", "current_image": "http://127.0.0.1:5001/api/media/images/output/corrected/user_xxx/2026/03/18/demo.jpg?token={{token}}", "applied_products": []}})
        },
    },
    ("/api/makeup/reset-part", "post"): {
        "description": "只卸除某一个局部分类，例如 `lip` 或 `brow`，其余分类保持不变。",
        "responses": {
            "200": _json_resp("局部重置成功", {"code": 0, "message": "局部重置成功", "data": {"session_id": "session_abcd1234ef56", "current_image": "http://127.0.0.1:5001/api/media/images/output/session_render/user_xxx/2026/03/18/demo.jpg?token={{token}}", "applied_products": [{"product_id": "brow_001_brown", "category": "brow"}], "reset_category": "lip"}})
        },
    },
    ("/api/makeup/style-templates", "get"): {
        "description": "获取当前季型可用的风格模板列表，用于试妆页快捷风格入口。",
    },
    ("/api/makeup/schemes", "post"): {
        "description": "把当前试妆会话保存成个人形象方案，并在需要时把临时图片迁移到正式目录。",
        "responses": {
            "200": _json_resp("保存成功", {"code": 0, "message": "保存成功", "data": {"scheme_id": "scheme_1234567890ab", "product_count": 3, "promoted_images": []}})
        },
    },
    ("/api/makeup/schemes/{scheme_id}", "get"): {
        "description": "获取单个方案的详情，包括封面图和结构化商品列表。",
    },
    ("/api/makeup/session/{session_id}", "get"): {
        "description": "获取试妆会话详情，用于前端恢复试妆状态或重新进入结果页。",
    },
    ("/api/makeup/score", "post"): {
        "description": "对当前试妆结果进行评分，返回完整度、清晰度、协调度等维度。",
    },
    ("/api/admin/products", "get"): {
        "description": "管理员获取商品列表，支持分类与关键字筛选。",
    },
    ("/api/admin/products/{product_id}", "get"): {
        "description": "管理员查看单个商品详情。",
    },
    ("/api/admin/products/{product_id}", "put"): {
        "description": "管理员更新单个商品。可更新渲染色值、遮罩参数、库存等字段。",
    },
    ("/api/admin/products/{product_id}", "delete"): {
        "description": "管理员删除单个商品。若商品仍被方案、购物车、推荐关系引用，需结合业务谨慎处理。",
    },
    ("/api/media/compress", "post"): {
        "description": "上传图片并执行压缩，适合前端上传前测试压缩效果。",
    },
    ("/api/media/process-upload", "post"): {
        "description": "上传并预处理图片，完成压缩、脸部检查、姿态校正，返回矫正图地址与分析结果。",
        "responses": {
            "200": _json_resp("图片处理成功", {"code": 0, "message": "图片处理成功", "data": {"group_id": "user_xxx_xxx", "input_image": "http://127.0.0.1:5001/api/media/images/upload/demo.jpg?token={{token}}", "corrected_image": "http://127.0.0.1:5001/api/media/images/output/corrected/user_xxx/2026/03/18/demo.jpg?token={{token}}", "has_face": True}})
        },
    },
}


def _json_resp(description: str, example: Any) -> Dict[str, Any]:
    return {"description": description, "content": {"application/json": {"example": example}}}

def _json_resp_examples(description: str, examples: Dict[str, Any]) -> Dict[str, Any]:
    return {"description": description, "content": {"application/json": {"examples": examples}}}

def _binary_resp(description: str, media_type: str = "image/jpeg") -> Dict[str, Any]:
    return {"description": description, "content": {media_type: {"example": "<binary file>"}}}

_OPENAPI_RESPONSE_EXAMPLES: Dict[Tuple[str, str, str], Dict[str, Any]] = {
    ("/health", "get", "200"): _json_resp("服务健康检查成功", {"code": 0, "message": "health ok", "data": {"status": "ok"}}),
}

def _ensure_auth_doc(operation: Dict[str, Any], allow_query_token: bool = False) -> None:
    operation.setdefault("security", [{"BearerAuth": []}])
    parameters = operation.setdefault("parameters", [])
    if not any(p.get("name") == "Authorization" and p.get("in") == "header" for p in parameters):
        parameters.append({
            "name": "Authorization",
            "in": "header",
            "required": False if allow_query_token else True,
            "description": "Bearer Token，例如：Bearer {{token}}",
            "schema": {"type": "string", "example": "Bearer {{token}}"},
        })
    if allow_query_token and not any(p.get("name") == "token" and p.get("in") == "query" for p in parameters):
        parameters.append({
            "name": "token",
            "in": "query",
            "required": False,
            "description": "图片访问兼容的 query token，用于 <img> 或临时直链访问。与 Authorization 二选一。",
            "schema": {"type": "string", "example": "{{token}}"},
        })

def _merge_dict(target: Dict[str, Any], patch: Dict[str, Any]) -> None:
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            _merge_dict(target[k], v)
        else:
            target[k] = v

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    components = schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "Token",
        "description": "在 Apipost 中统一设置 Authorization: Bearer {{token}}。",
    }

    schema["tags"] = [
        {"name": "auth", "description": "认证与用户身份接口"},
        {"name": "user", "description": "用户资料、偏好、会员信息"},
        {"name": "analysis", "description": "图片分析与季型分析"},
        {"name": "recommend", "description": "商品/套装/个性化推荐"},
        {"name": "makeup", "description": "试妆会话、应用、撤销、评分、方案保存"},
        {"name": "cart", "description": "购物车相关接口"},
        {"name": "admin", "description": "后台商品管理接口"},
        {"name": "media", "description": "图片访问与文件处理接口"},
        {"name": "images", "description": "图片文件流接口"},
    ]

    paths = schema.setdefault("paths", {})

    for (path, method), patch in _OPENAPI_REQUEST_PATCHES.items():
        operation = paths.get(path, {}).get(method)
        if operation:
            _merge_dict(operation, patch)

    for path, methods in _OPENAPI_PROTECTED.items():
        path_item = paths.get(path) or {}
        for method in methods:
            operation = path_item.get(method)
            if not operation:
                continue
            _ensure_auth_doc(operation, allow_query_token=path.startswith("/api/media/images/"))
            responses = operation.setdefault("responses", {})
            responses.setdefault("401", {
                "description": "未登录或 token 无效",
                "content": {"application/json": {"example": {"code": 401, "message": "缺少 Authorization Bearer token", "data": None, "error_code": "UNAUTHORIZED"}}},
            })
            responses.setdefault("403", {
                "description": "无权限访问",
                "content": {"application/json": {"example": {"code": 403, "message": "无权限访问", "data": None, "error_code": "FORBIDDEN"}}},
            })

    for (path, method, status), payload in _OPENAPI_RESPONSE_EXAMPLES.items():
        operation = paths.get(path, {}).get(method)
        if not operation:
            continue
        responses = operation.setdefault("responses", {})
        responses[status] = payload

    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=5001, reload=False)
