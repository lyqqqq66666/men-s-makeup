import json
import os
import sqlite3
import uuid
import hashlib
import threading
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'app_data.db')
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'schema.sql')

_DB_WRITE_LOCK = threading.Lock()


class DBWrapper:
    """
    包装 pymysql 连接，模拟 sqlite3.Connection 接口。
    - 自动把 SQL 中的 ? 占位符转成 %s（pymysql 要求）
    - 静默忽略 PRAGMA 语句（MySQL 不支持）
    - row_factory 赋值被接受但不生效（DictCursor 已返回 dict）
    """
    def __init__(self, pymysql_conn):
        self._conn = pymysql_conn
        self._cursor = pymysql_conn.cursor()
        self.row_factory = None
        # 存储数据库名，供 _table_exists 等函数使用
        self._db_name = getattr(pymysql_conn, 'db', None) or getattr(pymysql_conn, 'database', 'menx')

    def _translate(self, sql: str):
        s = sql.strip()
        if s.upper().startswith("PRAGMA"):
            return None
        return sql.replace("?", "%s")

    def execute(self, sql, params=None):
        translated = self._translate(sql)
        if translated is None:
            self._last_result = None
            return self
        if params is None:
            params = ()
        self._cursor.execute(translated, params)
        self._last_result = self._cursor
        return self

    def executemany(self, sql, params_seq):
        translated = self._translate(sql)
        if translated is None:
            self._last_result = None
            return self
        self._cursor.executemany(translated, params_seq)
        self._last_result = self._cursor
        return self

    def fetchone(self):
        if self._last_result is None:
            return None
        return self._last_result.fetchone()

    def fetchall(self):
        if self._last_result is None:
            return []
        return self._last_result.fetchall()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    @property
    def rowcount(self):
        return self._cursor.rowcount


def _read_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    cfg = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, _, v = line.partition("=")
                    cfg[k.strip()] = v.strip()
    return cfg


def _get_db_type():
    t = os.getenv("DB_TYPE", "").lower()
    if t:
        return t
    return _read_env().get("DB_TYPE", "sqlite").lower()



def _row_to_dict(row):
    return dict(row) if row else None


def _rows_to_dicts(rows):
    return [dict(r) for r in rows]


def _to_json_safe(value):
    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(v) for v in value]
    if hasattr(value, 'item'):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)



def get_db_connection():
    db_type = _get_db_type()
    if db_type == "mysql":
        import pymysql
        cfg = _read_env()
        db_host = cfg.get("DB_HOST", "localhost")
        db_port = int(cfg.get("DB_PORT", "3306"))
        db_name = cfg.get("DB_NAME", "menx")
        db_user = cfg.get("DB_USER", "")
        db_pass = cfg.get("DB_PASSWORD", "")
        if not db_user:
            raise RuntimeError("DB_TYPE=mysql 但 .env 中未设置 DB_USER")
        raw_conn = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        # 返回 DBWrapper（如果定义了）；否则直接返回 raw_conn
        if "DBWrapper" in globals():
            return DBWrapper(raw_conn)
        return raw_conn
    # SQLite（默认）
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _table_exists(conn, table_name: str) -> bool:
    if isinstance(conn, DBWrapper):
        # MySQL：通过 INFORMATION_SCHEMA 查询
        db_name = conn._db_name or "menx"
        conn.execute(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?",
            (db_name, table_name)
        )
        row = conn.fetchone()
        return row is not None
    # SQLite
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,)
    ).fetchone()
    return row is not None


def _get_column_names(conn, table_name: str) -> set:
    if not _table_exists(conn, table_name):
        return set()
    if isinstance(conn, DBWrapper):
        # MySQL：通过 INFORMATION_SCHEMA.COLUMNS 查询
        db_name = conn._db_name or "menx"
        conn.execute(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?",
            (db_name, table_name)
        )
        rows = conn.fetchall()
        return {r["COLUMN_NAME"] for r in rows}
    # SQLite
    cols = conn.execute(f'PRAGMA table_info({table_name})').fetchall()
    return {c[1] for c in cols}


def _ensure_column(conn, table_name: str, column_name: str, column_sql: str) -> None:
    col_names = _get_column_names(conn, table_name)
    if column_name not in col_names:
        conn.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_sql}')


def _rebuild_users_without_username(conn) -> None:
    col_names = _get_column_names(conn, 'users')
    if 'username' not in col_names:
        return
    conn.execute('PRAGMA foreign_keys = OFF')
    conn.execute('DROP INDEX IF EXISTS idx_users_username_unique')
    conn.execute('DROP INDEX IF EXISTS idx_users_username_unique_nocase')
    try:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS users__new (
                user_id TEXT PRIMARY KEY,
                phone TEXT,
                password_hash TEXT,
                nickname TEXT NOT NULL CHECK (length(trim(nickname)) > 0),
                avatar TEXT,
                role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled', 'deleted')),
                season_type TEXT,
                last_login_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        conn.execute(
            '''
            INSERT INTO users__new (
                user_id, phone, password_hash, nickname, avatar, role, status, season_type, last_login_at, created_at, updated_at
            )
            SELECT
                user_id, phone, password_hash, nickname, avatar,
                COALESCE(role, 'user'),
                COALESCE(status, 'active'),
                season_type, last_login_at, created_at, updated_at
            FROM users
            '''
        )
        conn.execute('DROP TABLE users')
        conn.execute('ALTER TABLE users__new RENAME TO users')
    finally:
        conn.execute('PRAGMA foreign_keys = ON')


def _ensure_users_columns_before_schema(conn):
    """在执行 schema.sql 前，先兼容旧 users 表缺失列的情况。

    场景：旧库 users 表没有 password_hash / phone 等字段，
    初始化阶段需要兜底补列。
    MySQL 模式：表会由 schema_mysql_clean.sql 完整创建，不需要修补。
    """
    # MySQL 模式：直接返回，不需要修补
    db_type = _get_db_type()
    if db_type == 'mysql':
        return
    if not _table_exists(conn, 'users'):
        return

    if 'username' in _get_column_names(conn, 'users'):
        _rebuild_users_without_username(conn)

    cols = conn.execute("PRAGMA table_info(users)").fetchall()
    col_names = {c[1] for c in cols}

    if 'password_hash' not in col_names:
        conn.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')
    if 'phone' not in col_names:
        conn.execute('ALTER TABLE users ADD COLUMN phone TEXT')
    if 'status' not in col_names:
        conn.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
    if 'last_login_at' not in col_names:
        conn.execute('ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP')
    if 'role' not in col_names:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")

def init_db():
    """初始化数据库表结构"""
    # 确保存储目录已建立
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with _DB_WRITE_LOCK:
        conn = get_db_connection()
        try:
            _ensure_users_columns_before_schema(conn)
            conn.execute('PRAGMA foreign_keys = OFF')
            for sql in [
                'DROP INDEX IF EXISTS idx_uploads_group_id_unique',
                'DROP INDEX IF EXISTS idx_uploads_created_at',
                'DROP INDEX IF EXISTS idx_debug_images_group_created',
                'DROP INDEX IF EXISTS idx_corrected_images_group_created',
                'DROP INDEX IF EXISTS idx_makeup_images_group_created',
                'DROP INDEX IF EXISTS idx_products_season_category',
                'DROP INDEX IF EXISTS idx_products_category',
                'DROP INDEX IF EXISTS idx_products_category_price',
                'DROP INDEX IF EXISTS idx_products_season_price',
                'DROP INDEX IF EXISTS idx_cart_user_product_unique',
                'DROP INDEX IF EXISTS idx_cart_user_id',
                'DROP INDEX IF EXISTS idx_product_color_profiles_product_id',
                'DROP INDEX IF EXISTS idx_season_sku_map_season_product',
                'DROP TABLE IF EXISTS makeup_images',
                'DROP TABLE IF EXISTS debug_images',
                'DROP TABLE IF EXISTS corrected_images',
                'DROP TABLE IF EXISTS uploads',
                'DROP TABLE IF EXISTS cart',
                'DROP TABLE IF EXISTS products',
                'DROP TABLE IF EXISTS season_sku_map',
                'DROP TABLE IF EXISTS product_color_profiles',
            ]:
                try:
                    conn.execute(sql)
                except Exception:
                    pass
            # 根据数据库类型选择 schema 文件
            db_type = _get_db_type()
            if db_type == 'mysql':
                schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'schema_mysql_clean.sql')
            else:
                schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'schema.sql')
            
            with open(schema_path, 'r', encoding='utf-8') as f:
                raw_sql = f.read()

            if db_type == 'mysql' and isinstance(conn, DBWrapper):
                # MySQL 模式：逐条执行 SQL，跳过 PRAGMA
                if isinstance(conn, DBWrapper):
                    try:
                        conn.execute('SET foreign_key_checks=0')
                    except Exception as e:
                        print(f"[init_db] Warning: Cannot disable foreign_key_checks: {e}")
                for stmt in raw_sql.split(';'):
                    stmt = stmt.strip()
                    if not stmt or stmt.upper().startswith('PRAGMA'):
                        continue
                    try:
                        conn.execute(stmt)
                    except Exception as e:
                        # 打印错误但不中断（如 IF NOT EXISTS 类的重复创建）
                        print(f"[init_db] Warning: SQL execution error (continuing): {e}")
                        print(f"[init_db] Statement: {stmt[:200]}")
                if isinstance(conn, DBWrapper):
                    try:
                        conn.execute('SET foreign_key_checks=1')
                    except Exception as e:
                        print(f"[init_db] Warning: Cannot enable foreign_key_checks: {e}")
            else:
                schema_sql = raw_sql.replace('PRAGMA foreign_keys = ON;\n', '', 1)
                for legacy_stmt in [
                    'DROP TABLE IF EXISTS makeup_images;\n',
                    'DROP TABLE IF EXISTS debug_images;\n',
                    'DROP TABLE IF EXISTS corrected_images;\n',
                    'DROP TABLE IF EXISTS uploads;\n',
                    'DROP TABLE IF EXISTS cart;\n',
                    'DROP TABLE IF EXISTS products;\n',
                    'DROP INDEX IF EXISTS idx_uploads_group_id_unique;\n',
                    'DROP INDEX IF EXISTS idx_uploads_created_at;\n',
                    'DROP INDEX IF EXISTS idx_debug_images_group_created;\n',
                    'DROP INDEX IF EXISTS idx_corrected_images_group_created;\n',
                    'DROP INDEX IF EXISTS idx_makeup_images_group_created;\n',
                    'DROP INDEX IF EXISTS idx_products_season_category;\n',
                    'DROP INDEX IF EXISTS idx_products_category;\n',
                    'DROP INDEX IF EXISTS idx_products_category_price;\n',
                    'DROP INDEX IF EXISTS idx_products_season_price;\n',
                    'DROP INDEX IF EXISTS idx_cart_user_product_unique;\n',
                    'DROP INDEX IF EXISTS idx_cart_user_id;\n',
                    'DROP INDEX IF EXISTS idx_product_color_profiles_product_id;\n',
                    'DROP INDEX IF EXISTS idx_season_sku_map_season_product;\n',
                    'DROP TABLE IF EXISTS season_sku_map;\n',
                    'DROP TABLE IF EXISTS product_color_profiles;\n',
                ]:
                    schema_sql = schema_sql.replace(legacy_stmt, '')
                conn.executescript(schema_sql)
                conn.execute('PRAGMA foreign_keys = ON')
            _run_migrations(conn)
            conn.commit()
        finally:
            try:
                conn.execute('PRAGMA foreign_keys = ON')
            except Exception:
                pass
            conn.close()
    print(f"数据库初始化完成，路径: {DB_PATH}")


