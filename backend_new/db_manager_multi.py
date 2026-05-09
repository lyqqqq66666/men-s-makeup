import json
import os
import uuid
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# 尝试导入MySQL驱动
try:
    import pymysql
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

# 导入数据库配置
from config.database import DATABASE_TYPE, MYSQL_CONFIG, SQLITE_DB_PATH

_DB_WRITE_LOCK = threading.Lock()


def _row_to_dict(row) -> Optional[Dict]:
    if row is None:
        return None
    if hasattr(row, '_mapping'):
        return dict(row._mapping)
    if isinstance(row, dict):
        return row
    return dict(row)


def _rows_to_dicts(rows) -> List[Dict]:
    result = []
    for row in rows:
        result.append(_row_to_dict(row))
    return result


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


def _safe_json_text_to_list(text: str) -> List:
    if not text:
        return []
    try:
        return json.loads(text)
    except Exception:
        return []


def get_db_connection():
    """获取数据库连接"""
    if DATABASE_TYPE == 'mysql' and MYSQL_AVAILABLE:
        conn = pymysql.connect(
            host=MYSQL_CONFIG['host'],
            port=MYSQL_CONFIG['port'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            database=MYSQL_CONFIG['database'],
            charset=MYSQL_CONFIG['charset'],
            connect_timeout=MYSQL_CONFIG['connect_timeout'],
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    else:
        import sqlite3
        conn = sqlite3.connect(SQLITE_DB_PATH, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('PRAGMA journal_mode = WAL')
        return conn


def _table_exists(conn, table_name: str) -> bool:
    if DATABASE_TYPE == 'mysql':
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s",
            (MYSQL_CONFIG['database'], table_name)
        )
        result = cursor.fetchone()
        cursor.close()
        return result['COUNT(*)'] > 0
    else:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (table_name,)
        ).fetchone()
        return row is not None


def _get_column_names(conn, table_name: str) -> set:
    if not _table_exists(conn, table_name):
        return set()
    
    if DATABASE_TYPE == 'mysql':
        cursor = conn.cursor()
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        cursor.close()
        return {col['Field'] for col in columns}
    else:
        cols = conn.execute(f'PRAGMA table_info({table_name})').fetchall()
        return {c[1] for c in cols}


def _ensure_column(conn, table_name: str, column_name: str, column_sql: str) -> None:
    col_names = _get_column_names(conn, table_name)
    if column_name not in col_names:
        conn.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_sql}')


def now_iso():
    return datetime.utcnow().isoformat(timespec='seconds')


def future_iso(hours=24):
    return (datetime.utcnow() + timedelta(hours=hours)).isoformat(timespec='seconds')


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == (password_hash or '')


def normalize_nickname(nickname: str) -> str:
    return (nickname or '').strip()


def default_nickname(phone=None) -> str:
    phone_text = (phone or '').strip()
    if len(phone_text) >= 4:
        return f'用户{phone_text[-4:]}'
    return f'用户{uuid.uuid4().hex[:6]}'


# ============================
# 初始化函数
# ============================

def init_db():
    """初始化数据库表结构"""
    os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)

    with _DB_WRITE_LOCK:
        conn = get_db_connection()
        try:
            _run_migrations(conn)
            conn.commit()
        finally:
            conn.close()
    print(f"数据库初始化完成，类型: {DATABASE_TYPE}")


