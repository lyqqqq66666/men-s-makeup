PRAGMA foreign_keys = ON;

-- ============================
-- 全量重建脚本（不是增量初始化脚本）
-- 每次执行都会清空当前新版/旧版表结构后重建
-- ============================
DROP TABLE IF EXISTS bundle_items;
DROP TABLE IF EXISTS bundle_recommendations;
DROP TABLE IF EXISTS product_pair_recommendations;
DROP TABLE IF EXISTS makeup_plan_items;
DROP TABLE IF EXISTS makeup_schemes;
DROP TABLE IF EXISTS makeup_session_steps;
DROP TABLE IF EXISTS makeup_sessions;
DROP TABLE IF EXISTS cart_items;
DROP TABLE IF EXISTS product_color_profiles;
DROP TABLE IF EXISTS season_sku_map;
DROP TABLE IF EXISTS product_sku;
DROP TABLE IF EXISTS product_spu;
DROP TABLE IF EXISTS pca_analysis_records;
DROP TABLE IF EXISTS image_quality_reports;
DROP TABLE IF EXISTS user_images;
DROP TABLE IF EXISTS user_behavior_events;
DROP TABLE IF EXISTS user_preferences;
DROP TABLE IF EXISTS membership_profiles;
DROP TABLE IF EXISTS auth_tokens;
DROP TABLE IF EXISTS verification_codes;
DROP TABLE IF EXISTS import_jobs;
DROP TABLE IF EXISTS season_rules;
DROP TABLE IF EXISTS users;

DROP TABLE IF EXISTS makeup_images;
DROP TABLE IF EXISTS debug_images;
DROP TABLE IF EXISTS corrected_images;
DROP TABLE IF EXISTS uploads;
DROP TABLE IF EXISTS cart;
DROP TABLE IF EXISTS products;

DROP INDEX IF EXISTS idx_uploads_group_id_unique;
DROP INDEX IF EXISTS idx_uploads_created_at;
DROP INDEX IF EXISTS idx_debug_images_group_created;
DROP INDEX IF EXISTS idx_corrected_images_group_created;
DROP INDEX IF EXISTS idx_makeup_images_group_created;
DROP INDEX IF EXISTS idx_products_season_category;
DROP INDEX IF EXISTS idx_products_category;
DROP INDEX IF EXISTS idx_products_category_price;
DROP INDEX IF EXISTS idx_products_season_price;
DROP INDEX IF EXISTS idx_cart_user_product_unique;
DROP INDEX IF EXISTS idx_cart_user_id;
DROP INDEX IF EXISTS idx_product_spu_category;
DROP INDEX IF EXISTS idx_product_sku_spu_id;
DROP INDEX IF EXISTS idx_product_sku_season_match;
DROP INDEX IF EXISTS idx_product_color_profiles_sku_id;
DROP INDEX IF EXISTS idx_product_color_profiles_hex_color;
DROP INDEX IF EXISTS idx_season_sku_map_season_sku;
DROP INDEX IF EXISTS idx_season_sku_map_unique;
DROP INDEX IF EXISTS idx_cart_items_user_sku_unique;
DROP INDEX IF EXISTS idx_cart_items_user_id;
DROP INDEX IF EXISTS idx_makeup_sessions_user_id;
DROP INDEX IF EXISTS idx_makeup_sessions_user_status_updated;
DROP INDEX IF EXISTS idx_makeup_session_steps_session_no;
DROP INDEX IF EXISTS idx_makeup_schemes_user_id;
DROP INDEX IF EXISTS idx_makeup_schemes_user_created;
DROP INDEX IF EXISTS idx_makeup_plan_items_scheme;
DROP INDEX IF EXISTS idx_user_behavior_user_type_created;
DROP INDEX IF EXISTS idx_product_pair_source_score;
DROP INDEX IF EXISTS idx_product_pair_unique;
DROP INDEX IF EXISTS idx_auth_tokens_user_expires;
DROP INDEX IF EXISTS idx_auth_tokens_expires;
DROP INDEX IF EXISTS idx_verification_codes_target_biz_status;
DROP INDEX IF EXISTS idx_user_images_user_type_created;
DROP INDEX IF EXISTS idx_pca_analysis_user_created;
DROP INDEX IF EXISTS idx_users_phone_unique;
DROP TRIGGER IF EXISTS trg_users_updated_at;
DROP TRIGGER IF EXISTS trg_cart_items_updated_at;
DROP TRIGGER IF EXISTS trg_makeup_sessions_updated_at;
DROP TRIGGER IF EXISTS trg_user_preferences_updated_at;
DROP TRIGGER IF EXISTS trg_membership_profiles_updated_at;