def _run_migrations(conn):
    """兼容历史库结构，按需补齐字段/索引"""
    # MySQL 模式：表已由 schema_mysql_clean.sql 完整创建，跳过所有迁移
    db_type = _get_db_type()
    if db_type == 'mysql':
        print(f"[migrations] MySQL mode detected, skipping all migrations")
        return
    cols = conn.execute("PRAGMA table_info(users)").fetchall()
    col_names = {c[1] for c in cols}

    if 'username' in col_names:
        _rebuild_users_without_username(conn)
        cols = conn.execute("PRAGMA table_info(users)").fetchall()
        col_names = {c[1] for c in cols}

    if 'password_hash' not in col_names:
        conn.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')
    if 'phone' not in col_names:
        conn.execute('ALTER TABLE users ADD COLUMN phone TEXT')
    if 'status' not in col_names:
        conn.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
    if 'last_login_at' not in col_names:
        conn.execute('ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP')
    if 'role' not in col_names:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")

    if _table_exists(conn, 'auth_tokens'):
        _ensure_column(conn, 'auth_tokens', 'token_type', "token_type TEXT NOT NULL DEFAULT 'bearer'")
        _ensure_column(conn, 'auth_tokens', 'source', "source TEXT NOT NULL DEFAULT 'password'")
        _ensure_column(conn, 'auth_tokens', 'created_at', 'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        _ensure_column(conn, 'auth_tokens', 'expires_at', 'expires_at TIMESTAMP')
        _ensure_column(conn, 'auth_tokens', 'revoked_at', 'revoked_at TIMESTAMP')

    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_unique ON users (phone) WHERE phone IS NOT NULL')

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS season_rules (
            season_type TEXT PRIMARY KEY,
            tone TEXT,
            lips_palette TEXT NOT NULL DEFAULT '[]',
            cheeks_palette TEXT NOT NULL DEFAULT '[]',
            brow_palette TEXT NOT NULL DEFAULT '[]',
            avoid_palette TEXT NOT NULL DEFAULT '[]',
            recommended_palette TEXT NOT NULL DEFAULT '[]',
            source TEXT DEFAULT 'excel',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS season_sku_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            season_type TEXT NOT NULL,
            sku_id TEXT NOT NULL,
            source TEXT DEFAULT 'excel',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sku_id) REFERENCES product_sku (sku_id)
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS product_color_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku_id TEXT NOT NULL,
            shade_name TEXT,
            hex_color TEXT NOT NULL,
            color_role TEXT NOT NULL DEFAULT 'primary' CHECK (color_role IN ('primary', 'palette', 'render', 'avoid')),
            source TEXT DEFAULT 'excel',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sku_id) REFERENCES product_sku (sku_id)
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS import_jobs (
            job_id TEXT PRIMARY KEY,
            source_name TEXT NOT NULL,
            source_path TEXT,
            status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'success', 'failed')),
            summary_json TEXT NOT NULL DEFAULT '{}',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        )
        '''
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_product_color_profiles_sku_id ON product_color_profiles (sku_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_product_color_profiles_hex_color ON product_color_profiles (hex_color)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_season_sku_map_season_sku ON season_sku_map (season_type, sku_id)')

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS verification_codes (
            code_id TEXT PRIMARY KEY,
            target TEXT NOT NULL,
            code TEXT NOT NULL,
            biz_type TEXT NOT NULL CHECK (biz_type IN ('register', 'login', 'reset_password')),
            channel TEXT NOT NULL DEFAULT 'mock' CHECK (channel IN ('mock', 'sms')),
            status TEXT NOT NULL DEFAULT 'sent' CHECK (status IN ('sent', 'verified', 'used', 'expired', 'cancelled')),
            expires_at TIMESTAMP NOT NULL,
            verified_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            meta_json TEXT NOT NULL DEFAULT '{}'
        )
        '''
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_verification_codes_target_biz_status ON verification_codes (target, biz_type, status)')

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS user_images (
            image_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            group_id TEXT,
            image_type TEXT NOT NULL,
            origin_filename TEXT,
            stored_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            mime_type TEXT,
            file_size INTEGER DEFAULT 0,
            width INTEGER,
            height INTEGER,
            source_session_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        '''
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_user_images_user_type_created ON user_images (user_id, image_type, created_at DESC)')

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS image_quality_reports (
            report_id TEXT PRIMARY KEY,
            image_id TEXT NOT NULL,
            has_face INTEGER NOT NULL DEFAULT 0,
            blur_score REAL,
            left_eye_score REAL,
            right_eye_score REAL,
            mouth_score REAL,
            occlusion_flag INTEGER NOT NULL DEFAULT 0,
            raw_report_json TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (image_id) REFERENCES user_images (image_id)
        )
        '''
    )

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS pca_analysis_records (
            analysis_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            image_id TEXT NOT NULL,
            season_type TEXT NOT NULL,
            tone TEXT,
            confidence REAL,
            recommended_palette_json TEXT NOT NULL DEFAULT '[]',
            avoid_palette_json TEXT NOT NULL DEFAULT '[]',
            feature_vector_json TEXT NOT NULL DEFAULT '[]',
            model_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (image_id) REFERENCES user_images (image_id)
        )
        '''
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_pca_analysis_user_created ON pca_analysis_records (user_id, created_at DESC)')

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS product_spu (
            spu_id TEXT PRIMARY KEY,
            brand TEXT,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            apply_area TEXT NOT NULL,
            image_url TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_product_spu_category ON product_spu (category)')

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS product_sku (
            sku_id TEXT PRIMARY KEY,
            spu_id TEXT NOT NULL,
            shade_name TEXT,
            hex_color TEXT NOT NULL,
            render_hex TEXT NOT NULL,
            render_mode INTEGER DEFAULT 0,
            finish_type TEXT,
            opacity REAL DEFAULT 0.6,
            feather INTEGER DEFAULT 8,
            transparency_max REAL DEFAULT 0.7,
            season_match TEXT,
            price REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            source TEXT DEFAULT 'seed',
            mask_params TEXT,
            render_params TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (spu_id) REFERENCES product_spu (spu_id)
        )
        '''
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_product_sku_spu_id ON product_sku (spu_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_product_sku_season_match ON product_sku (season_match)')

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS cart_items (
            cart_item_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            sku_id TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (sku_id) REFERENCES product_sku (sku_id)
        )
        '''
    )
    conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_cart_items_user_sku_unique ON cart_items (user_id, sku_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_cart_items_user_id ON cart_items (user_id)')

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS makeup_session_steps (
            step_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            step_no INTEGER NOT NULL,
            category TEXT NOT NULL,
            sku_id TEXT,
            input_image_id TEXT,
            output_image_id TEXT,
            render_params_json TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES makeup_sessions (session_id)
        )
        '''
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_makeup_session_steps_session_no ON makeup_session_steps (session_id, step_no)')

    scheme_cols = conn.execute("PRAGMA table_info(makeup_schemes)").fetchall() if _table_exists(conn, 'makeup_schemes') else []
    scheme_col_names = {c[1] for c in scheme_cols}
    if 'scene_tag' not in scheme_col_names:
        conn.execute('ALTER TABLE makeup_schemes ADD COLUMN scene_tag TEXT')
    if 'recommend_reason' not in scheme_col_names:
        conn.execute('ALTER TABLE makeup_schemes ADD COLUMN recommend_reason TEXT')

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS makeup_plan_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheme_id TEXT NOT NULL,
            category TEXT NOT NULL,
            sku_id TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scheme_id) REFERENCES makeup_schemes (scheme_id)
        )
        '''
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_makeup_plan_items_scheme ON makeup_plan_items (scheme_id, sort_order)')

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS bundle_recommendations (
            bundle_id TEXT PRIMARY KEY,
            season_type TEXT NOT NULL,
            bundle_name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS bundle_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bundle_id TEXT NOT NULL,
            sku_id TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (bundle_id) REFERENCES bundle_recommendations (bundle_id)
        )
        '''
    )
    bundle_count_row = conn.execute('SELECT COUNT(1) AS c FROM bundle_recommendations').fetchone()
    bundle_count = int(bundle_count_row['c'] or 0) if bundle_count_row else 0
    if bundle_count == 0:
        now = now_iso()
        conn.execute(
            'INSERT INTO bundle_recommendations (bundle_id, season_type, bundle_name, description, created_at) VALUES (?, ?, ?, ?, ?)',
            ('bundle_warm_autumn_basic', 'Warm Autumn', '暖秋基础推荐套装', '适合暖秋季型的基础妆容组合', now)
        )
        conn.execute(
            'INSERT INTO bundle_recommendations (bundle_id, season_type, bundle_name, description, created_at) VALUES (?, ?, ?, ?, ?)',
            ('bundle_cool_winter_basic', 'Cool Winter', '冷冬基础推荐套装', '适合冷冬季型的基础妆容组合', now)
        )
        for bundle_id, sku_id, sort_order in [
            ('bundle_warm_autumn_basic', 'SKU001', 1),
            ('bundle_warm_autumn_basic', 'SKU012', 2),
            ('bundle_warm_autumn_basic', 'SKU017', 3),
            ('bundle_cool_winter_basic', 'SKU002', 1),
            ('bundle_cool_winter_basic', 'SKU016', 2),
            ('bundle_cool_winter_basic', 'SKU021', 3),
        ]:
            sku_exists = conn.execute('SELECT 1 FROM product_sku WHERE sku_id = ?', (sku_id,)).fetchone()
            if sku_exists:
                conn.execute(
                    'INSERT INTO bundle_items (bundle_id, sku_id, sort_order) VALUES (?, ?, ?)',
                    (bundle_id, sku_id, sort_order)
                )

    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            preferred_scenes_json TEXT NOT NULL DEFAULT '[]',
            preferred_categories_json TEXT NOT NULL DEFAULT '[]',
            preferred_finishes_json TEXT NOT NULL DEFAULT '[]',
            budget_min REAL DEFAULT 0,
            budget_max REAL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS user_behavior_events (
            event_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            ref_type TEXT NOT NULL,
            ref_id TEXT,
            event_value REAL DEFAULT 1,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        '''
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_user_behavior_user_type_created ON user_behavior_events (user_id, event_type, created_at DESC)')
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS product_pair_recommendations (
            pair_id TEXT PRIMARY KEY,
            source_sku_id TEXT NOT NULL,
            target_sku_id TEXT NOT NULL,
            reason TEXT,
            score REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_sku_id) REFERENCES product_sku (sku_id),
            FOREIGN KEY (target_sku_id) REFERENCES product_sku (sku_id)
        )
        '''
    )
    conn.execute('CREATE INDEX IF NOT EXISTS idx_product_pair_source_score ON product_pair_recommendations (source_sku_id, score DESC)')
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS membership_profiles (
            user_id TEXT PRIMARY KEY,
            member_level TEXT NOT NULL DEFAULT 'basic',
            points INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        '''
    )


def _cleanup_expired_tokens(conn):
    now = now_iso()
    conn.execute('DELETE FROM auth_tokens WHERE expires_at IS NOT NULL AND expires_at <= ?', (now,))


def normalize_nickname(nickname: str) -> str:
    return (nickname or '').strip()


def default_nickname(phone=None) -> str:
    phone_text = (phone or '').strip()
    if len(phone_text) >= 4:
        return f'用户{phone_text[-4:]}'
    return f'用户{uuid.uuid4().hex[:6]}'


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == (password_hash or '')


def now_iso():
    return datetime.utcnow().isoformat(timespec='seconds')


def future_iso(hours=24):
    return (datetime.utcnow() + timedelta(hours=hours)).isoformat(timespec='seconds')

def get_full_history(group_id):
    """根据 group_id 查询新版图片链路。"""
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT * FROM user_images
        WHERE group_id = ?
        ORDER BY created_at ASC
        ''',
        (group_id,)
    ).fetchall()
    conn.close()
    images = _rows_to_dicts(rows)
    return {
        'group_id': group_id,
        'images': images,
        'upload': next((row for row in images if row.get('image_type') == 'upload'), None),
        'debug_images': [row for row in images if row.get('image_type') == 'debug'],
        'corrected': next((row for row in images if row.get('image_type') == 'corrected'), None),
    }