def _run_migrations(conn):
    """执行数据库迁移"""
    # 创建用户表
    if not _table_exists(conn, 'users'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE users (
                    user_id VARCHAR(36) PRIMARY KEY,
                    phone VARCHAR(20),
                    password_hash VARCHAR(64),
                    nickname VARCHAR(100) NOT NULL,
                    avatar VARCHAR(500),
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    season_type VARCHAR(50),
                    last_login_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY idx_users_phone_unique (phone)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
        else:
            conn.execute('''
                CREATE TABLE users (
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
            ''')
            conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_unique ON users (phone) WHERE phone IS NOT NULL')

    # 创建认证令牌表
    if not _table_exists(conn, 'auth_tokens'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE auth_tokens (
                    token VARCHAR(100) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    token_type VARCHAR(20) NOT NULL DEFAULT 'bearer',
                    source VARCHAR(50) NOT NULL DEFAULT 'password',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME,
                    revoked_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            conn.execute('CREATE INDEX idx_auth_tokens_user_expires ON auth_tokens (user_id, expires_at)')
            conn.execute('CREATE INDEX idx_auth_tokens_expires ON auth_tokens (expires_at)')
        else:
            conn.execute('''
                CREATE TABLE auth_tokens (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_type TEXT NOT NULL DEFAULT 'bearer',
                    source TEXT NOT NULL DEFAULT 'password',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    revoked_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_expires ON auth_tokens (user_id, expires_at)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_auth_tokens_expires ON auth_tokens (expires_at)')

    # 创建用户图片表
    if not _table_exists(conn, 'user_images'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE user_images (
                    image_id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    group_id VARCHAR(50),
                    image_type VARCHAR(50) NOT NULL,
                    origin_filename VARCHAR(200),
                    stored_filename VARCHAR(200) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    mime_type VARCHAR(100),
                    file_size INT DEFAULT 0,
                    width INT,
                    height INT,
                    source_session_id VARCHAR(50),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            conn.execute('CREATE INDEX idx_user_images_user_type_created ON user_images (user_id, image_type, created_at DESC)')
        else:
            conn.execute('''
                CREATE TABLE user_images (
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
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_user_images_user_type_created ON user_images (user_id, image_type, created_at DESC)')

    # 创建产品SPU表
    if not _table_exists(conn, 'product_spu'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE product_spu (
                    spu_id VARCHAR(50) PRIMARY KEY,
                    brand VARCHAR(100),
                    product_name VARCHAR(200) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    apply_area VARCHAR(100) NOT NULL,
                    image_url VARCHAR(500),
                    status VARCHAR(20) NOT NULL DEFAULT 'active',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            conn.execute('CREATE INDEX idx_product_spu_category ON product_spu (category)')
        else:
            conn.execute('''
                CREATE TABLE product_spu (
                    spu_id TEXT PRIMARY KEY,
                    brand TEXT,
                    product_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    apply_area TEXT NOT NULL,
                    image_url TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_product_spu_category ON product_spu (category)')

    # 创建产品SKU表
    if not _table_exists(conn, 'product_sku'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE product_sku (
                    sku_id VARCHAR(50) PRIMARY KEY,
                    spu_id VARCHAR(50) NOT NULL,
                    shade_name VARCHAR(100),
                    hex_color VARCHAR(20) NOT NULL,
                    render_hex VARCHAR(20) NOT NULL,
                    render_mode INT DEFAULT 0,
                    finish_type VARCHAR(50),
                    opacity DECIMAL(3,2) DEFAULT 0.6,
                    feather INT DEFAULT 8,
                    transparency_max DECIMAL(3,2) DEFAULT 0.7,
                    season_match VARCHAR(50),
                    price DECIMAL(10,2) DEFAULT 0,
                    stock INT DEFAULT 0,
                    source VARCHAR(50) DEFAULT 'seed',
                    mask_params TEXT,
                    render_params TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (spu_id) REFERENCES product_spu(spu_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            conn.execute('CREATE INDEX idx_product_sku_spu_id ON product_sku (spu_id)')
            conn.execute('CREATE INDEX idx_product_sku_season_match ON product_sku (season_match)')
        else:
            conn.execute('''
                CREATE TABLE product_sku (
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
                    FOREIGN KEY (spu_id) REFERENCES product_spu(spu_id)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_product_sku_spu_id ON product_sku (spu_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_product_sku_season_match ON product_sku (season_match)')

    # 创建购物车表
    if not _table_exists(conn, 'cart_items'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE cart_items (
                    cart_item_id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    sku_id VARCHAR(50) NOT NULL,
                    quantity INT NOT NULL DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (sku_id) REFERENCES product_sku(sku_id),
                    UNIQUE KEY idx_cart_items_user_sku_unique (user_id, sku_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            conn.execute('CREATE INDEX idx_cart_items_user_id ON cart_items (user_id)')
        else:
            conn.execute('''
                CREATE TABLE cart_items (
                    cart_item_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    sku_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (sku_id) REFERENCES product_sku(sku_id)
                )
            ''')
            conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_cart_items_user_sku_unique ON cart_items (user_id, sku_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_cart_items_user_id ON cart_items (user_id)')

    # 创建验证码表
    if not _table_exists(conn, 'verification_codes'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE verification_codes (
                    code_id VARCHAR(50) PRIMARY KEY,
                    target VARCHAR(100) NOT NULL,
                    code VARCHAR(20) NOT NULL,
                    biz_type VARCHAR(50) NOT NULL,
                    channel VARCHAR(50) NOT NULL DEFAULT 'mock',
                    status VARCHAR(20) NOT NULL DEFAULT 'sent',
                    expires_at DATETIME NOT NULL,
                    verified_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    meta_json TEXT NOT NULL DEFAULT '{}'
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            conn.execute('CREATE INDEX idx_verification_codes_target_biz_status ON verification_codes (target, biz_type, status)')
        else:
            conn.execute('''
                CREATE TABLE verification_codes (
                    code_id TEXT PRIMARY KEY,
                    target TEXT NOT NULL,
                    code TEXT NOT NULL,
                    biz_type TEXT NOT NULL,
                    channel TEXT NOT NULL DEFAULT 'mock',
                    status TEXT NOT NULL DEFAULT 'sent',
                    expires_at TIMESTAMP NOT NULL,
                    verified_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    meta_json TEXT NOT NULL DEFAULT '{}'
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_verification_codes_target_biz_status ON verification_codes (target, biz_type, status)')

    # 创建PCA分析记录表
    if not _table_exists(conn, 'pca_analysis_records'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE pca_analysis_records (
                    analysis_id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    image_id VARCHAR(50) NOT NULL,
                    season_type VARCHAR(50) NOT NULL,
                    tone VARCHAR(50),
                    confidence DECIMAL(5,4),
                    recommended_palette_json TEXT NOT NULL DEFAULT '[]',
                    avoid_palette_json TEXT NOT NULL DEFAULT '[]',
                    feature_vector_json TEXT NOT NULL DEFAULT '[]',
                    model_version VARCHAR(50),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (image_id) REFERENCES user_images(image_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            conn.execute('CREATE INDEX idx_pca_analysis_user_created ON pca_analysis_records (user_id, created_at DESC)')
        else:
            conn.execute('''
                CREATE TABLE pca_analysis_records (
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
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (image_id) REFERENCES user_images(image_id)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_pca_analysis_user_created ON pca_analysis_records (user_id, created_at DESC)')

    # 创建化妆会话表
    if not _table_exists(conn, 'makeup_sessions'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE makeup_sessions (
                    session_id VARCHAR(50) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    session_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    scheme_id VARCHAR(50),
                    input_image_id VARCHAR(50),
                    final_image_id VARCHAR(50),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
        else:
            conn.execute('''
                CREATE TABLE makeup_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    scheme_id TEXT,
                    input_image_id TEXT,
                    final_image_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

    # 创建化妆会话步骤表
    if not _table_exists(conn, 'makeup_session_steps'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE makeup_session_steps (
                    step_id VARCHAR(50) PRIMARY KEY,
                    session_id VARCHAR(50) NOT NULL,
                    step_no INT NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    sku_id VARCHAR(50),
                    input_image_id VARCHAR(50),
                    output_image_id VARCHAR(50),
                    render_params_json TEXT NOT NULL DEFAULT '{}',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES makeup_sessions(session_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            conn.execute('CREATE INDEX idx_makeup_session_steps_session_no ON makeup_session_steps (session_id, step_no)')
        else:
            conn.execute('''
                CREATE TABLE makeup_session_steps (
                    step_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    step_no INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    sku_id TEXT,
                    input_image_id TEXT,
                    output_image_id TEXT,
                    render_params_json TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES makeup_sessions(session_id)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_makeup_session_steps_session_no ON makeup_session_steps (session_id, step_no)')

    # 创建用户偏好表
    if not _table_exists(conn, 'user_preferences'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE user_preferences (
                    user_id VARCHAR(36) PRIMARY KEY,
                    preferred_scenes_json TEXT NOT NULL DEFAULT '[]',
                    preferred_categories_json TEXT NOT NULL DEFAULT '[]',
                    preferred_finishes_json TEXT NOT NULL DEFAULT '[]',
                    budget_min DECIMAL(10,2) DEFAULT 0,
                    budget_max DECIMAL(10,2) DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
        else:
            conn.execute('''
                CREATE TABLE user_preferences (
                    user_id TEXT PRIMARY KEY,
                    preferred_scenes_json TEXT NOT NULL DEFAULT '[]',
                    preferred_categories_json TEXT NOT NULL DEFAULT '[]',
                    preferred_finishes_json TEXT NOT NULL DEFAULT '[]',
                    budget_min REAL DEFAULT 0,
                    budget_max REAL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

    # 创建会员资料表
    if not _table_exists(conn, 'membership_profiles'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE membership_profiles (
                    user_id VARCHAR(36) PRIMARY KEY,
                    member_level VARCHAR(20) NOT NULL DEFAULT 'basic',
                    points INT NOT NULL DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
        else:
            conn.execute('''
                CREATE TABLE membership_profiles (
                    user_id TEXT PRIMARY KEY,
                    member_level TEXT NOT NULL DEFAULT 'basic',
                    points INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')

    # 创建化妆方案表
    if not _table_exists(conn, 'makeup_schemes'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE makeup_schemes (
                    scheme_id VARCHAR(50) PRIMARY KEY,
                    scheme_name VARCHAR(100) NOT NULL,
                    season_type VARCHAR(50),
                    scene_tag VARCHAR(50),
                    recommend_reason TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
        else:
            conn.execute('''
                CREATE TABLE makeup_schemes (
                    scheme_id TEXT PRIMARY KEY,
                    scheme_name TEXT NOT NULL,
                    season_type TEXT,
                    scene_tag TEXT,
                    recommend_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    # 创建方案项目表
    if not _table_exists(conn, 'makeup_plan_items'):
        if DATABASE_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE makeup_plan_items (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    scheme_id VARCHAR(50) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    sku_id VARCHAR(50) NOT NULL,
                    sort_order INT NOT NULL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scheme_id) REFERENCES makeup_schemes(scheme_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            ''')
            conn.execute('CREATE INDEX idx_makeup_plan_items_scheme ON makeup_plan_items (scheme_id, sort_order)')
        else:
            conn.execute('''
                CREATE TABLE makeup_plan_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scheme_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    sku_id TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (scheme_id) REFERENCES makeup_schemes(scheme_id)
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_makeup_plan_items_scheme ON makeup_plan_items (scheme_id, sort_order)')

    # 确保所有必要的列都存在
    _ensure_column(conn, 'users', 'password_hash', 'password_hash TEXT')
    _ensure_column(conn, 'users', 'phone', 'phone TEXT')
    _ensure_column(conn, 'users', 'status', "status TEXT DEFAULT 'active'")
    _ensure_column(conn, 'users', 'last_login_at', 'last_login_at TIMESTAMP')
    _ensure_column(conn, 'users', 'role', "role TEXT DEFAULT 'user'")


def _cleanup_expired_tokens(conn):
    now = now_iso()
    conn.execute('DELETE FROM auth_tokens WHERE expires_at IS NOT NULL AND expires_at <= ?', (now,))


# ============================
# 用户相关操作
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
    if DATABASE_TYPE == 'mysql':
        conn.execute(
            '''
            INSERT INTO users (user_id, phone, password_hash, nickname, avatar, role, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, 'user', 'active', %s, %s)
            ''',
            (user_id, phone, pwd_hash, nickname, avatar, now, now)
        )
    else:
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


# ============================
# 认证相关操作
# ============================

def create_auth_token(user_id, expire_hours=24):
    token = f"session_token_{uuid.uuid4().hex}"
    with _DB_WRITE_LOCK:
        conn = get_db_connection()
        try:
            _cleanup_expired_tokens(conn)
            conn.execute('DELETE FROM auth_tokens WHERE user_id = ?', (user_id,))
            conn.execute(
                'INSERT INTO auth_tokens (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)',
                (token, user_id, now_iso(), future_iso(expire_hours))
            )
            conn.commit()
        finally:
            conn.close()
    return token


def get_user_by_token(token):
    conn = get_db_connection()
    try:
        _cleanup_expired_tokens(conn)
        row = conn.execute(
            '''
            SELECT u.* FROM auth_tokens t
            JOIN users u ON u.user_id = t.user_id
            WHERE t.token = ? AND (t.revoked_at IS NULL) AND (t.expires_at IS NULL OR t.expires_at > ?)
            ''',
            (token, now_iso())
        ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row)


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


# ============================
# 验证码相关操作
# ============================

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


def verify_code(target, biz_type, code):
    row = get_latest_valid_verification_code(target, biz_type)
    if not row:
        return False, 'CODE_NOT_FOUND'
    if str(row.get('code') or '').strip() != str(code or '').strip():
        return False, 'CODE_INCORRECT'
    mark_verification_code_used(row['code_id'], status='verified')
    return True, row


# ============================
# 用户图片相关操作
# ============================

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


def get_user_image(image_id, user_id):
    conn = get_db_connection()
    row = conn.execute(
        'SELECT * FROM user_images WHERE image_id = ? AND user_id = ?',
        (image_id, user_id)
    ).fetchone()
    conn.close()
    return _row_to_dict(row)


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


def delete_user_image(image_id, user_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM user_images WHERE image_id = ? AND user_id = ?', (image_id, user_id))
    conn.commit()
    deleted = conn.affected_rows if DATABASE_TYPE == 'mysql' else conn.execute('SELECT changes()').fetchone()[0]
    conn.close()
    return deleted > 0


# ============================
# 产品相关操作
# ============================

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
        fallback_params = []
        if category:
            fallback_sql += ' AND spu.category = ?'
            fallback_params.append(category)
        fallback_sql += ' ORDER BY price ASC LIMIT ?'
        fallback_params.append(limit)
        rows = conn.execute(fallback_sql, tuple(fallback_params)).fetchall()

    conn.close()
    return _rows_to_dicts(rows)


# ============================
# 购物车相关操作
# ============================

def add_to_cart(user_id, sku_id, quantity=1):
    cart_item_id = f'cart_{uuid.uuid4().hex[:16]}'
    conn = get_db_connection()
    
    existing = conn.execute(
        'SELECT cart_item_id, quantity FROM cart_items WHERE user_id = ? AND sku_id = ?',
        (user_id, sku_id)
    ).fetchone()
    
    if existing:
        new_quantity = existing['quantity'] + quantity
        conn.execute(
            'UPDATE cart_items SET quantity = ?, updated_at = ? WHERE cart_item_id = ?',
            (new_quantity, now_iso(), existing['cart_item_id'])
        )
    else:
        conn.execute(
            '''
            INSERT INTO cart_items (cart_item_id, user_id, sku_id, quantity, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (cart_item_id, user_id, sku_id, quantity, now_iso(), now_iso())
        )
    
    conn.commit()
    conn.close()
    return cart_item_id


def get_cart_items(user_id):
    conn = get_db_connection()
    rows = conn.execute(
        '''
        SELECT ci.*, sku.price, sku.shade_name, spu.product_name, spu.image_url
        FROM cart_items ci
        JOIN product_sku sku ON sku.sku_id = ci.sku_id
        JOIN product_spu spu ON spu.spu_id = sku.spu_id
        WHERE ci.user_id = ?
        ORDER BY ci.created_at DESC
        ''',
        (user_id,)
    ).fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def remove_from_cart(user_id, cart_item_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM cart_items WHERE cart_item_id = ? AND user_id = ?', (cart_item_id, user_id))
    conn.commit()
    conn.close()


# ============================
# PCA分析相关操作
# ============================

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


# ============================
# 用户偏好相关操作
# ============================

def upsert_user_preferences(user_id, preferred_scenes=None, preferred_categories=None, preferred_finishes=None,
                            budget_min=None, budget_max=None):
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO user_preferences (
            user_id, preferred_scenes_json, preferred_categories_json, preferred_finishes_json,
            budget_min, budget_max, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE
            preferred_scenes_json = VALUES(preferred_scenes_json),
            preferred_categories_json = VALUES(preferred_categories_json),
            preferred_finishes_json = VALUES(preferred_finishes_json),
            budget_min = VALUES(budget_min),
            budget_max = VALUES(budget_max),
            updated_at = VALUES(updated_at)
        ''' if DATABASE_TYPE == 'mysql' else '''
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


# ============================
# 会员相关操作
# ============================

def get_membership_profile(user_id):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM membership_profiles WHERE user_id = ?', (user_id,)).fetchone()
    if not row:
        conn.execute('INSERT INTO membership_profiles (user_id, member_level, points, updated_at) VALUES (?, ?, ?, ?)', (user_id, 'basic', 0, now_iso()))
        conn.commit()
        row = conn.execute('SELECT * FROM membership_profiles WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


# ============================
# 化妆会话相关操作
# ============================

def create_makeup_session(user_id, session_type='makeup', scheme_id=None):
    session_id = f'sess_{uuid.uuid4().hex[:16]}'
    conn = get_db_connection()
    conn.execute(
        '''
        INSERT INTO makeup_sessions (session_id, user_id, session_type, status, scheme_id, created_at, updated_at)
        VALUES (?, ?, ?, 'pending', ?, ?, ?)
        ''',
        (session_id, user_id, session_type, scheme_id, now_iso(), now_iso())
    )
    conn.commit()
    conn.close()
    return session_id


def update_makeup_session(session_id, status=None, final_image_id=None):
    sets = []
    params = []
    if status is not None:
        sets.append('status = ?')
        params.append(status)
    if final_image_id is not None:
        sets.append('final_image_id = ?')
        params.append(final_image_id)
    if not sets:
        return
    sets.append('updated_at = ?')
    params.append(now_iso())
    params.append(session_id)
    
    conn = get_db_connection()
    conn.execute(f"UPDATE makeup_sessions SET {', '.join(sets)} WHERE session_id = ?", tuple(params))
    conn.commit()
    conn.close()


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