-- ============================
-- 正式新版主模型：认证 / 图片 / PCA / 商品 / 推荐 / 试妆 / 购物车
-- ============================
CREATE TABLE IF NOT EXISTS users (
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
 );

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
);

CREATE TABLE IF NOT EXISTS auth_tokens (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_type TEXT NOT NULL DEFAULT 'bearer' CHECK (token_type IN ('bearer')),
    source TEXT NOT NULL DEFAULT 'password' CHECK (source IN ('password', 'code', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    revoked_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS user_images (
    image_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    group_id TEXT,
    image_type TEXT NOT NULL CHECK (image_type IN ('upload', 'corrected', 'pca_input', 'pca_result', 'session_original', 'session_render', 'plan_cover', 'debug')),
    origin_filename TEXT,
    stored_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    mime_type TEXT,
    file_size INTEGER DEFAULT 0,
    width INTEGER,
    height INTEGER,
    source_session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE
);

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
    FOREIGN KEY (image_id) REFERENCES user_images (image_id) ON DELETE CASCADE ON UPDATE CASCADE
);

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
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (image_id) REFERENCES user_images (image_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS product_spu (
    spu_id TEXT PRIMARY KEY,
    brand TEXT,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('base', 'brow', 'eye', 'contour', 'lip')),
    apply_area TEXT NOT NULL CHECK (apply_area IN ('skin', 'brow', 'eyes', 'lips', 'cheeks')),
    image_url TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_sku (
    sku_id TEXT PRIMARY KEY,
    spu_id TEXT NOT NULL,
    shade_name TEXT,
    hex_color TEXT NOT NULL,
    render_hex TEXT NOT NULL,
    render_mode INTEGER DEFAULT 0 CHECK (render_mode IN (0, 1)),
    finish_type TEXT,
    opacity REAL DEFAULT 0.6 CHECK (opacity >= 0 AND opacity <= 1),
    feather INTEGER DEFAULT 8 CHECK (feather >= 0 AND feather <= 100),
    transparency_max REAL DEFAULT 0.7 CHECK (transparency_max >= 0 AND transparency_max <= 1),
    season_match TEXT,
    price REAL DEFAULT 0 CHECK (price >= 0),
    stock INTEGER DEFAULT 0 CHECK (stock >= 0),
    source TEXT DEFAULT 'seed',
    mask_params TEXT,
    render_params TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (spu_id) REFERENCES product_spu (spu_id) ON DELETE CASCADE ON UPDATE CASCADE
);

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
);

CREATE TABLE IF NOT EXISTS season_sku_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_type TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    source TEXT DEFAULT 'excel',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sku_id) REFERENCES product_sku (sku_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS product_color_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku_id TEXT NOT NULL,
    shade_name TEXT,
    hex_color TEXT NOT NULL,
    color_role TEXT NOT NULL DEFAULT 'primary' CHECK (color_role IN ('primary', 'palette', 'render', 'avoid')),
    source TEXT DEFAULT 'excel',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sku_id) REFERENCES product_sku (sku_id)
);