# ============================
# PRD 业务能力
# ============================

def get_user_by_id(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def create_user_with_phone(phone, password, nickname, avatar=None):
    user_id = f'user_{uuid.uuid4().hex[:12]}'
    pwd_hash = hash_password(password)
    now = now_iso()
    phone = (phone or '').strip() or None
    nickname = normalize_nickname(nickname) or default_nickname(phone=phone)

    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO users (user_id, phone, password_hash, nickname, avatar, role, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'user', 'active', ?, ?)
        ''',
        (user_id, phone, pwd_hash, nickname, avatar, now, now)
    )
    conn.commit()
    conn.close()
    return user_id


def get_user_by_phone(phone):
    phone = (phone or '').strip()
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM users WHERE phone = ?', (phone,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def upsert_user(user_id, nickname, avatar=None):
    conn = get_db_connection()
    existing = conn.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,)).fetchone()
    now = now_iso()

    if existing:
        conn.execute(
            'UPDATE users SET nickname = ?, avatar = COALESCE(?, avatar), updated_at = ? WHERE user_id = ?',
            (nickname, avatar, now, user_id)
        )
    else:
        conn.execute(
            'INSERT INTO users (user_id, nickname, avatar, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
            (user_id, nickname, avatar, now, now)
        )

    conn.commit()
    conn.close()


def update_user_season(user_id, season_type):
    conn = get_db_connection()
    conn.execute(
        'UPDATE users SET season_type = ?, updated_at = ? WHERE user_id = ?',
        (season_type, now_iso(), user_id)
    )
    conn.commit()
    conn.close()


def update_user_last_login(user_id):
    conn = get_db_connection()
    conn.execute(
        'UPDATE users SET last_login_at = ?, updated_at = ? WHERE user_id = ?',
        (now_iso(), now_iso(), user_id)
    )
    conn.commit()
    conn.close()


def update_user_profile(user_id, nickname=None, avatar=None):
    sets = []
    params = []
    if nickname is not None:
        sets.append('nickname = ?')
        params.append(str(nickname).strip())
    if avatar is not None:
        sets.append('avatar = ?')
        params.append(str(avatar).strip() or None)
    if not sets:
        return get_user_by_id(user_id)
    sets.append('updated_at = ?')
    params.append(now_iso())
    params.append(user_id)
    conn = get_db_connection()
    conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE user_id = ?", tuple(params))
    conn.commit()
    conn.close()
    return get_user_by_id(user_id)


def update_user_nickname(user_id, nickname):
    nickname = normalize_nickname(nickname)
    if not nickname:
        raise ValueError('nickname cannot be empty')
    return update_user_profile(user_id, nickname=nickname)


def update_user_avatar(user_id, avatar):
    avatar = str(avatar or '').strip()
    if not avatar:
        raise ValueError('avatar cannot be empty')
    return update_user_profile(user_id, avatar=avatar)


def upsert_user_preferences(user_id, preferred_scenes=None, preferred_categories=None, preferred_finishes=None,
                            budget_min=None, budget_max=None):
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO user_preferences (
            user_id, preferred_scenes_json, preferred_categories_json, preferred_finishes_json,
            budget_min, budget_max, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            preferred_scenes_json = excluded.preferred_scenes_json,
            preferred_categories_json = excluded.preferred_categories_json,
            preferred_finishes_json = excluded.preferred_finishes_json,
            budget_min = excluded.budget_min,
            budget_max = excluded.budget_max,
            updated_at = excluded.updated_at
        ''',
        (
            user_id,
            json.dumps(preferred_scenes or [], ensure_ascii=False),
            json.dumps(preferred_categories or [], ensure_ascii=False),
            json.dumps(preferred_finishes or [], ensure_ascii=False),
            float(budget_min or 0),
            float(budget_max or 0),
            now_iso(),
        )
    )
    conn.commit()
    conn.close()
    return get_user_preferences(user_id)


