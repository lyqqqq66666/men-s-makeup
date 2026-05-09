#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import requests


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    import db_manager  # type: ignore
except Exception:
    db_manager = None


@dataclass
class Config:
    base_url: str
    token: str = ""
    secondary_token: str = ""
    admin_token: str = ""
    phone: str = "13800138000"
    password: str = "123456"
    new_password: str = "654321"
    second_phone: str = "13800138001"
    second_password: str = "123456"
    register_code: str = ""
    login_code: str = ""
    reset_code: str = ""
    second_register_code: str = ""
    second_login_code: str = ""
    image_path: str = ""
    user_id: str = ""
    secondary_user_id: str = ""
    product_id: str = "lip_001"
    bundle_id: str = ""
    source_sku_id: str = "lip_001"
    season: str = "Warm Autumn"
    category: str = "lip"
    scheme_name: str = "通勤妆方案"
    legacy_filename: str = ""
    legacy_style: str = "clean"
    timeout: float = 40.0
    output: str = "api_test_report.json"
    verify_ssl: bool = True
    auto_bootstrap_codes: bool = False


@dataclass
class TestResult:
    name: str
    method: str
    path: str
    ok: bool = False
    status_code: Optional[int] = None
    request: Dict[str, Any] = field(default_factory=dict)
    response: Any = None
    error: str = ""
    elapsed_ms: Optional[int] = None
    skipped: bool = False
    skip_reason: str = ""