CREATE TABLE IF NOT EXISTS import_jobs (
    job_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_path TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'success', 'failed')),
    summary_json TEXT NOT NULL DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cart_items (
    cart_item_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (sku_id) REFERENCES product_sku (sku_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS makeup_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    original_image TEXT NOT NULL,
    current_image TEXT NOT NULL,
    applied_products TEXT NOT NULL DEFAULT '[]',
    render_history TEXT NOT NULL DEFAULT '[]',
    step INTEGER NOT NULL DEFAULT 0 CHECK (step >= 0),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'closed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE
);

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
    FOREIGN KEY (session_id) REFERENCES makeup_sessions (session_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (sku_id) REFERENCES product_sku (sku_id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (input_image_id) REFERENCES user_images (image_id) ON DELETE SET NULL ON UPDATE CASCADE,
    FOREIGN KEY (output_image_id) REFERENCES user_images (image_id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS makeup_schemes (
    scheme_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    scheme_name TEXT NOT NULL,
    product_list TEXT NOT NULL,
    cover_image TEXT,
    season_type TEXT,
    scene_tag TEXT,
    recommend_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS makeup_plan_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheme_id TEXT NOT NULL,
    category TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scheme_id) REFERENCES makeup_schemes (scheme_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (sku_id) REFERENCES product_sku (sku_id) ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS bundle_recommendations (
    bundle_id TEXT PRIMARY KEY,
    season_type TEXT NOT NULL,
    bundle_name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bundle_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bundle_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (bundle_id) REFERENCES bundle_recommendations (bundle_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (sku_id) REFERENCES product_sku (sku_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    preferred_scenes_json TEXT NOT NULL DEFAULT '[]',
    preferred_categories_json TEXT NOT NULL DEFAULT '[]',
    preferred_finishes_json TEXT NOT NULL DEFAULT '[]',
    budget_min REAL DEFAULT 0,
    budget_max REAL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS user_behavior_events (
    event_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    ref_type TEXT NOT NULL,
    ref_id TEXT,
    event_value REAL DEFAULT 1,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS product_pair_recommendations (
    pair_id TEXT PRIMARY KEY,
    source_sku_id TEXT NOT NULL,
    target_sku_id TEXT NOT NULL,
    reason TEXT,
    score REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_sku_id) REFERENCES product_sku (sku_id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (target_sku_id) REFERENCES product_sku (sku_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS membership_profiles (
    user_id TEXT PRIMARY KEY,
    member_level TEXT NOT NULL DEFAULT 'basic',
    points INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_product_spu_category ON product_spu (category);
CREATE INDEX IF NOT EXISTS idx_product_sku_spu_id ON product_sku (spu_id);
CREATE INDEX IF NOT EXISTS idx_product_sku_season_match ON product_sku (season_match);
CREATE INDEX IF NOT EXISTS idx_product_color_profiles_sku_id ON product_color_profiles (sku_id);
CREATE INDEX IF NOT EXISTS idx_product_color_profiles_hex_color ON product_color_profiles (hex_color);
CREATE INDEX IF NOT EXISTS idx_season_sku_map_season_sku ON season_sku_map (season_type, sku_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_season_sku_map_unique ON season_sku_map (season_type, sku_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_cart_items_user_sku_unique ON cart_items (user_id, sku_id);
CREATE INDEX IF NOT EXISTS idx_cart_items_user_id ON cart_items (user_id);

CREATE INDEX IF NOT EXISTS idx_makeup_sessions_user_id ON makeup_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_makeup_sessions_user_status_updated ON makeup_sessions (user_id, status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_makeup_session_steps_session_no ON makeup_session_steps (session_id, step_no);
CREATE INDEX IF NOT EXISTS idx_makeup_schemes_user_id ON makeup_schemes (user_id);
CREATE INDEX IF NOT EXISTS idx_makeup_schemes_user_created ON makeup_schemes (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_makeup_plan_items_scheme ON makeup_plan_items (scheme_id, sort_order);
CREATE INDEX IF NOT EXISTS idx_user_behavior_user_type_created ON user_behavior_events (user_id, event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_product_pair_source_score ON product_pair_recommendations (source_sku_id, score DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_product_pair_unique ON product_pair_recommendations (source_sku_id, target_sku_id);

CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_expires ON auth_tokens (user_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_expires ON auth_tokens (expires_at);
CREATE INDEX IF NOT EXISTS idx_verification_codes_target_biz_status ON verification_codes (target, biz_type, status);
CREATE INDEX IF NOT EXISTS idx_user_images_user_type_created ON user_images (user_id, image_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pca_analysis_user_created ON pca_analysis_records (user_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_unique ON users (phone) WHERE phone IS NOT NULL;

CREATE TRIGGER IF NOT EXISTS trg_users_updated_at
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = OLD.user_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_cart_items_updated_at
AFTER UPDATE ON cart_items
FOR EACH ROW
BEGIN
    UPDATE cart_items SET updated_at = CURRENT_TIMESTAMP WHERE cart_item_id = OLD.cart_item_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_makeup_sessions_updated_at
AFTER UPDATE ON makeup_sessions
FOR EACH ROW
BEGIN
    UPDATE makeup_sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = OLD.session_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_user_preferences_updated_at
AFTER UPDATE ON user_preferences
FOR EACH ROW
BEGIN
    UPDATE user_preferences SET updated_at = CURRENT_TIMESTAMP WHERE user_id = OLD.user_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_membership_profiles_updated_at
AFTER UPDATE ON membership_profiles
FOR EACH ROW
BEGIN
    UPDATE membership_profiles SET updated_at = CURRENT_TIMESTAMP WHERE user_id = OLD.user_id;
END;

-- ============================
-- 初始化商品主数据（SPU / SKU）
-- ============================
INSERT OR IGNORE INTO product_spu (spu_id, brand, product_name, category, apply_area, image_url, status) VALUES
('base_001', 'ZHIF', '自然轻薄底妆系列', 'base', 'skin', '/images/styles/natural.png', 'active'),
('base_002', 'ZHIF', '冷调柔雾底妆系列', 'base', 'skin', '/images/styles/business.png', 'active'),
('brow_001', 'ZHIF', '暖调自然眉笔系列', 'brow', 'brow', '/images/styles/textured.png', 'active'),
('brow_002', 'ZHIF', '冷调塑形眉笔系列', 'brow', 'brow', '/images/styles/business.png', 'active'),
('contour_001', 'ZHIF', '暖调轮廓修容系列', 'contour', 'cheeks', '/images/styles/textured.png', 'active'),
('contour_002', 'ZHIF', '冷调阴影修容系列', 'contour', 'cheeks', '/images/styles/business.png', 'active'),
('lip_001', 'ZHIF', '暖调唇妆系列', 'lip', 'lips', '/images/styles/natural.png', 'active'),
('lip_002', 'ZHIF', '冷调唇妆系列', 'lip', 'lips', '/images/styles/idol.png', 'active'),
('eye_001', 'ZHIF', '暖调眼妆系列', 'eye', 'eyes', '/images/styles/business.png', 'active'),
('eye_002', 'ZHIF', '冷调眼妆系列', 'eye', 'eyes', '/images/styles/idol.png', 'active');

INSERT OR IGNORE INTO product_sku (
    sku_id, spu_id, shade_name, hex_color, render_hex, render_mode, finish_type,
    opacity, feather, transparency_max, season_match, price, stock, source, mask_params, render_params
) VALUES
('base_001_natural', 'base_001', '自然轻薄底妆', '#D8B89B', '#D8B89B', 0, 'semi-matte', 0.35, 15, 0.45, 'Warm Autumn', 169.00, 100, 'seed', '{}', '{}'),
('base_001_warm', 'base_001', '暖调清透底妆', '#CFA789', '#CFA789', 0, 'semi-matte', 0.38, 16, 0.48, 'Warm Autumn', 169.00, 100, 'seed', '{}', '{}'),
('base_002_cool', 'base_002', '冷调柔雾底妆', '#D2B5A1', '#D2B5A1', 0, 'matte', 0.34, 15, 0.44, 'Cool Winter', 179.00, 100, 'seed', '{}', '{}'),
('base_002_ivory', 'base_002', '象牙冷调底妆', '#E1C9B5', '#E1C9B5', 0, 'matte', 0.33, 14, 0.43, 'Cool Winter', 179.00, 100, 'seed', '{}', '{}'),
('brow_001_brown', 'brow_001', '深棕立体眉笔', '#5A3A28', '#5A3A28', 1, 'matte', 0.62, 6, 0.68, 'Warm Autumn', 89.00, 120, 'seed', '{}', '{}'),
('brow_001_softbrown', 'brow_001', '浅棕自然眉笔', '#6F4A35', '#6F4A35', 1, 'matte', 0.56, 6, 0.66, 'Warm Autumn', 89.00, 120, 'seed', '{}', '{}'),
('brow_002_gray', 'brow_002', '冷灰塑形眉笔', '#4C4C4C', '#4C4C4C', 1, 'matte', 0.58, 6, 0.65, 'Cool Winter', 99.00, 120, 'seed', '{}', '{}'),
('brow_002_ash', 'brow_002', '烟灰冷调眉笔', '#5B5B63', '#5B5B63', 1, 'matte', 0.57, 6, 0.65, 'Cool Winter', 99.00, 120, 'seed', '{}', '{}'),
('contour_001_warm', 'contour_001', '暖调轮廓修容', '#8B5A3C', '#8B5A3C', 1, 'matte', 0.34, 18, 0.40, 'Warm Autumn', 129.00, 100, 'seed', '{}', '{}'),
('contour_001_toffee', 'contour_001', '太妃轮廓修容', '#9A6A4A', '#9A6A4A', 1, 'matte', 0.32, 18, 0.40, 'Warm Autumn', 129.00, 100, 'seed', '{}', '{}'),
('contour_002_cool', 'contour_002', '冷调阴影修容', '#7A6260', '#7A6260', 1, 'matte', 0.30, 18, 0.38, 'Cool Winter', 139.00, 100, 'seed', '{}', '{}'),
('contour_002_graytaupe', 'contour_002', '灰棕阴影修容', '#6A5A58', '#6A5A58', 1, 'matte', 0.30, 18, 0.38, 'Cool Winter', 139.00, 100, 'seed', '{}', '{}'),
('lip_001_coral', 'lip_001', '珊瑚暖调唇膏', '#C86A52', '#C86A52', 1, 'semi-matte', 0.48, 10, 0.58, 'Warm Autumn', 159.00, 150, 'seed', '{}', '{}'),
('lip_001_amber', 'lip_001', '琥珀暖棕唇膏', '#A35A3A', '#A35A3A', 1, 'semi-matte', 0.50, 10, 0.60, 'Warm Autumn', 159.00, 150, 'seed', '{}', '{}'),
('lip_001_peach', 'lip_001', '蜜桃裸调唇膏', '#D08A73', '#D08A73', 1, 'glossy', 0.44, 10, 0.56, 'Warm Autumn', 159.00, 150, 'seed', '{}', '{}'),
('lip_002_rose', 'lip_002', '冷玫瑰唇膏', '#A14C63', '#A14C63', 1, 'semi-matte', 0.47, 10, 0.58, 'Cool Winter', 169.00, 150, 'seed', '{}', '{}'),
('lip_002_plum', 'lip_002', '梅子冷调唇膏', '#7E3F52', '#7E3F52', 1, 'matte', 0.50, 10, 0.60, 'Cool Winter', 169.00, 150, 'seed', '{}', '{}'),
('lip_002_wine', 'lip_002', '酒红冷调唇膏', '#6E3143', '#6E3143', 1, 'matte', 0.52, 10, 0.62, 'Cool Winter', 169.00, 150, 'seed', '{}', '{}'),
('eye_001_earth', 'eye_001', '大地暖调眼妆', '#8A6B56', '#8A6B56', 0, 'matte', 0.20, 12, 0.30, 'Warm Autumn', 139.00, 80, 'seed', '{}', '{}'),
('eye_001_bronze', 'eye_001', '古铜暖调眼妆', '#7A5742', '#7A5742', 0, 'semi-matte', 0.22, 12, 0.32, 'Warm Autumn', 139.00, 80, 'seed', '{}', '{}'),
('eye_002_taupe', 'eye_002', '灰棕冷调眼妆', '#6D6266', '#6D6266', 0, 'matte', 0.20, 12, 0.30, 'Cool Winter', 149.00, 80, 'seed', '{}', '{}'),
('eye_002_steel', 'eye_002', '钢灰冷调眼妆', '#5D5E69', '#5D5E69', 0, 'matte', 0.21, 12, 0.31, 'Cool Winter', 149.00, 80, 'seed', '{}', '{}');