def get_user_preferences(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM user_preferences WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    result = _row_to_dict(row)
    if not result:
        return None
    result['preferred_scenes'] = _safe_json_text_to_list(result.get('preferred_scenes_json'))
    result['preferred_categories'] = _safe_json_text_to_list(result.get('preferred_categories_json'))
    result['preferred_finishes'] = _safe_json_text_to_list(result.get('preferred_finishes_json'))
    return result


def create_user_behavior_event(user_id, event_type, ref_type, ref_id=None, event_value=1, payload=None):
    event_id = f'evt_{uuid.uuid4().hex[:16]}'
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO user_behavior_events (event_id, user_id, event_type, ref_type, ref_id, event_value, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (event_id, user_id, event_type, ref_type, ref_id, float(event_value or 1), json.dumps(payload or {}, ensure_ascii=False), now_iso())
    )
    conn.commit()
    conn.close()
    return event_id


def list_user_behavior_events(user_id, limit=50):
    conn = get_db_connection()
    rows = conn.execute(
        'SELECT * FROM user_behavior_events WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
        (user_id, max(1, min(int(limit or 50), 200)))
    ).fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def get_personalized_recommendations(user_id, limit=10):
    prefs = get_user_preferences(user_id) or {}
    season = (get_user_by_id(user_id) or {}).get('season_type')
    category = (prefs.get('preferred_categories') or [None])[0]
    products = get_products(season=season, category=category, limit=limit)
    return products


def list_pair_recommendations(source_sku_id, limit=6):
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT ppr.pair_id, ppr.source_sku_id, ppr.target_sku_id, ppr.reason, ppr.score,
               spu.product_name AS name, spu.brand AS brand, spu.category AS category,
               sku.price AS price, sku.hex_color AS color_hex, spu.image_url AS image_url
        FROM product_pair_recommendations ppr
        JOIN product_sku sku ON sku.sku_id = ppr.target_sku_id
        JOIN product_spu spu ON spu.spu_id = sku.spu_id
        WHERE ppr.source_sku_id = ?
        ORDER BY ppr.score DESC, ppr.created_at DESC
        LIMIT ?
        ''',
        (source_sku_id, max(1, min(int(limit or 6), 50)))
    ).fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def get_membership_profile(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM membership_profiles WHERE user_id = ?', (user_id,)).fetchone()
    if not row:
        conn.execute('INSERT INTO membership_profiles (user_id, member_level, points, updated_at) VALUES (?, ?, ?, ?)', (user_id, 'basic', 0, now_iso()))
        conn.commit()
        row = conn.execute('SELECT * FROM membership_profiles WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def list_user_recent_history(user_id, limit=20):
    try:
        limit = int(limit)
    except Exception:
        limit = 20
    limit = max(1, min(limit, 100))

    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT
            up.group_id,
            up.stored_filename AS upload_filename,
            up.file_path AS upload_path,
            up.created_at AS upload_created_at,
            corr.stored_filename AS corrected_filename,
            corr.file_path AS corrected_path,
            corr.created_at AS corrected_created_at
        FROM user_images up
        LEFT JOIN user_images corr
            ON corr.group_id = up.group_id
           AND corr.user_id = up.user_id
           AND corr.image_type = 'corrected'
        WHERE up.user_id = ?
          AND up.image_type = 'upload'
        ORDER BY up.created_at DESC
        LIMIT ?
        ''',
        (user_id, limit)
    ).fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def list_user_images(user_id, limit=50):
    try:
        limit = int(limit)
    except Exception:
        limit = 50
    limit = max(1, min(limit, 200))

    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT *
        FROM user_images
        WHERE user_id = ?
          AND image_type IN ('upload', 'corrected')
          AND file_path NOT LIKE '%/avatar/%'
          AND file_path NOT LIKE '%\\avatar\\%'
        ORDER BY created_at DESC
        LIMIT ?
        ''',
        (user_id, limit)
    ).fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def get_user_image(image_id, user_id):
    conn = get_db_connection()
    row = conn.execute(
        'SELECT * FROM user_images WHERE image_id = ? AND user_id = ?',
        (image_id, user_id)
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


def delete_user_image(image_id, user_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM image_quality_reports WHERE image_id = ?', (image_id,))
    conn.execute('DELETE FROM pca_analysis_records WHERE image_id = ?', (image_id,))
    conn.execute('DELETE FROM makeup_session_steps WHERE input_image_id = ? OR output_image_id = ?', (image_id, image_id))
    cursor = conn.execute('DELETE FROM user_images WHERE image_id = ? AND user_id = ?', (image_id, user_id))
    conn.commit()
    deleted = int(cursor.rowcount or 0)
    conn.close()
    return deleted > 0


def create_user_image(user_id, image_type, stored_filename, file_path, origin_filename=None, group_id=None,
                      mime_type=None, file_size=0, width=None, height=None, source_session_id=None):
    image_id = f'img_{uuid.uuid4().hex[:16]}'
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO user_images (
            image_id, user_id, group_id, image_type, origin_filename, stored_filename,
            file_path, mime_type, file_size, width, height, source_session_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            image_id, user_id, group_id, image_type, origin_filename, stored_filename,
            file_path, mime_type, int(file_size or 0), width, height, source_session_id, now_iso()
        )
    )
    conn.commit()
    conn.close()
    return image_id


def get_user_image_by_filename(user_id, stored_filename):
    conn = get_db_connection()
    row = conn.execute(
        'SELECT * FROM user_images WHERE user_id = ? AND stored_filename = ? ORDER BY created_at DESC LIMIT 1',
        (user_id, stored_filename)
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


def get_latest_session_image(session_id, image_type=None):
    conn = get_db_connection()
    if image_type:
        row = conn.execute(
            'SELECT * FROM user_images WHERE source_session_id = ? AND image_type = ? ORDER BY created_at DESC LIMIT 1',
            (session_id, image_type)
        ).fetchone()
    else:
        row = conn.execute(
            'SELECT * FROM user_images WHERE source_session_id = ? ORDER BY created_at DESC LIMIT 1',
            (session_id,)
        ).fetchone()
    conn.close()
    return _row_to_dict(row)


def list_session_images(session_id):
    conn = get_db_connection()
    rows = conn.execute(
        'SELECT * FROM user_images WHERE source_session_id = ? ORDER BY created_at ASC',
        (session_id,)
    ).fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def update_user_image_storage(image_id, *, stored_filename, file_path):
    conn = get_db_connection()
    conn.execute(
        'UPDATE user_images SET stored_filename = ?, file_path = ? WHERE image_id = ?',
        (stored_filename, file_path, image_id)
    )
    conn.commit()
    conn.close()


def get_latest_user_image(user_id, image_type=None):
    conn = get_db_connection()
    try:
        if image_type:
            if image_type == 'upload':
                row = conn.execute(
                    "SELECT * FROM user_images WHERE user_id = ? AND image_type = ? AND file_path NOT LIKE '%/avatar/%' AND file_path NOT LIKE '%\\avatar\\%' ORDER BY created_at DESC LIMIT 1",
                    (user_id, image_type)
                ).fetchone()
            else:
                row = conn.execute(
                    'SELECT * FROM user_images WHERE user_id = ? AND image_type = ? ORDER BY created_at DESC LIMIT 1',
                    (user_id, image_type)
                ).fetchone()
        else:
            row = conn.execute(
                'SELECT * FROM user_images WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
                (user_id,)
            ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


def create_image_quality_report(image_id, has_face, blur_score=None, left_eye_score=None, right_eye_score=None,
                                mouth_score=None, occlusion_flag=False, raw_report=None):
    report_id = f'report_{uuid.uuid4().hex[:16]}'
    safe_raw_report = _to_json_safe(raw_report or {})
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO image_quality_reports (
            report_id, image_id, has_face, blur_score, left_eye_score, right_eye_score,
            mouth_score, occlusion_flag, raw_report_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            report_id, image_id, 1 if has_face else 0, blur_score, left_eye_score, right_eye_score,
            mouth_score, 1 if occlusion_flag else 0, json.dumps(safe_raw_report, ensure_ascii=False), now_iso()
        )
    )
    conn.commit()
    conn.close()
    return report_id


def create_pca_analysis_record(user_id, image_id, season_type, tone=None, confidence=None,
                               recommended_palette=None, avoid_palette=None, feature_vector=None,
                               model_version=None):
    analysis_id = f'pca_{uuid.uuid4().hex[:16]}'
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO pca_analysis_records (
            analysis_id, user_id, image_id, season_type, tone, confidence,
            recommended_palette_json, avoid_palette_json, feature_vector_json, model_version, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            analysis_id, user_id, image_id, season_type, tone, confidence,
            json.dumps(recommended_palette or [], ensure_ascii=False),
            json.dumps(avoid_palette or [], ensure_ascii=False),
            json.dumps(feature_vector or [], ensure_ascii=False),
            model_version, now_iso()
        )
    )
    conn.commit()
    conn.close()
    return analysis_id


def create_makeup_session_step(session_id, step_no, category, sku_id=None, input_image_id=None,
                               output_image_id=None, render_params=None):
    step_id = f'step_{uuid.uuid4().hex[:16]}'
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO makeup_session_steps (
            step_id, session_id, step_no, category, sku_id, input_image_id,
            output_image_id, render_params_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            step_id,
            session_id,
            int(step_no),
            category,
            sku_id,
            input_image_id,
            output_image_id,
            json.dumps(render_params or {}, ensure_ascii=False),
            now_iso(),
        )
    )
    conn.commit()
    conn.close()
    return step_id


def create_auth_token(user_id, expire_hours=24):
    token = f"session_token_{uuid.uuid4().hex}"
    with _DB_WRITE_LOCK:
        conn = get_db_connection()
        try:
            _cleanup_expired_tokens(conn)
            conn.execute('DELETE FROM auth_tokens WHERE user_id = ?', (user_id,))
            conn.execute(
                'INSERT OR REPLACE INTO auth_tokens (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)',
                (token, user_id, now_iso(), future_iso(expire_hours))
            )
            conn.commit()
        finally:
            conn.close()
    return token


def revoke_auth_token(token):
    with _DB_WRITE_LOCK:
        conn = get_db_connection()
        try:
            auth_token_columns = _get_column_names(conn, 'auth_tokens')
            if 'revoked_at' in auth_token_columns:
                conn.execute('UPDATE auth_tokens SET revoked_at = ? WHERE token = ?', (now_iso(), token))
            else:
                conn.execute('DELETE FROM auth_tokens WHERE token = ?', (token,))
            conn.commit()
        finally:
            conn.close()


def get_user_by_token(token):
    conn = get_db_connection()
    try:
        _cleanup_expired_tokens(conn)
        auth_token_columns = _get_column_names(conn, 'auth_tokens')
        where_clauses = ['t.token = ?']
        params = [token]
        if 'revoked_at' in auth_token_columns:
            where_clauses.append('t.revoked_at IS NULL')
        if 'expires_at' in auth_token_columns:
            where_clauses.append('(t.expires_at IS NULL OR t.expires_at > ?)')
            params.append(now_iso())
        row = conn.execute(
            f'''
            SELECT u.* FROM auth_tokens t
            JOIN users u ON u.user_id = t.user_id
            WHERE {' AND '.join(where_clauses)}
            ''',
            tuple(params)
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


def create_verification_code(target, biz_type, code, channel='mock', expires_minutes=5, meta=None):
    code_id = f'vc_{uuid.uuid4().hex[:12]}'
    with _DB_WRITE_LOCK:
        conn = get_db_connection()
        try:
            conn.execute(
                '''
                INSERT INTO verification_codes (code_id, target, code, biz_type, channel, status, expires_at, meta_json)
                VALUES (?, ?, ?, ?, ?, 'sent', ?, ?)
                ''',
                (
                    code_id,
                    str(target).strip(),
                    str(code).strip(),
                    str(biz_type).strip(),
                    str(channel).strip() or 'mock',
                    (datetime.utcnow() + timedelta(minutes=expires_minutes)).isoformat(timespec='seconds'),
                    json.dumps(meta or {}, ensure_ascii=False),
                )
            )
            conn.commit()
        finally:
            conn.close()
    return code_id


def get_latest_valid_verification_code(target, biz_type):
    conn = get_db_connection()
    row = conn.execute(
        '''
        SELECT * FROM verification_codes
        WHERE target = ? AND biz_type = ? AND status = 'sent' AND expires_at > ?
        ORDER BY created_at DESC
        LIMIT 1
        ''',
        (str(target).strip(), str(biz_type).strip(), now_iso())
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


def mark_verification_code_used(code_id, status='used'):
    conn = get_db_connection()
    verified_at = now_iso() if status in {'used', 'verified'} else None
    conn.execute(
        'UPDATE verification_codes SET status = ?, verified_at = COALESCE(?, verified_at) WHERE code_id = ?',
        (status, verified_at, code_id)
    )
    conn.commit()
    conn.close()


def check_verification_code(target, biz_type, code):
    row = get_latest_valid_verification_code(target, biz_type)
    if not row:
        return False, 'CODE_NOT_FOUND'
    if str(row.get('code') or '').strip() != str(code or '').strip():
        return False, 'CODE_INCORRECT'
    return True, row


def verify_code(target, biz_type, code):
    ok_flag, row = check_verification_code(target, biz_type, code)
    if not ok_flag:
        return ok_flag, row
    mark_verification_code_used(row['code_id'], status='verified')
    return True, row


def get_products(season=None, category=None, limit=30):
    try:
        limit = int(limit)
    except Exception:
        limit = 30
    limit = max(1, min(limit, 100))

    conn = get_db_connection()
    params = []
    sql = '''
        SELECT
            sku.sku_id AS p_id,
            sku.sku_id AS product_id,
            sku.spu_id AS product_group_id,
            spu.product_name AS name,
            spu.brand AS brand,
            spu.category AS category,
            spu.apply_area AS apply_area,
            sku.render_hex AS render_hex,
            sku.render_mode AS render_mode,
            sku.finish_type AS finish_type,
            sku.opacity AS opacity,
            sku.feather AS feather,
            sku.transparency_max AS transparency_max,
            sku.season_match AS season_tag,
            sku.hex_color AS color_hex,
            sku.price AS price,
            spu.image_url AS image_url,
            sku.mask_params AS mask_params,
            sku.render_params AS render_params,
            sku.stock AS stock,
            sku.shade_name AS shade_name,
            sku.source AS source
        FROM product_sku sku
        JOIN product_spu spu ON spu.spu_id = sku.spu_id
        WHERE sku.stock > 0 AND spu.status = 'active'
    '''

    if season:
        sql += ' AND sku.season_match = ?'
        params.append(season)
    if category:
        sql += ' AND spu.category = ?'
        params.append(category)

    sql += ' ORDER BY price ASC LIMIT ?'
    params.append(limit)

    rows = conn.execute(sql, tuple(params)).fetchall()

    if season and not rows:
        fallback_params = []
        fallback_sql = '''
            SELECT
                sku.sku_id AS p_id,
                sku.sku_id AS product_id,
                sku.spu_id AS product_group_id,
                spu.product_name AS name,
                spu.brand AS brand,
                spu.category AS category,
                spu.apply_area AS apply_area,
                sku.render_hex AS render_hex,
                sku.render_mode AS render_mode,
                sku.finish_type AS finish_type,
                sku.opacity AS opacity,
                sku.feather AS feather,
                sku.transparency_max AS transparency_max,
                sku.season_match AS season_tag,
                sku.hex_color AS color_hex,
                sku.price AS price,
                spu.image_url AS image_url,
                sku.mask_params AS mask_params,
                sku.render_params AS render_params,
                sku.stock AS stock,
                sku.shade_name AS shade_name,
                sku.source AS source
            FROM product_sku sku
            JOIN product_spu spu ON spu.spu_id = sku.spu_id
            WHERE sku.stock > 0 AND spu.status = 'active'
        '''
        if category:
            fallback_sql += ' AND spu.category = ?'
            fallback_params.append(category)
        fallback_sql += ' ORDER BY price ASC LIMIT ?'
        fallback_params.append(limit)
        rows = conn.execute(fallback_sql, tuple(fallback_params)).fetchall()

    conn.close()
    return _rows_to_dicts(rows)


def replace_excel_products(products):
    conn = get_db_connection()
    now = now_iso()
    conn.execute("DELETE FROM product_color_profiles WHERE source = 'excel'")
    conn.execute("DELETE FROM season_sku_map WHERE source = 'excel'")
    excel_skus = conn.execute("SELECT sku_id, spu_id FROM product_sku WHERE source = 'excel'").fetchall()
    excel_spu_ids = {row['spu_id'] for row in excel_skus}
    conn.execute("DELETE FROM product_sku WHERE source = 'excel'")
    for spu_id in excel_spu_ids:
        still_used = conn.execute("SELECT 1 FROM product_sku WHERE spu_id = ? LIMIT 1", (spu_id,)).fetchone()
        if not still_used:
            conn.execute("DELETE FROM product_spu WHERE spu_id = ?", (spu_id,))

    for product in products:
        sku_id = str(product['p_id'])
        spu_id = str(product.get('product_group_id') or sku_id)
        product_name = str(product.get('name') or sku_id)
        brand = product.get('brand')
        category = product.get('category')
        apply_area = product.get('apply_area')
        image_url = product.get('image_url')

        conn.execute(
            '''
            INSERT INTO product_spu (
                spu_id, brand, product_name, category, apply_area, image_url, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
            ON CONFLICT(spu_id) DO UPDATE SET
                brand = excluded.brand,
                product_name = excluded.product_name,
                category = excluded.category,
                apply_area = excluded.apply_area,
                image_url = excluded.image_url,
                status = 'active'
            ''',
            (spu_id, brand, product_name, category, apply_area, image_url, now)
        )
        conn.execute(
            '''
            INSERT INTO product_sku (
                sku_id, spu_id, shade_name, hex_color, render_hex, render_mode, finish_type,
                opacity, feather, transparency_max, season_match, price, stock, source,
                mask_params, render_params, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'excel', ?, ?, ?)
            ''',
            (
                sku_id, spu_id, product.get('name'), product.get('color_hex') or product['render_hex'], product['render_hex'], product.get('render_mode', 1), product.get('finish_type', 'semi-matte'),
                product.get('opacity', 0.6), product.get('feather', 8), product.get('transparency_max', 0.7),
                product.get('season_tag'), product.get('price', 0), product.get('stock', 100),
                json.dumps(product.get('mask_params') or {}, ensure_ascii=False),
                json.dumps(product.get('render_params') or {}, ensure_ascii=False),
                now
            )
        )
        for color in product.get('color_profiles') or []:
            conn.execute(
                '''
                INSERT INTO product_color_profiles (sku_id, shade_name, hex_color, color_role, source, created_at)
                VALUES (?, ?, ?, ?, 'excel', ?)
                ''',
                (
                    sku_id,
                    color.get('shade_name'),
                    color['hex_color'],
                    color.get('color_role', 'primary'),
                    now
                )
            )

    conn.commit()
    conn.close()


def replace_season_rules(season_rules):
    conn = get_db_connection()
    now = now_iso()
    conn.execute("DELETE FROM season_rules WHERE source = 'excel'")
    for rule in season_rules:
        conn.execute(
            '''
            INSERT OR REPLACE INTO season_rules (
                season_type, tone, lips_palette, cheeks_palette, brow_palette,
                avoid_palette, recommended_palette, source, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'excel', ?)
            ''',
            (
                rule['season_type'],
                rule.get('tone'),
                json.dumps(rule.get('lips_palette') or [], ensure_ascii=False),
                json.dumps(rule.get('cheeks_palette') or [], ensure_ascii=False),
                json.dumps(rule.get('brow_palette') or [], ensure_ascii=False),
                json.dumps(rule.get('avoid_palette') or [], ensure_ascii=False),
                json.dumps(rule.get('recommended_palette') or [], ensure_ascii=False),
                now
            )
        )
    conn.commit()
    conn.close()


def replace_season_sku_map(rows):
    conn = get_db_connection()
    now = now_iso()
    conn.execute("DELETE FROM season_sku_map WHERE source = 'excel'")
    for row in rows:
        conn.execute(
            '''
            INSERT INTO season_sku_map (season_type, sku_id, source, created_at)
            VALUES (?, ?, 'excel', ?)
            ''',
            (row['season_type'], row['product_id'], now)
        )
    conn.commit()
    conn.close()


def create_import_job(source_name, source_path=None, status='pending'):
    job_id = f'import_{uuid.uuid4().hex[:12]}'
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO import_jobs (job_id, source_name, source_path, status, summary_json)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (job_id, source_name, source_path, status, '{}')
    )
    conn.commit()
    conn.close()
    return job_id


def finish_import_job(job_id, status, summary=None, error_message=None):
    conn = get_db_connection()
    conn.execute(
        '''
        UPDATE import_jobs
        SET status = ?, summary_json = ?, error_message = ?, finished_at = ?
        WHERE job_id = ?
        ''',
        (status, json.dumps(summary or {}, ensure_ascii=False), error_message, now_iso(), job_id)
    )
    conn.commit()
    conn.close()


def get_season_rule(season_type):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM season_rules WHERE season_type = ?', (season_type,)).fetchone()
    conn.close()
    result = _row_to_dict(row)
    if not result:
        return None
    for field in ('lips_palette', 'cheeks_palette', 'brow_palette', 'avoid_palette', 'recommended_palette'):
        result[field] = _safe_json_text_to_list(result.get(field))
    return result


def _safe_json_text_to_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def get_product_by_id(product_id):
    conn = get_db_connection()
    row = conn.execute(
        '''
        SELECT
            sku.sku_id AS p_id,
            sku.sku_id AS product_id,
            sku.spu_id AS product_group_id,
            spu.product_name AS name,
            spu.brand AS brand,
            spu.category AS category,
            spu.apply_area AS apply_area,
            sku.render_hex AS render_hex,
            sku.render_mode AS render_mode,
            sku.finish_type AS finish_type,
            sku.opacity AS opacity,
            sku.feather AS feather,
            sku.transparency_max AS transparency_max,
            sku.season_match AS season_tag,
            sku.hex_color AS color_hex,
            sku.price AS price,
            spu.image_url AS image_url,
            sku.mask_params AS mask_params,
            sku.render_params AS render_params,
            sku.stock AS stock,
            sku.shade_name AS shade_name,
            sku.source AS source
        FROM product_sku sku
        JOIN product_spu spu ON spu.spu_id = sku.spu_id
        WHERE sku.sku_id = ?
        ''',
        (product_id,)
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


def get_cart_item(user_id, product_id):
    conn = get_db_connection()
    row = conn.execute(
        'SELECT * FROM cart_items WHERE user_id = ? AND sku_id = ?',
        (user_id, product_id)
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


def create_makeup_session(session_id, user_id, original_image, current_image, original_image_id=None):
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO makeup_sessions
        (session_id, user_id, original_image, current_image, applied_products, render_history, step, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            session_id,
            user_id,
            original_image,
            current_image,
            '[]',
            json.dumps([original_image], ensure_ascii=False),
            0,
            'active',
            now_iso(),
            now_iso()
        )
    )
    conn.commit()
    conn.close()


def get_makeup_session(session_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM makeup_sessions WHERE session_id = ?', (session_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def get_makeup_session_owner(session_id):
    conn = get_db_connection()
    row = conn.execute('SELECT user_id FROM makeup_sessions WHERE session_id = ?', (session_id,)).fetchone()
    conn.close()
    return row['user_id'] if row else None


def user_owns_image_via_session(user_id, filename):
    """兜底校验：图片文件名是否被该用户任一试妆会话引用。"""
    base = os.path.basename(filename or '')
    if not base:
        return False

    like_pattern = f'%{base}%'
    conn = get_db_connection()
    row = conn.execute(
        '''
        SELECT 1
        FROM makeup_sessions
        WHERE user_id = ?
          AND (
            original_image LIKE ?
            OR current_image LIKE ?
            OR render_history LIKE ?
          )
        LIMIT 1
        ''',
        (user_id, like_pattern, like_pattern, like_pattern)
    ).fetchone()
    conn.close()
    return row is not None


def update_makeup_session_state(session_id, current_image, applied_products, render_history, step, status='active'):
    conn = get_db_connection()
    conn.execute(
        '''
        UPDATE makeup_sessions
        SET current_image = ?, applied_products = ?, render_history = ?, step = ?, status = ?, updated_at = ?
        WHERE session_id = ?
        ''',
        (
            current_image,
            json.dumps(applied_products, ensure_ascii=False),
            json.dumps(render_history, ensure_ascii=False),
            step,
            status,
            now_iso(),
            session_id
        )
    )
    conn.commit()
    conn.close()


def list_expired_makeup_sessions(expire_before_iso: str):
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT * FROM makeup_sessions
        WHERE status = 'active' AND updated_at < ?
        ORDER BY updated_at ASC
        ''',
        (expire_before_iso,)
    ).fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def close_makeup_session(session_id):
    conn = get_db_connection()
    conn.execute(
        '''
        UPDATE makeup_sessions
        SET status = 'closed', updated_at = ?
        WHERE session_id = ?
        ''',
        (now_iso(), session_id)
    )
    conn.commit()
    conn.close()