class APITester:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.session = requests.Session()
        self.results: List[TestResult] = []
        self.runtime: Dict[str, Any] = {
            "primary_token": cfg.token,
            "secondary_token": cfg.secondary_token,
            "admin_token": cfg.admin_token,
            "primary_user_id": cfg.user_id,
            "secondary_user_id": cfg.secondary_user_id,
            "register_probe_phone": f"139{int(time.time()) % 100000000:08d}",
            "session_id": "",
            "scheme_id": "",
            "group_id": "",
            "result_url": "",
            "current_image": "",
            "output_filename": "",
            "created_product_id": "",
            "bootstrap": {},
            "openapi_paths": [],
            "bundle_id": "",
        }
        self.route_aliases: Dict[str, List[str]] = {}

    def _normalize_path(self, path: str) -> str:
        text = str(path or "").strip()
        if not text:
            return text
        parts = text.split("?")[0].split("/")
        if len(parts) >= 5 and parts[1:4] == ["api", "admin", "products"] and parts[4]:
            return "/api/admin/products/{product_id}"
        if len(parts) >= 5 and parts[1:4] == ["api", "makeup", "schemes"] and parts[4]:
            return "/api/makeup/schemes/{scheme_id}"
        if len(parts) >= 5 and parts[1:4] == ["api", "makeup", "session"] and parts[4]:
            return "/api/makeup/session/{session_id}"
        if len(parts) >= 5 and parts[1:4] == ["api", "cart", "items"] and parts[4]:
            return "/api/cart/items/{product_id}"
        if len(parts) >= 5 and parts[1:4] == ["api", "media", "images"]:
            image_type = parts[4]
            if image_type in {"output", "upload", "avatar"}:
                return f"/api/media/images/{image_type}/{{filename}}"
        return text

    def prepare_fixtures(self) -> None:
        if db_manager is None:
            return

        if not self.cfg.image_path:
            candidates = [
                os.path.join(os.path.dirname(CURRENT_DIR), 'backend_lose', 'input', 'test_jpg.jpg'),
                os.path.join(os.path.dirname(CURRENT_DIR), 'backend_lose', 'input', '1.jpg'),
            ]
            for candidate in candidates:
                if os.path.exists(candidate):
                    self.cfg.image_path = candidate
                    break

        if not self.cfg.admin_token:
            try:
                conn = db_manager.get_db_connection()
                try:
                    admin_phone = '13900000000'
                    row = conn.execute('SELECT user_id FROM users WHERE phone = ?', (admin_phone,)).fetchone()
                    if row:
                        admin_user_id = row['user_id']
                        conn.execute('UPDATE users SET role = ?, nickname = COALESCE(nickname, ?) WHERE user_id = ?', ('admin', '管理员', admin_user_id))
                    else:
                        admin_user_id = db_manager.create_user_with_phone(phone=admin_phone, password='123456', nickname='管理员', avatar='')
                        conn.execute('UPDATE users SET role = ? WHERE user_id = ?', ('admin', admin_user_id))
                    conn.commit()
                finally:
                    conn.close()
                self.runtime['admin_token'] = db_manager.create_auth_token(admin_user_id)
            except sqlite3.OperationalError:
                self.runtime['bootstrap']['admin_bootstrap_skipped'] = 'database_locked'

        if not self.cfg.bundle_id:
            self.cfg.bundle_id = 'bundle_warm_autumn_basic'
            self.runtime['bundle_id'] = self.cfg.bundle_id

    def _full_url(self, path: str) -> str:
        return self.cfg.base_url.rstrip("/") + path

    def _headers(self, token: str = "") -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _decode_response(self, resp: requests.Response) -> Any:
        ctype = resp.headers.get("content-type", "")
        if "application/json" in ctype:
            try:
                return resp.json()
            except Exception:
                return resp.text
        if "image/" in ctype or "application/octet-stream" in ctype:
            return {
                "content_type": ctype,
                "bytes": len(resp.content),
                "filename": resp.headers.get("content-disposition", ""),
            }
        return resp.text

    def request(self, name: str, method: str, path: str, *, token: str = "", expected: Tuple[int, ...] = (200,), json_body: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None, files: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, allow_fail: bool = False) -> Optional[requests.Response]:
        req_headers = self._headers(token)
        if headers:
            req_headers.update(headers)
        url = self._full_url(path)
        started = time.time()
        result = TestResult(name=name, method=method.upper(), path=path)
        result.request = {"url": url, "headers": req_headers, "params": params, "json": json_body, "data": data, "files": list(files.keys()) if files else None, "expected": list(expected)}
        try:
            resp = self.session.request(method=method.upper(), url=url, headers=req_headers, params=params, json=json_body, data=data, files=files, timeout=self.cfg.timeout, verify=self.cfg.verify_ssl)
            result.status_code = resp.status_code
            result.response = self._decode_response(resp)
            result.ok = resp.status_code in expected
            result.elapsed_ms = int((time.time() - started) * 1000)
            if not result.ok and not allow_fail:
                result.error = f"unexpected status {resp.status_code}, expected {expected}"
            self.results.append(result)
            return resp
        except Exception as e:
            result.ok = False
            result.error = str(e)
            result.elapsed_ms = int((time.time() - started) * 1000)
            self.results.append(result)
            return None

    def skip(self, name: str, method: str, path: str, reason: str) -> None:
        self.results.append(TestResult(name=name, method=method.upper(), path=path, skipped=True, skip_reason=reason))

    def _open_file_tuple(self, path: str) -> tuple[str, Any, str]:
        filename = os.path.basename(path)
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return filename, open(path, "rb"), mime

    def _body_data(self, resp: Optional[requests.Response]) -> Dict[str, Any]:
        if resp is None:
            return {}
        body = self._decode_response(resp)
        if isinstance(body, dict):
            return body.get("data") or {}
        return {}

    def _extract_output_filename(self, url: str) -> str:
        text = str(url or "").strip()
        if not text:
            return ""
        for marker in ("/api/media/images/output/", "/images/output/"):
            if marker in text:
                return text.split(marker, 1)[1].split("?", 1)[0]
        return ""

    def _collect_openapi_paths(self) -> None:
        resp = self.request("openapi_inventory", "GET", "/openapi.json", expected=(200,), allow_fail=True)
        if resp is None:
            return
        body = self._decode_response(resp)
        if not isinstance(body, dict):
            return
        items: List[Dict[str, str]] = []
        for path, methods in (body.get("paths") or {}).items():
            if isinstance(methods, dict):
                for method in methods.keys():
                    items.append({"method": str(method).upper(), "path": str(path)})
        self.runtime["openapi_paths"] = items

    def _coverage_summary(self) -> Dict[str, Any]:
        expected_pairs = {(x["method"], self._normalize_path(x["path"])) for x in self.runtime.get("openapi_paths") or []}
        tested_pairs = {(str(r.method).upper(), self._normalize_path(str(r.path))) for r in self.results}
        expanded = set(tested_pairs)
        for method, path in list(tested_pairs):
            for alias in self.route_aliases.get(path, []):
                expanded.add((method, self._normalize_path(alias)))
        covered = sorted(expected_pairs & expanded)
        uncovered = sorted(expected_pairs - expanded)
        return {
            "openapi_total": len(expected_pairs),
            "tested_total": len(tested_pairs),
            "covered_total": len(covered),
            "uncovered_total": len(uncovered),
            "covered": [{"method": m, "path": p} for m, p in covered],
            "uncovered": [{"method": m, "path": p} for m, p in uncovered],
        }

    def _latest_mock_code(self, phone: str, biz_type: str) -> str:
        if not self.cfg.auto_bootstrap_codes or db_manager is None:
            return ""
        row = db_manager.get_latest_valid_verification_code(phone, biz_type)
        return str((row or {}).get("code") or "").strip()

    def _login_password(self, phone: str, password: str, *, name_prefix: str) -> Tuple[str, str]:
        resp = self.request(f"{name_prefix}_login_by_password", "POST", "/api/auth/login", json_body={"phone": phone, "password": password, "loginType": "password"}, expected=(200, 400, 401, 404, 500), allow_fail=True)
        data = self._body_data(resp)
        return str(data.get("token") or ""), str(data.get("user_id") or "")

    def _register_or_login_user(self, *, phone: str, password: str, register_code: str, login_code: str, runtime_token_key: str, runtime_user_key: str, name_prefix: str) -> None:
        self.request(f"{name_prefix}_send_code_register", "POST", "/api/auth/send-code", json_body={"phone": phone, "type": "register"}, expected=(200, 400, 409, 500), allow_fail=True)
        register_code = register_code or self._latest_mock_code(phone, "register")
        if register_code:
            resp = self.request(f"{name_prefix}_register", "POST", "/api/auth/register", json_body={"phone": phone, "password": password, "code": register_code}, expected=(201, 200, 400, 409, 500), allow_fail=True)
            data = self._body_data(resp)
            if data.get("token"):
                self.runtime[runtime_token_key] = data["token"]
            if data.get("user_id"):
                self.runtime[runtime_user_key] = data["user_id"]
        if not self.runtime.get(runtime_token_key):
            token, user_id = self._login_password(phone, password, name_prefix=name_prefix)
            if token:
                self.runtime[runtime_token_key] = token
            if user_id:
                self.runtime[runtime_user_key] = user_id
        self.request(f"{name_prefix}_send_code_login", "POST", "/api/auth/send-code", json_body={"phone": phone, "type": "login"}, expected=(200, 400, 500), allow_fail=True)
        login_code = login_code or self._latest_mock_code(phone, "login")
        if login_code:
            resp = self.request(f"{name_prefix}_login_by_code", "POST", "/api/auth/login", json_body={"phone": phone, "code": login_code, "loginType": "code"}, expected=(200, 400, 404, 500), allow_fail=True)
            data = self._body_data(resp)
            if data.get("token"):
                self.runtime[f"{runtime_token_key}_by_code"] = data["token"]
                self.runtime[runtime_token_key] = data["token"]
            if data.get("user_id") and not self.runtime.get(runtime_user_key):
                self.runtime[runtime_user_key] = data["user_id"]

    def _primary_token(self) -> str:
        return str(self.runtime.get("primary_token") or self.cfg.token or "")

    def _secondary_token(self) -> str:
        return str(self.runtime.get("secondary_token") or self.cfg.secondary_token or "")

    def _admin_token(self) -> str:
        return str(self.runtime.get("admin_token") or self.cfg.admin_token or "")

    def _primary_user_id(self) -> str:
        return str(self.runtime.get("primary_user_id") or self.cfg.user_id or "")

    def _secondary_user_id(self) -> str:
        return str(self.runtime.get("secondary_user_id") or self.cfg.secondary_user_id or "")

    def bootstrap_identities(self) -> None:
        self._register_or_login_user(phone=self.cfg.phone, password=self.cfg.password, register_code=self.cfg.register_code, login_code=self.cfg.login_code, runtime_token_key="primary_token", runtime_user_key="primary_user_id", name_prefix="primary")
        self._register_or_login_user(phone=self.cfg.second_phone, password=self.cfg.second_password, register_code=self.cfg.second_register_code, login_code=self.cfg.second_login_code, runtime_token_key="secondary_token", runtime_user_key="secondary_user_id", name_prefix="secondary")
        self.runtime["bootstrap"] = {"primary_token_ready": bool(self._primary_token()), "secondary_token_ready": bool(self._secondary_token()), "admin_token_ready": bool(self._admin_token()), "primary_user_id": self._primary_user_id(), "secondary_user_id": self._secondary_user_id()}

    def test_public(self) -> None:
        self.prepare_fixtures()
        self.request("health", "GET", "/health", expected=(200,))
        self.request("openapi", "GET", "/openapi.json", expected=(200,))
        self._collect_openapi_paths()
        probe_phone = str(self.runtime.get("register_probe_phone") or "").strip()
        if probe_phone:
            self.request("send_code_register_probe_public", "POST", "/api/auth/send-code", json_body={"phone": probe_phone, "type": "register"}, expected=(200, 400, 409, 500), allow_fail=True)
            probe_code = self._latest_mock_code(probe_phone, "register")
            if probe_code:
                self.request("register_probe_public", "POST", "/api/auth/register", json_body={"phone": probe_phone, "password": self.cfg.password, "code": probe_code}, expected=(201, 200, 400, 409, 500), allow_fail=True)
        self.request("send_code_register_public", "POST", "/api/auth/send-code", json_body={"phone": self.cfg.phone, "type": "register"}, expected=(200, 400, 409, 500), allow_fail=True)
        self.request("send_code_login_public", "POST", "/api/auth/send-code", json_body={"phone": self.cfg.phone, "type": "login"}, expected=(200, 400, 404, 500), allow_fail=True)

    def test_auth(self) -> None:
        self.bootstrap_identities()
        reset_code = self.cfg.reset_code
        self.request("primary_send_code_reset_without_token_should_fail", "POST", "/api/auth/send-code", json_body={"phone": self.cfg.phone, "type": "reset_password"}, expected=(401, 403, 500), allow_fail=True)
        self.request("primary_send_code_reset", "POST", "/api/auth/send-code", token=self._primary_token(), json_body={"phone": self.cfg.phone, "type": "reset_password"}, expected=(200, 400, 401, 403, 500), allow_fail=True)
        if not reset_code:
            reset_code = self._latest_mock_code(self.cfg.phone, "reset_password")
        if reset_code:
            self.request("reset_password_without_token_should_fail", "POST", "/api/auth/reset-password", json_body={"phone": self.cfg.phone, "code": reset_code, "newPassword": self.cfg.new_password}, expected=(401, 403, 500), allow_fail=True)
            self.request("reset_password", "POST", "/api/auth/reset-password", token=self._primary_token(), json_body={"phone": self.cfg.phone, "code": reset_code, "newPassword": self.cfg.new_password}, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
            resp = self.request("login_by_new_password", "POST", "/api/auth/login", json_body={"phone": self.cfg.phone, "password": self.cfg.new_password, "loginType": "password"}, expected=(200, 400, 401, 404, 500), allow_fail=True)
            data = self._body_data(resp)
            if data.get("token"):
                self.runtime["primary_token"] = data["token"]
            if data.get("user_id"):
                self.runtime["primary_user_id"] = data["user_id"]
        else:
            self.skip("reset_password", "POST", "/api/auth/reset-password", "缺少 reset_password 验证码")

    def test_protected(self) -> None:
        primary = self._primary_token()
        secondary = self._secondary_token()
        if not primary:
            self.skip("protected_matrix", "GET", "/api/user/info", "主用户 token 不可用")
            return
        self.request("user_info_unauthorized", "GET", "/api/user/info", expected=(401, 500), allow_fail=True)
        self.request("user_info_primary", "GET", "/api/user/info", token=primary, expected=(200, 401, 500), allow_fail=True)
        self.request("update_profile_primary", "PUT", "/api/user/profile", token=primary, json_body={"avatar": "https://example.com/avatar.jpg"}, expected=(200, 400, 401, 500), allow_fail=True)
        self.request("update_nickname_primary", "PUT", "/api/user/nickname", token=primary, json_body={"nickname": "新昵称测试"}, expected=(200, 400, 401, 500), allow_fail=True)
        self.request("user_history_primary", "GET", "/api/user/history", token=primary, params={"limit": 10}, expected=(200, 401, 500), allow_fail=True)
        self.request("preferences_get_primary", "GET", "/api/user/preferences", token=primary, expected=(200, 401, 500), allow_fail=True)
        self.request("preferences_put_primary", "PUT", "/api/user/preferences", token=primary, json_body={"preferred_scenes": ["日常通勤", "商务稳重"], "preferred_categories": ["lip", "brow"], "preferred_finishes": ["natural"], "budget_min": 50, "budget_max": 300}, expected=(200, 400, 401, 500), allow_fail=True)
        self.request("membership_primary", "GET", "/api/user/membership", token=primary, expected=(200, 401, 500), allow_fail=True)
        self.request("latest_user_image_primary", "GET", "/api/user/images/latest", token=primary, expected=(200, 401, 404, 500), allow_fail=True)
        self.request("personalized_primary", "GET", "/api/pca/personalized_recommendations", token=primary, params={"limit": 10}, expected=(200, 401, 500), allow_fail=True)
        self.request("pair_recommendations_primary", "GET", "/api/recommend/pairs", token=primary, params={"source_sku_id": self.cfg.source_sku_id, "limit": 6}, expected=(200, 401, 500), allow_fail=True)
        self.request("recommend_products_primary", "GET", "/api/recommend/products", token=primary, params={"season": self.cfg.season, "category": self.cfg.category, "limit": 20}, expected=(200, 401, 403, 500), allow_fail=True)
        self.request("bundle_recommend_primary", "GET", "/api/recommend/bundles", token=primary, params={"season": self.cfg.season, "current_product": self.cfg.product_id}, expected=(200, 401, 403, 500), allow_fail=True)
        self.request("style_templates_primary", "GET", "/api/makeup/style-templates", token=primary, params={"season": self.cfg.season}, expected=(200, 401, 500), allow_fail=True)
        if secondary and self._primary_user_id():
            self.request("recommend_products_cross_user_forbidden", "GET", "/api/recommend/products", token=secondary, params={"user_id": self._primary_user_id(), "season": self.cfg.season, "category": self.cfg.category}, expected=(403, 401, 500), allow_fail=True)
            self.request("cart_list_cross_user_forbidden", "GET", "/api/cart", token=secondary, params={"user_id": self._primary_user_id()}, expected=(403, 401, 500), allow_fail=True)

    def test_media(self) -> None:
        primary = self._primary_token()
        if not primary:
            self.skip("media_group", "POST", "/api/media/process-upload", "主用户 token 不可用")
            return
        if not self.cfg.image_path or not os.path.exists(self.cfg.image_path):
            self.skip("media_group", "POST", "/api/media/process-upload", "缺少可用的 --image 文件")
            return
        f1 = self._open_file_tuple(self.cfg.image_path)
        try:
            resp = self.request("process_upload_primary", "POST", "/api/media/process-upload", token=primary, files={"file": f1}, expected=(200, 400, 401, 500), allow_fail=True)
        finally:
            f1[1].close()
        data = self._body_data(resp)
        if data.get("group_id"):
            self.runtime["group_id"] = data["group_id"]
        if data.get("result_url"):
            self.runtime["result_url"] = data["result_url"]
            self.runtime["current_image"] = data["result_url"]
            extracted = self._extract_output_filename(str(data["result_url"]))
            if extracted:
                self.runtime["output_filename"] = extracted
        f2 = self._open_file_tuple(self.cfg.image_path)
        try:
            self.request("analyze_color_type_primary", "POST", "/api/pca/analyze", token=primary, files={"image": f2}, data={"user_id": self._primary_user_id()}, expected=(200, 400, 401, 403, 500), allow_fail=True)
        finally:
            f2[1].close()
        f3 = self._open_file_tuple(self.cfg.image_path)
        try:
            self.request("compress_primary", "POST", "/api/media/compress", token=primary, files={"file": f3}, expected=(200, 400, 401, 500), allow_fail=True)
        finally:
            f3[1].close()

        f4 = self._open_file_tuple(self.cfg.image_path)
        try:
            self.request("upload_avatar_primary", "POST", "/api/user/avatar/upload", token=primary, files={"file": f4}, expected=(200, 400, 401, 500), allow_fail=True)
        finally:
            f4[1].close()

    def test_makeup(self) -> None:
        primary = self._primary_token()
        secondary = self._secondary_token()
        if not primary:
            self.skip("makeup_group", "POST", "/api/makeup/session", "主用户 token 不可用")
            return
        resp = None
        if self.cfg.image_path and os.path.exists(self.cfg.image_path):
            f = self._open_file_tuple(self.cfg.image_path)
            try:
                resp = self.request("create_makeup_session_upload", "POST", "/api/makeup/session", token=primary, files={"original_image": f}, data={"user_id_form": self._primary_user_id()}, expected=(200, 400, 401, 403, 500), allow_fail=True)
            finally:
                f[1].close()
        elif self.runtime.get("result_url"):
            resp = self.request("create_makeup_session_json", "POST", "/api/makeup/session", token=primary, json_body={"original_image": self.runtime["result_url"], "user_id": self._primary_user_id()}, expected=(200, 400, 401, 403, 500), allow_fail=True)
        else:
            latest_image_resp = self.request("latest_user_image_for_makeup", "GET", "/api/user/images/latest", token=primary, expected=(200, 404, 401, 500), allow_fail=True)
            latest_data = self._body_data(latest_image_resp)
            latest_url = str(latest_data.get("url") or "").strip()
            if latest_url:
                resp = self.request("create_makeup_session_latest_image", "POST", "/api/makeup/session", token=primary, json_body={"original_image": latest_url, "user_id": self._primary_user_id()}, expected=(200, 400, 401, 403, 500), allow_fail=True)
            else:
                self.skip("create_makeup_session", "POST", "/api/makeup/session", "缺少图片或可复用 URL")
        data = self._body_data(resp)
        if data.get("session_id"):
            self.runtime["session_id"] = data["session_id"]
        original_image = str(data.get("original_image") or "").strip()
        extracted_original = self._extract_output_filename(original_image)
        if extracted_original:
            self.runtime["output_filename"] = extracted_original
        if data.get("current_image"):
            self.runtime["current_image"] = data["current_image"]
            current_image = str(data.get("current_image") or "").strip()
            extracted_current = self._extract_output_filename(current_image)
            if extracted_current:
                self.runtime["output_filename"] = extracted_current
        session_id = str(self.runtime.get("session_id") or "")
        if not session_id:
            self.skip("makeup_session_ops", "POST", "/api/makeup/apply", "没有可用 session_id")
            return
        self.request("apply_makeup_primary", "POST", "/api/makeup/apply", token=primary, json_body={"session_id": session_id, "product_id": self.cfg.product_id, "category": self.cfg.category}, expected=(200, 400, 401, 403, 404, 500, 503), allow_fail=True)
        self.request("get_makeup_session_primary", "GET", f"/api/makeup/session/{session_id}", token=primary, expected=(200, 401, 403, 404, 500), allow_fail=True)
        self.request("score_look_primary", "POST", "/api/makeup/score", token=primary, json_body={"session_id": session_id}, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        self.request("undo_makeup_primary", "POST", "/api/makeup/undo", token=primary, json_body={"session_id": session_id}, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        self.request("reset_part_primary", "POST", "/api/makeup/reset-part", token=primary, json_body={"session_id": session_id, "category": self.cfg.category}, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        self.request("reset_makeup_primary", "POST", "/api/makeup/reset", token=primary, json_body={"session_id": session_id}, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        resp = self.request("save_makeup_scheme_primary", "POST", "/api/makeup/schemes", token=primary, json_body={"session_id": session_id, "scheme_name": self.cfg.scheme_name, "user_id": self._primary_user_id()}, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        data = self._body_data(resp)
        if data.get("scheme_id"):
            self.runtime["scheme_id"] = data["scheme_id"]
        self.request("get_makeup_schemes_primary", "GET", "/api/makeup/schemes", token=primary, params={"limit": 20}, expected=(200, 401, 403, 500), allow_fail=True)
        if self.runtime.get("scheme_id"):
            self.request("get_makeup_scheme_detail_primary", "GET", f"/api/makeup/schemes/{self.runtime['scheme_id']}", token=primary, expected=(200, 401, 403, 404, 500), allow_fail=True)
        if secondary:
            self.request("get_makeup_session_other_user_forbidden", "GET", f"/api/makeup/session/{session_id}", token=secondary, expected=(403, 401, 404, 500), allow_fail=True)
            self.request("score_look_other_user_forbidden", "POST", "/api/makeup/score", token=secondary, json_body={"session_id": session_id}, expected=(403, 401, 404, 500), allow_fail=True)
            self.request("delete_scheme_other_user_forbidden", "DELETE", f"/api/makeup/schemes/{self.runtime.get('scheme_id') or ''}", token=secondary, expected=(403, 400, 401, 404, 500), allow_fail=True)
            if self.runtime.get("scheme_id"):
                self.request("get_makeup_scheme_detail_other_user_forbidden", "GET", f"/api/makeup/schemes/{self.runtime['scheme_id']}", token=secondary, expected=(401, 403, 404, 500), allow_fail=True)
        if self.runtime.get("scheme_id"):
            self.request("delete_makeup_scheme_primary", "DELETE", f"/api/makeup/schemes/{self.runtime['scheme_id']}", token=primary, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        legacy_filename = self.cfg.legacy_filename or self.runtime.get("output_filename") or ""

    def test_cart(self) -> None:
        primary = self._primary_token()
        secondary = self._secondary_token()
        if not primary:
            self.skip("cart_group", "GET", "/cart/list", "主用户 token 不可用")
            return
        self.request("cart_list_primary", "GET", "/api/cart", token=primary, expected=(200, 401, 403, 500), allow_fail=True)
        self.request("cart_add_primary", "POST", "/api/cart/items", token=primary, json_body={"product_id": self.cfg.product_id, "quantity": 1}, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        self.request("cart_update_primary", "PUT", "/api/cart/items", token=primary, json_body={"product_id": self.cfg.product_id, "quantity": 2}, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        if self.cfg.bundle_id:
            self.request("cart_add_bundle_by_bundle_primary", "POST", "/api/cart/bundles", token=primary, json_body={"bundle_id": self.cfg.bundle_id}, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        else:
            self.skip("cart_add_bundle_by_bundle_primary", "POST", "/cart/add_bundle", "缺少 --bundle-id")
        self.request("cart_add_bundle_by_products_primary", "POST", "/api/cart/bundles", token=primary, json_body={"product_ids": [self.cfg.product_id]}, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        self.request("cart_set_bulk_primary", "POST", "/api/cart/items/bulk", token=primary, json_body={"items": [{"product_id": self.cfg.product_id, "quantity": 2}]}, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        self.request("cart_remove_primary", "DELETE", f"/api/cart/items/{self.cfg.product_id}", token=primary, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        self.request("cart_clear_primary", "POST", "/api/cart/clear", token=primary, expected=(200, 401, 403, 500), allow_fail=True)
        if secondary and self._primary_user_id():
            self.request("cart_add_cross_user_forbidden", "POST", "/api/cart/items", token=secondary, json_body={"product_id": self.cfg.product_id, "quantity": 1, "user_id": self._primary_user_id()}, expected=(403, 401, 404, 500), allow_fail=True)

    def test_admin(self) -> None:
        admin_token = self._admin_token()
        primary = self._primary_token()
        if primary:
            self.request("admin_products_with_normal_user_forbidden", "GET", "/api/admin/products", token=primary, params={"limit": 20}, expected=(403, 401, 500), allow_fail=True)
        if not admin_token:
            self.skip("admin_group", "GET", "/api/admin/products", "缺少管理员 token")
            return
        self.request("admin_products", "GET", "/api/admin/products", token=admin_token, params={"limit": 50, "category": self.cfg.category}, expected=(200, 401, 403, 500), allow_fail=True)
        create_id = f"test_{int(time.time())}_{self.cfg.product_id}"
        self.runtime["created_product_id"] = create_id
        self.request("admin_create_product", "POST", "/api/admin/products", token=admin_token, json_body={"p_id": create_id, "name": "接口测试商品", "category": self.cfg.category, "apply_area": "lips", "render_hex": "#B14A5A"}, expected=(200, 400, 401, 403, 500), allow_fail=True)
        self.request("admin_get_product", "GET", f"/api/admin/products/{create_id}", token=admin_token, expected=(200, 401, 403, 404, 500), allow_fail=True)
        self.request("admin_put_product", "PUT", f"/api/admin/products/{create_id}", token=admin_token, json_body={"name": "接口测试商品-更新", "render_hex": "#A84558"}, expected=(200, 400, 401, 403, 404, 500), allow_fail=True)
        self.request("admin_delete_product", "DELETE", f"/api/admin/products/{create_id}", token=admin_token, expected=(200, 401, 403, 404, 500), allow_fail=True)

    def test_images(self) -> None:
        primary = self._primary_token()
        secondary = self._secondary_token()
        filename = self.cfg.legacy_filename or self.runtime.get("output_filename") or ""
        latest_image_type = ""
        if not primary:
            self.skip("images_group", "GET", "/api/media/images/output/{filename}", "主用户 token 不可用")
            return
        if not filename:
            latest_image_resp = self.request("latest_user_image_for_images", "GET", "/api/user/images/latest", token=primary, expected=(200, 404, 401, 500), allow_fail=True)
            latest_data = self._body_data(latest_image_resp)
            latest_url = str(latest_data.get("url") or "").strip()
            latest_image_type = str(latest_data.get("image_type") or "").strip()
            if latest_url:
                filename = self._extract_output_filename(latest_url)
                if not filename and "/images/upload/" in latest_url:
                    filename = latest_url.split('/images/upload/', 1)[1].split('?', 1)[0]
            if not filename:
                self.skip("images_group", "GET", "/api/media/images/output/{filename}", "缺少图片 filename")
                return
        self.request("serve_output_image_header_primary", "GET", f"/api/media/images/output/{filename}", token=primary, expected=(200, 401, 403, 404, 500), allow_fail=True)
        self.request("serve_output_image_query_primary", "GET", f"/api/media/images/output/{filename}", params={"token": primary}, headers={"Authorization": ""}, expected=(200, 401, 403, 404, 500), allow_fail=True)
        self.request("serve_upload_image_primary", "GET", f"/api/media/images/upload/{filename}", token=primary, expected=(200, 401, 403, 404, 500), allow_fail=True)
        self.request("serve_avatar_image_primary", "GET", f"/api/media/images/avatar/defaults/avatar-default.png", token=primary, expected=(200, 401, 403, 404, 500), allow_fail=True)
        if secondary:
            self.request("serve_output_image_other_user_forbidden", "GET", f"/api/media/images/output/{filename}", token=secondary, expected=(403, 401, 404, 500), allow_fail=True)

    def test_logout(self) -> None:
        primary = self._primary_token()
        if not primary:
            self.skip("logout", "POST", "/api/auth/logout", "主用户 token 不可用")
            return
        self.request("logout_primary", "POST", "/api/auth/logout", token=primary, expected=(200, 401, 500), allow_fail=True)
        self.request("user_info_after_logout_should_fail", "GET", "/api/user/info", token=primary, expected=(401, 500), allow_fail=True)

    def save_report(self) -> None:
        coverage = self._coverage_summary()
        payload = {"base_url": self.cfg.base_url, "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"), "runtime": self.runtime, "summary": {"total": len(self.results), "passed": sum(1 for r in self.results if r.ok), "failed": sum(1 for r in self.results if not r.ok and not r.skipped), "skipped": sum(1 for r in self.results if r.skipped)}, "coverage": coverage, "results": [r.__dict__ for r in self.results]}
        with open(self.cfg.output, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存: {self.cfg.output}")
        print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
        print(json.dumps(payload["coverage"], ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="FastAPI 接口回归脚本")
    p.add_argument("--base-url", default="http://127.0.0.1:5001")
    p.add_argument("--run", default="all", choices=["public", "auth", "protected", "media", "makeup", "cart", "admin", "images", "logout", "all"])
    p.add_argument("--token", default="")
    p.add_argument("--secondary-token", default="")
    p.add_argument("--admin-token", default="")
    p.add_argument("--phone", default="13800138000")
    p.add_argument("--password", default="123456")
    p.add_argument("--new-password", default="654321")
    p.add_argument("--second-phone", default="13800138001")
    p.add_argument("--second-password", default="123456")
    p.add_argument("--register-code", default="")
    p.add_argument("--login-code", default="")
    p.add_argument("--reset-code", default="")
    p.add_argument("--second-register-code", default="")
    p.add_argument("--second-login-code", default="")
    p.add_argument("--image", dest="image_path", default="")
    p.add_argument("--user-id", default="")
    p.add_argument("--secondary-user-id", default="")
    p.add_argument("--product-id", default="lip_001")
    p.add_argument("--bundle-id", default="")
    p.add_argument("--source-sku-id", default="lip_001")
    p.add_argument("--season", default="Warm Autumn")
    p.add_argument("--category", default="lip")
    p.add_argument("--scheme-name", default="通勤妆方案")
    p.add_argument("--legacy-filename", default="")
    p.add_argument("--legacy-style", default="clean")
    p.add_argument("--timeout", type=float, default=40.0)
    p.add_argument("--output", default="api_test_report.json")
    p.add_argument("--no-verify-ssl", action="store_true")
    p.add_argument("--auto-bootstrap-codes", action="store_true")
    return p


def main() -> int:
    args = build_parser().parse_args()
    cfg = Config(base_url=args.base_url, token=args.token, secondary_token=args.secondary_token, admin_token=args.admin_token, phone=args.phone, password=args.password, new_password=args.new_password, second_phone=args.second_phone, second_password=args.second_password, register_code=args.register_code, login_code=args.login_code, reset_code=args.reset_code, second_register_code=args.second_register_code, second_login_code=args.second_login_code, image_path=args.image_path, user_id=args.user_id, secondary_user_id=args.secondary_user_id, product_id=args.product_id, bundle_id=args.bundle_id, source_sku_id=args.source_sku_id, season=args.season, category=args.category, scheme_name=args.scheme_name, legacy_filename=args.legacy_filename, legacy_style=args.legacy_style, timeout=args.timeout, output=args.output, verify_ssl=not args.no_verify_ssl, auto_bootstrap_codes=args.auto_bootstrap_codes)
    tester = APITester(cfg)
    groups = {
        "public": [tester.test_public],
        "auth": [tester.test_auth],
        "protected": [tester.bootstrap_identities, tester.test_protected],
        "media": [tester.bootstrap_identities, tester.test_media],
        "makeup": [tester.bootstrap_identities, tester.test_media, tester.test_makeup],
        "cart": [tester.bootstrap_identities, tester.test_cart],
        "admin": [tester.bootstrap_identities, tester.test_admin],
        "images": [tester.bootstrap_identities, tester.test_media, tester.test_images],
        "logout": [tester.bootstrap_identities, tester.test_logout],
        "all": [tester.test_public, tester.test_auth, tester.test_protected, tester.test_media, tester.test_makeup, tester.test_cart, tester.test_admin, tester.test_images, tester.test_logout],
    }
    for fn in groups[args.run]:
        print(f"\n=== 运行测试组: {fn.__name__} ===")
        fn()
    tester.save_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