def save_makeup_scheme(scheme_id, user_id, scheme_name, product_list, cover_image, season_type):
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO makeup_schemes
        (scheme_id, user_id, scheme_name, product_list, cover_image, season_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            scheme_id,
            user_id,
            scheme_name,
            json.dumps(product_list, ensure_ascii=False),
            cover_image,
            season_type,
            now_iso()
        )
    )

    for idx, item in enumerate(product_list or []):
        sku_id = str(item.get('product_id') or item.get('sku_id') or '').strip()
        category = str(item.get('category') or '').strip()
        if not sku_id:
            continue
        conn.execute(
            '''
            INSERT INTO makeup_plan_items (scheme_id, category, sku_id, sort_order, created_at)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (scheme_id, category, sku_id, idx, now_iso())
        )
    conn.commit()
    conn.close()


def list_makeup_schemes(user_id, limit=50):
    try:
        limit = int(limit)
    except Exception:
        limit = 50
    limit = max(1, min(limit, 200))

    conn = get_db_connection()
    rows = conn.execute(
        'SELECT * FROM makeup_schemes WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
        (user_id, limit)
    ).fetchall()
    items = conn.execute(
        '''
        SELECT mpi.scheme_id, mpi.category, mpi.sku_id, mpi.sort_order,
               spu.product_name AS name, spu.brand AS brand, sku.hex_color AS color_hex
        FROM makeup_plan_items mpi
        LEFT JOIN product_sku sku ON sku.sku_id = mpi.sku_id
        LEFT JOIN product_spu spu ON spu.spu_id = sku.spu_id
        WHERE mpi.scheme_id IN (
            SELECT scheme_id FROM makeup_schemes WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        )
        ORDER BY mpi.scheme_id, mpi.sort_order ASC
        ''',
        (user_id, limit)
    ).fetchall()
    conn.close()
    scheme_rows = _rows_to_dicts(rows)
    item_rows = _rows_to_dicts(items)
    grouped = {}
    for item in item_rows:
        grouped.setdefault(item['scheme_id'], []).append(item)
    for row in scheme_rows:
        row['items'] = grouped.get(row['scheme_id'], [])
    return scheme_rows


def get_makeup_scheme_detail(scheme_id, user_id):
    conn = get_db_connection()
    row = conn.execute(
        'SELECT * FROM makeup_schemes WHERE scheme_id = ? AND user_id = ?',
        (scheme_id, user_id)
    ).fetchone()
    if not row:
        conn.close()
        return None
    items = conn.execute(
        '''
        SELECT mpi.scheme_id, mpi.category, mpi.sku_id, mpi.sort_order,
               spu.product_name AS name, spu.brand AS brand, sku.hex_color AS color_hex,
               sku.render_hex AS render_hex, sku.price AS price, spu.image_url AS image_url
        FROM makeup_plan_items mpi
        LEFT JOIN product_sku sku ON sku.sku_id = mpi.sku_id
        LEFT JOIN product_spu spu ON spu.spu_id = sku.spu_id
        WHERE mpi.scheme_id = ?
        ORDER BY mpi.sort_order ASC
        ''',
        (scheme_id,)
    ).fetchall()
    conn.close()
    result = _row_to_dict(row)
    result['items'] = _rows_to_dicts(items)
    return result


def delete_makeup_scheme(scheme_id, user_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM makeup_plan_items WHERE scheme_id = ?', (scheme_id,))
    cursor = conn.execute(
        'DELETE FROM makeup_schemes WHERE scheme_id = ? AND user_id = ?',
        (scheme_id, user_id)
    )
    conn.commit()
    deleted = int(cursor.rowcount or 0)
    conn.close()
    return deleted > 0


def get_bundle_recommend(season, current_product=None):
    conn = get_db_connection()

    bundle_rows = conn.execute(
        '''
        SELECT
            b.bundle_id,
            b.season_type,
            b.bundle_name,
            b.description,
            bi.sku_id AS p_id,
            bi.sku_id AS product_id,
            bi.sort_order,
            spu.product_name AS name,
            spu.brand AS brand,
            spu.category AS category,
            sku.price AS price,
            sku.hex_color AS color_hex,
            spu.image_url AS image_url
        FROM bundle_recommendations b
        JOIN bundle_items bi ON bi.bundle_id = b.bundle_id
        JOIN product_sku sku ON sku.sku_id = bi.sku_id
        JOIN product_spu spu ON spu.spu_id = sku.spu_id
        WHERE b.season_type = ?
        ORDER BY b.bundle_id, bi.sort_order ASC
        ''',
        (season,)
    ).fetchall()

    if bundle_rows:
        grouped = {}
        for row in _rows_to_dicts(bundle_rows):
            bundle_id = row['bundle_id']
            grouped.setdefault(bundle_id, {
                'bundle_id': bundle_id,
                'season_type': row['season_type'],
                'bundle_name': row['bundle_name'],
                'description': row['description'],
                'items': []
            })
            grouped[bundle_id]['items'].append({
                'product_id': row['product_id'],
                'name': row['name'],
                'brand': row['brand'],
                'category': row['category'],
                'price': row['price'],
                'color_hex': row['color_hex'],
                'image_url': row['image_url'],
                'sort_order': row['sort_order'],
            })
        conn.close()
        first_bundle = list(grouped.values())[0]
        return first_bundle['items']

    rows = conn.execute(
        '''
        SELECT
            sku.sku_id AS p_id,
            sku.sku_id AS product_id,
            spu.product_name AS name,
            spu.brand AS brand,
            spu.category AS category,
            sku.price AS price,
            sku.hex_color AS color_hex,
            spu.image_url AS image_url
        FROM product_sku sku
        JOIN product_spu spu ON spu.spu_id = sku.spu_id
        WHERE sku.season_match = ?
          AND spu.category IN ('base', 'brow', 'lip')
          AND sku.stock > 0
          AND spu.status = 'active'
        ORDER BY
          CASE spu.category
            WHEN 'base' THEN 1
            WHEN 'brow' THEN 2
            WHEN 'lip' THEN 3
            ELSE 9
          END,
          sku.price ASC
        ''',
        (season,)
    ).fetchall()

    # 回退策略：该季型无SKU时，放宽到全部可用SKU，保证接口有稳定返回
    if not rows:
        rows = conn.execute(
            '''
            SELECT
                sku.sku_id AS p_id,
                sku.sku_id AS product_id,
                spu.product_name AS name,
                spu.brand AS brand,
                spu.category AS category,
                sku.price AS price,
                sku.hex_color AS color_hex,
                spu.image_url AS image_url
            FROM product_sku sku
            JOIN product_spu spu ON spu.spu_id = sku.spu_id
            WHERE spu.category IN ('base', 'brow', 'lip')
              AND sku.stock > 0
              AND spu.status = 'active'
            ORDER BY
              CASE spu.category
                WHEN 'base' THEN 1
                WHEN 'brow' THEN 2
                WHEN 'lip' THEN 3
                ELSE 9
              END,
              sku.price ASC
            '''
        ).fetchall()

    conn.close()
    candidates = _rows_to_dicts(rows)

    selected = []
    used_categories = set()

    for item in candidates:
        if current_product and item['p_id'] == current_product:
            continue
        if item['category'] in used_categories:
            continue
        selected.append(item)
        used_categories.add(item['category'])
        if len(selected) >= 3:
            break

    return selected


def get_bundle_by_id(bundle_id):
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT
            b.bundle_id,
            b.season_type,
            b.bundle_name,
            b.description,
            bi.sku_id AS product_id,
            bi.sort_order,
            spu.product_name AS name,
            spu.brand AS brand,
            spu.category AS category,
            sku.price AS price,
            sku.hex_color AS color_hex,
            spu.image_url AS image_url
        FROM bundle_recommendations b
        JOIN bundle_items bi ON bi.bundle_id = b.bundle_id
        JOIN product_sku sku ON sku.sku_id = bi.sku_id
        JOIN product_spu spu ON spu.spu_id = sku.spu_id
        WHERE b.bundle_id = ?
        ORDER BY bi.sort_order ASC
        ''',
        (bundle_id,)
    ).fetchall()
    conn.close()
    rows = _rows_to_dicts(rows)
    if not rows:
        return None
    first = rows[0]
    return {
        'bundle_id': first['bundle_id'],
        'season_type': first['season_type'],
        'bundle_name': first['bundle_name'],
        'description': first['description'],
        'items': rows,
    }


def add_to_cart(user_id, product_id, quantity=1):
    quantity = max(1, int(quantity or 1))
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO cart_items (cart_item_id, user_id, sku_id, quantity, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, sku_id)
        DO UPDATE SET quantity = cart_items.quantity + excluded.quantity, updated_at = excluded.updated_at
        ''',
        (f'cartitem_{uuid.uuid4().hex[:12]}', user_id, product_id, quantity, now_iso(), now_iso())
    )
    conn.commit()
    conn.close()


def update_cart_item(user_id, product_id, quantity):
    quantity = int(quantity or 0)
    conn = get_db_connection()
    if quantity <= 0:
        conn.execute('DELETE FROM cart_items WHERE user_id = ? AND sku_id = ?', (user_id, product_id))
    else:
        conn.execute(
            'UPDATE cart_items SET quantity = ?, updated_at = ? WHERE user_id = ? AND sku_id = ?',
            (quantity, now_iso(), user_id, product_id)
        )
    conn.commit()
    conn.close()


def remove_cart_item(user_id, product_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM cart_items WHERE user_id = ? AND sku_id = ?', (user_id, product_id))
    conn.commit()
    conn.close()


def clear_cart(user_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM cart_items WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def list_cart_items(user_id):
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT
            c.cart_item_id AS cart_id,
            c.user_id,
            c.sku_id AS product_id,
            c.quantity,
            c.created_at,
            spu.product_name AS name,
            spu.brand AS brand,
            spu.category AS category,
            sku.price AS price,
            spu.image_url AS image_url,
            sku.hex_color AS color_hex,
            sku.stock AS stock,
            sku.shade_name AS shade_name
        FROM cart_items c
        JOIN product_sku sku ON sku.sku_id = c.sku_id
        JOIN product_spu spu ON spu.spu_id = sku.spu_id
        WHERE c.user_id = ?
        ORDER BY c.created_at DESC
        ''',
        (user_id,)
    ).fetchall()
    conn.close()

    items = _rows_to_dicts(rows)
    for item in items:
        item['line_total'] = round(float(item.get('price') or 0) * int(item.get('quantity') or 0), 2)
    return items


# ============================
# 商品管理（管理侧）
# ============================

def admin_list_products(limit=200, category=None, keyword=None):
    try:
        limit = int(limit)
    except Exception:
        limit = 200
    limit = max(1, min(limit, 500))

    conn = get_db_connection()
    params = []
    sql = '''
        SELECT
            sku.sku_id AS p_id,
            sku.sku_id AS product_id,
            sku.spu_id AS product_group_id,
            spu.product_name AS name,
            spu.brand AS brand,
            spu.category AS category,
            spu.apply_area AS apply_area,
            sku.render_hex AS render_hex,
            sku.render_mode AS render_mode,
            sku.finish_type AS finish_type,
            sku.opacity AS opacity,
            sku.feather AS feather,
            sku.transparency_max AS transparency_max,
            sku.season_match AS season_tag,
            sku.hex_color AS color_hex,
            sku.price AS price,
            spu.image_url AS image_url,
            sku.mask_params AS mask_params,
            sku.render_params AS render_params,
            sku.stock AS stock,
            sku.shade_name AS shade_name,
            sku.source AS source,
            sku.created_at AS created_at
        FROM product_sku sku
        JOIN product_spu spu ON spu.spu_id = sku.spu_id
        WHERE 1=1
    '''

    if category:
        sql += ' AND category = ?'
        params.append(category)

    if keyword:
        kw = f'%{str(keyword).strip()}%'
        sql += ' AND (sku.sku_id LIKE ? OR spu.product_name LIKE ? OR spu.brand LIKE ?)'
        params.extend([kw, kw, kw])

    sql += ' ORDER BY created_at DESC LIMIT ?'
    params.append(limit)

    rows = conn.execute(sql, tuple(params)).fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def admin_create_product(payload):
    p_id = str(payload.get('p_id') or '').strip()
    product_group_id = str(payload.get('product_group_id') or '').strip() or p_id
    name = str(payload.get('name') or '').strip()
    brand = str(payload.get('brand') or '').strip() or 'ZHIF'
    category = str(payload.get('category') or '').strip()
    apply_area = str(payload.get('apply_area') or '').strip()
    render_hex = str(payload.get('render_hex') or '').strip()

    if not p_id or not name or not category or not apply_area or not render_hex:
        raise ValueError('MISSING_REQUIRED_FIELDS')

    render_mode = int(payload.get('render_mode', 0) or 0)
    finish_type = str(payload.get('finish_type') or '').strip() or 'semi-matte'
    opacity = float(payload.get('opacity', 0.6) or 0.6)
    feather = int(payload.get('feather', 8) or 8)
    transparency_max = float(payload.get('transparency_max', 0.7) or 0.7)
    season_tag = str(payload.get('season_tag') or '').strip() or None
    color_hex = str(payload.get('color_hex') or '').strip() or render_hex
    price = float(payload.get('price', 0) or 0)
    image_url = str(payload.get('image_url') or '').strip() or None
    mask_params = json.dumps(payload.get('mask_params') or {}, ensure_ascii=False)
    render_params = json.dumps(payload.get('render_params') or {}, ensure_ascii=False)
    stock = int(payload.get('stock', 0) or 0)

    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO product_spu (
            spu_id, brand, product_name, category, apply_area, image_url, status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
        ''',
        (product_group_id, brand, name, category, apply_area, image_url, now_iso())
    )
    conn.execute(
        '''
        INSERT INTO product_sku (
            sku_id, spu_id, shade_name, hex_color, render_hex, render_mode, finish_type,
            opacity, feather, transparency_max, season_match, price, stock, source,
            mask_params, render_params, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'admin', ?, ?, ?)
        ''',
        (
            p_id, product_group_id, name, color_hex, render_hex, render_mode, finish_type,
            opacity, feather, transparency_max, season_tag, price, stock, mask_params, render_params, now_iso()
        )
    )
    conn.commit()
    conn.close()
    return get_product_by_id(p_id)


def admin_update_product(p_id, payload):
    sku_allowed = {'render_hex', 'render_mode', 'finish_type', 'opacity', 'feather', 'transparency_max', 'season_tag', 'color_hex', 'price', 'mask_params', 'render_params', 'stock'}
    spu_allowed = {'product_group_id', 'name', 'brand', 'category', 'apply_area', 'image_url'}
    sku_sets = []
    sku_params = []
    spu_sets = []
    spu_params = []
    next_spu_id = None
    for k, v in (payload or {}).items():
        if k in {'mask_params', 'render_params'} and isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        if k == 'product_group_id':
            next_spu_id = v
            spu_sets.append('spu_id = ?')
            spu_params.append(v)
        elif k == 'name':
            spu_sets.append('product_name = ?')
            spu_params.append(v)
        elif k in {'brand', 'category', 'apply_area', 'image_url'}:
            spu_sets.append(f'{k} = ?')
            spu_params.append(v)
        elif k in sku_allowed:
            column = 'season_match' if k == 'season_tag' else ('hex_color' if k == 'color_hex' else k)
            sku_sets.append(f'{column} = ?')
            sku_params.append(v)

    if not sku_sets and not spu_sets:
        raise ValueError('NO_UPDATABLE_FIELDS')
    conn = get_db_connection()
    sku_row = conn.execute('SELECT spu_id FROM product_sku WHERE sku_id = ?', (p_id,)).fetchone()
    if not sku_row:
        conn.close()
        raise ValueError('PRODUCT_NOT_FOUND')
    current_spu_id = sku_row['spu_id']
    target_spu_id = next_spu_id or current_spu_id
    if spu_sets:
        spu_params.append(current_spu_id)
        conn.execute(f"UPDATE product_spu SET {', '.join(spu_sets)} WHERE spu_id = ?", tuple(spu_params))
    if sku_sets or target_spu_id != current_spu_id:
        if target_spu_id != current_spu_id:
            sku_sets.insert(0, 'spu_id = ?')
            sku_params.insert(0, target_spu_id)
        sku_params.append(p_id)
        conn.execute(f"UPDATE product_sku SET {', '.join(sku_sets)} WHERE sku_id = ?", tuple(sku_params))
    conn.commit()
    conn.close()
    return get_product_by_id(p_id)


def admin_delete_product(p_id):
    conn = get_db_connection()
    sku_row = conn.execute('SELECT spu_id FROM product_sku WHERE sku_id = ?', (p_id,)).fetchone()
    conn.execute('DELETE FROM product_sku WHERE sku_id = ?', (p_id,))
    if sku_row:
        still_used = conn.execute('SELECT 1 FROM product_sku WHERE spu_id = ? LIMIT 1', (sku_row['spu_id'],)).fetchone()
        if not still_used:
            conn.execute('DELETE FROM product_spu WHERE spu_id = ?', (sku_row['spu_id'],))
    conn.commit()
    conn.close()
