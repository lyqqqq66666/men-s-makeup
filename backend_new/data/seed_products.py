# -*- coding: utf-8 -*-
"""
智颜方正 - 商品种子数据生成脚本
生成 150+ 男士化妆品 SKU 数据，覆盖 5 大品类
"""

import json
import os
import sys
import uuid

# 将 backend_new 目录加入 path 以便导入 db_manager
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import db_manager

SOURCE_TAG = 'seed_v2'

# ============================================================
# SPU 数据定义
# ============================================================
# 每个 SPU 代表一个商品系列，包含品牌、系列名、品类、上妆区域
SPU_DATA = [
    # ---- 底妆 (base) ----
    {"spu_id": "SPU_BASE_001", "brand": "杰威尔", "product_name": "净透持妆粉底液", "category": "base", "apply_area": "skin"},
    {"spu_id": "SPU_BASE_002", "brand": "欧莱雅男士", "product_name": "男士控油哑光粉底", "category": "base", "apply_area": "skin"},
    {"spu_id": "SPU_BASE_003", "brand": "曼秀雷敦男士", "product_name": "轻薄透气BB霜", "category": "base", "apply_area": "skin"},
    {"spu_id": "SPU_BASE_004", "brand": "兰蔻", "product_name": "男士精华气垫粉底", "category": "base", "apply_area": "skin"},
    {"spu_id": "SPU_BASE_005", "brand": "MAC", "product_name": "Studio Fix 男士粉底液", "category": "base", "apply_area": "skin"},
    {"spu_id": "SPU_BASE_006", "brand": "科颜氏男士", "product_name": "男士修饰隔离霜", "category": "base", "apply_area": "skin"},
    {"spu_id": "SPU_BASE_007", "brand": "碧欧泉男士", "product_name": "男士净透遮瑕膏", "category": "base", "apply_area": "skin"},
    {"spu_id": "SPU_BASE_008", "brand": "香奈儿男士", "product_name": "男士轻盈定妆散粉", "category": "base", "apply_area": "skin"},
    {"spu_id": "SPU_BASE_009", "brand": "杰威尔", "product_name": "男士素颜霜", "category": "base", "apply_area": "skin"},
    {"spu_id": "SPU_BASE_010", "brand": "欧莱雅男士", "product_name": "男士遮瑕笔", "category": "base", "apply_area": "skin"},

    # ---- 眉部 (brow) ----
    {"spu_id": "SPU_BROW_001", "brand": "杰威尔", "product_name": "立体塑形眉笔", "category": "brow", "apply_area": "brow"},
    {"spu_id": "SPU_BROW_002", "brand": "MAC", "product_name": "男士自动眉笔", "category": "brow", "apply_area": "brow"},
    {"spu_id": "SPU_BROW_003", "brand": "欧莱雅男士", "product_name": "男士三合一眉笔", "category": "brow", "apply_area": "brow"},
    {"spu_id": "SPU_BROW_004", "brand": "兰蔻", "product_name": "男士眉粉盒", "category": "brow", "apply_area": "brow"},
    {"spu_id": "SPU_BROW_005", "brand": "曼秀雷敦男士", "product_name": "自然眉笔", "category": "brow", "apply_area": "brow"},
    {"spu_id": "SPU_BROW_006", "brand": "科颜氏男士", "product_name": "男士眉胶", "category": "brow", "apply_area": "brow"},
    {"spu_id": "SPU_BROW_007", "brand": "杰威尔", "product_name": "男士眉部染眉膏", "category": "brow", "apply_area": "brow"},
    {"spu_id": "SPU_BROW_008", "brand": "香奈儿男士", "product_name": "男士精致眉笔", "category": "brow", "apply_area": "brow"},

    # ---- 眼部 (eye) ----
    {"spu_id": "SPU_EYE_001", "brand": "MAC", "product_name": "男士大地色眼影盘", "category": "eye", "apply_area": "eyes"},
    {"spu_id": "SPU_EYE_002", "brand": "杰威尔", "product_name": "男士单色眼影", "category": "eye", "apply_area": "eyes"},
    {"spu_id": "SPU_EYE_003", "brand": "兰蔻", "product_name": "男士深邃眼线笔", "category": "eye", "apply_area": "eyes"},
    {"spu_id": "SPU_EYE_004", "brand": "欧莱雅男士", "product_name": "男士眼影笔", "category": "eye", "apply_area": "eyes"},
    {"spu_id": "SPU_EYE_005", "brand": "香奈儿男士", "product_name": "男士四色眼影盘", "category": "eye", "apply_area": "eyes"},
    {"spu_id": "SPU_EYE_006", "brand": "科颜氏男士", "product_name": "男士眼部提亮笔", "category": "eye", "apply_area": "eyes"},
    {"spu_id": "SPU_EYE_007", "brand": "碧欧泉男士", "product_name": "男士眼影膏", "category": "eye", "apply_area": "eyes"},
    {"spu_id": "SPU_EYE_008", "brand": "杰威尔", "product_name": "男士内眼线笔", "category": "eye", "apply_area": "eyes"},

    # ---- 唇部 (lip) ----
    {"spu_id": "SPU_LIP_001", "brand": "杰威尔", "product_name": "男士润色唇膏", "category": "lip", "apply_area": "lips"},
    {"spu_id": "SPU_LIP_002", "brand": "MAC", "product_name": "男士哑光唇膏", "category": "lip", "apply_area": "lips"},
    {"spu_id": "SPU_LIP_003", "brand": "曼秀雷敦男士", "product_name": "男士保湿润唇膏", "category": "lip", "apply_area": "lips"},
    {"spu_id": "SPU_LIP_004", "brand": "欧莱雅男士", "product_name": "男士唇彩笔", "category": "lip", "apply_area": "lips"},
    {"spu_id": "SPU_LIP_005", "brand": "兰蔻", "product_name": "男士柔润唇膏", "category": "lip", "apply_area": "lips"},
    {"spu_id": "SPU_LIP_006", "brand": "香奈儿男士", "product_name": "男士丝绒唇釉", "category": "lip", "apply_area": "lips"},
    {"spu_id": "SPU_LIP_007", "brand": "科颜氏男士", "product_name": "男士自然唇色笔", "category": "lip", "apply_area": "lips"},
    {"spu_id": "SPU_LIP_008", "brand": "碧欧泉男士", "product_name": "男士护色唇膏", "category": "lip", "apply_area": "lips"},

    # ---- 修容 (contour) ----
    {"spu_id": "SPU_CONT_001", "brand": "MAC", "product_name": "男士修容盘", "category": "contour", "apply_area": "cheeks"},
    {"spu_id": "SPU_CONT_002", "brand": "杰威尔", "product_name": "男士立体修容粉", "category": "contour", "apply_area": "cheeks"},
    {"spu_id": "SPU_CONT_003", "brand": "欧莱雅男士", "product_name": "男士修容棒", "category": "contour", "apply_area": "cheeks"},
    {"spu_id": "SPU_CONT_004", "brand": "兰蔻", "product_name": "男士阴影膏", "category": "contour", "apply_area": "cheeks"},
    {"spu_id": "SPU_CONT_005", "brand": "香奈儿男士", "product_name": "男士双色修容盘", "category": "contour", "apply_area": "cheeks"},
    {"spu_id": "SPU_CONT_006", "brand": "科颜氏男士", "product_name": "男士古铜粉", "category": "contour", "apply_area": "cheeks"},
    {"spu_id": "SPU_CONT_007", "brand": "碧欧泉男士", "product_name": "男士高光修容笔", "category": "contour", "apply_area": "cheeks"},
    {"spu_id": "SPU_CONT_008", "brand": "曼秀雷敦男士", "product_name": "男士修容笔", "category": "contour", "apply_area": "cheeks"},
]

# ============================================================
# SKU 数据定义
# ============================================================
# 字段说明:
#   sku_id: SKU唯一标识
#   spu_id: 关联SPU
#   shade_name: 色号名称
#   hex_color: 原始色值
#   render_hex: 渲染色值
#   render_mode: 渲染模式 (0=标准, 1=增强)
#   finish_type: 妆效类型
#   opacity: 透明度 (0-1)
#   feather: 羽化值 (0-100)
#   season_match: 匹配季型
#   price: 价格
#   source: 数据来源

SKU_DATA = [
    # ===================== 底妆 (base) - 35 SKU =====================
    # SPU_BASE_001: 杰威尔 净透持妆粉底液
    {"sku_id": "SKU_BASE_001", "spu_id": "SPU_BASE_001", "shade_name": "象牙白", "hex_color": "#F5E6D3", "render_hex": "#F0DFC8", "render_mode": 0, "finish_type": "semi-matte", "opacity": 0.45, "feather": 20, "season_match": "Cool Winter", "price": 189.0},
    {"sku_id": "SKU_BASE_002", "spu_id": "SPU_BASE_001", "shade_name": "自然色", "hex_color": "#E8D4C4", "render_hex": "#E0C8B4", "render_mode": 0, "finish_type": "semi-matte", "opacity": 0.45, "feather": 20, "season_match": "Warm Spring", "price": 189.0},
    {"sku_id": "SKU_BASE_003", "spu_id": "SPU_BASE_001", "shade_name": "小麦色", "hex_color": "#D4B896", "render_hex": "#C8A880", "render_mode": 0, "finish_type": "semi-matte", "opacity": 0.45, "feather": 20, "season_match": "Warm Autumn", "price": 189.0},
    {"sku_id": "SKU_BASE_004", "spu_id": "SPU_BASE_001", "shade_name": "焦糖色", "hex_color": "#B89468", "render_hex": "#A88458", "render_mode": 0, "finish_type": "semi-matte", "opacity": 0.45, "feather": 20, "season_match": "Deep Autumn", "price": 189.0},

    # SPU_BASE_002: 欧莱雅男士 控油哑光粉底
    {"sku_id": "SKU_BASE_005", "spu_id": "SPU_BASE_002", "shade_name": "亮白", "hex_color": "#F5E6D3", "render_hex": "#F0DFC8", "render_mode": 0, "finish_type": "matte", "opacity": 0.5, "feather": 18, "season_match": "Cool Winter", "price": 159.0},
    {"sku_id": "SKU_BASE_006", "spu_id": "SPU_BASE_002", "shade_name": "自然", "hex_color": "#E8D4C4", "render_hex": "#E0C8B4", "render_mode": 0, "finish_type": "matte", "opacity": 0.5, "feather": 18, "season_match": "Warm Spring", "price": 159.0},
    {"sku_id": "SKU_BASE_007", "spu_id": "SPU_BASE_002", "shade_name": "深色", "hex_color": "#C8A882", "render_hex": "#BC9A72", "render_mode": 0, "finish_type": "matte", "opacity": 0.5, "feather": 18, "season_match": "Warm Autumn", "price": 159.0},

    # SPU_BASE_003: 曼秀雷敦男士 轻薄透气BB霜
    {"sku_id": "SKU_BASE_008", "spu_id": "SPU_BASE_003", "shade_name": "自然白皙", "hex_color": "#F0DFC8", "render_hex": "#E8D4BC", "render_mode": 0, "finish_type": "natural", "opacity": 0.35, "feather": 25, "season_match": "Cool Spring", "price": 79.0},
    {"sku_id": "SKU_BASE_009", "spu_id": "SPU_BASE_003", "shade_name": "自然健康", "hex_color": "#DFC5A8", "render_hex": "#D5B898", "render_mode": 0, "finish_type": "natural", "opacity": 0.35, "feather": 25, "season_match": "Warm Spring", "price": 79.0},
    {"sku_id": "SKU_BASE_010", "spu_id": "SPU_BASE_003", "shade_name": "小麦健康", "hex_color": "#C8A882", "render_hex": "#BC9A72", "render_mode": 0, "finish_type": "natural", "opacity": 0.35, "feather": 25, "season_match": "Warm Autumn", "price": 79.0},

    # SPU_BASE_004: 兰蔻 男士精华气垫粉底
    {"sku_id": "SKU_BASE_011", "spu_id": "SPU_BASE_004", "shade_name": "明亮白", "hex_color": "#F5E6D3", "render_hex": "#F0DFC8", "render_mode": 1, "finish_type": "dewy", "opacity": 0.4, "feather": 22, "season_match": "Cool Winter", "price": 499.0},
    {"sku_id": "SKU_BASE_012", "spu_id": "SPU_BASE_004", "shade_name": "自然色", "hex_color": "#E8D4C4", "render_hex": "#E0C8B4", "render_mode": 1, "finish_type": "dewy", "opacity": 0.4, "feather": 22, "season_match": "Warm Spring", "price": 499.0},
    {"sku_id": "SKU_BASE_013", "spu_id": "SPU_BASE_004", "shade_name": "小麦色", "hex_color": "#D4B896", "render_hex": "#C8A880", "render_mode": 1, "finish_type": "dewy", "opacity": 0.4, "feather": 22, "season_match": "Warm Autumn", "price": 499.0},
    {"sku_id": "SKU_BASE_014", "spu_id": "SPU_BASE_004", "shade_name": "深色", "hex_color": "#B89468", "render_hex": "#A88458", "render_mode": 1, "finish_type": "dewy", "opacity": 0.4, "feather": 22, "season_match": "Deep Autumn", "price": 499.0},

    # SPU_BASE_005: MAC Studio Fix 男士粉底液
    {"sku_id": "SKU_BASE_015", "spu_id": "SPU_BASE_005", "shade_name": "N1 白皙", "hex_color": "#F5E6D3", "render_hex": "#F0DFC8", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 15, "season_match": "Cool Winter", "price": 299.0},
    {"sku_id": "SKU_BASE_016", "spu_id": "SPU_BASE_005", "shade_name": "N3 自然", "hex_color": "#E8D4C4", "render_hex": "#E0C8B4", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 15, "season_match": "Warm Spring", "price": 299.0},
    {"sku_id": "SKU_BASE_017", "spu_id": "SPU_BASE_005", "shade_name": "N5 小麦", "hex_color": "#D4B896", "render_hex": "#C8A880", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 15, "season_match": "Warm Autumn", "price": 299.0},
    {"sku_id": "SKU_BASE_018", "spu_id": "SPU_BASE_005", "shade_name": "N7 深色", "hex_color": "#B89468", "render_hex": "#A88458", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 15, "season_match": "Deep Winter", "price": 299.0},
    {"sku_id": "SKU_BASE_019", "spu_id": "SPU_BASE_005", "shade_name": "N8 浓缩", "hex_color": "#8B7355", "render_hex": "#7A6248", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 15, "season_match": "Deep Winter", "price": 299.0},

    # SPU_BASE_006: 科颜氏男士 修饰隔离霜
    {"sku_id": "SKU_BASE_020", "spu_id": "SPU_BASE_006", "shade_name": "紫色隔离", "hex_color": "#E8D8E8", "render_hex": "#E0D0E0", "render_mode": 0, "finish_type": "natural", "opacity": 0.3, "feather": 28, "season_match": "Cool Summer", "price": 259.0},
    {"sku_id": "SKU_BASE_021", "spu_id": "SPU_BASE_006", "shade_name": "绿色隔离", "hex_color": "#D8E8D0", "render_hex": "#D0E0C8", "render_mode": 0, "finish_type": "natural", "opacity": 0.3, "feather": 28, "season_match": "Warm Spring", "price": 259.0},
    {"sku_id": "SKU_BASE_022", "spu_id": "SPU_BASE_006", "shade_name": "肤色隔离", "hex_color": "#E8D4C4", "render_hex": "#E0C8B4", "render_mode": 0, "finish_type": "natural", "opacity": 0.3, "feather": 28, "season_match": "Warm Autumn", "price": 259.0},

    # SPU_BASE_007: 碧欧泉男士 净透遮瑕膏
    {"sku_id": "SKU_BASE_023", "spu_id": "SPU_BASE_007", "shade_name": "浅色遮瑕", "hex_color": "#F0DFC8", "render_hex": "#E8D4BC", "render_mode": 1, "finish_type": "semi-matte", "opacity": 0.7, "feather": 10, "season_match": "Cool Winter", "price": 349.0},
    {"sku_id": "SKU_BASE_024", "spu_id": "SPU_BASE_007", "shade_name": "自然遮瑕", "hex_color": "#DFC5A8", "render_hex": "#D5B898", "render_mode": 1, "finish_type": "semi-matte", "opacity": 0.7, "feather": 10, "season_match": "Warm Spring", "price": 349.0},
    {"sku_id": "SKU_BASE_025", "spu_id": "SPU_BASE_007", "shade_name": "深色遮瑕", "hex_color": "#C8A882", "render_hex": "#BC9A72", "render_mode": 1, "finish_type": "semi-matte", "opacity": 0.7, "feather": 10, "season_match": "Warm Autumn", "price": 349.0},

    # SPU_BASE_008: 香奈儿男士 轻盈定妆散粉
    {"sku_id": "SKU_BASE_026", "spu_id": "SPU_BASE_008", "shade_name": "透明定妆", "hex_color": "#F5F0EB", "render_hex": "#F0EBE5", "render_mode": 0, "finish_type": "matte", "opacity": 0.2, "feather": 30, "season_match": "Cool Winter", "price": 599.0},
    {"sku_id": "SKU_BASE_027", "spu_id": "SPU_BASE_008", "shade_name": "自然定妆", "hex_color": "#E8D4C4", "render_hex": "#E0C8B4", "render_mode": 0, "finish_type": "matte", "opacity": 0.2, "feather": 30, "season_match": "Warm Spring", "price": 599.0},

    # SPU_BASE_009: 杰威尔 男士素颜霜
    {"sku_id": "SKU_BASE_028", "spu_id": "SPU_BASE_009", "shade_name": "自然白", "hex_color": "#F0DFC8", "render_hex": "#EAD4BC", "render_mode": 0, "finish_type": "natural", "opacity": 0.3, "feather": 25, "season_match": "Cool Spring", "price": 129.0},
    {"sku_id": "SKU_BASE_029", "spu_id": "SPU_BASE_009", "shade_name": "自然色", "hex_color": "#E8D4C4", "render_hex": "#E0C8B4", "render_mode": 0, "finish_type": "natural", "opacity": 0.3, "feather": 25, "season_match": "Warm Spring", "price": 129.0},

    # SPU_BASE_010: 欧莱雅男士 遮瑕笔
    {"sku_id": "SKU_BASE_030", "spu_id": "SPU_BASE_010", "shade_name": "浅色", "hex_color": "#F0DFC8", "render_hex": "#E8D4BC", "render_mode": 1, "finish_type": "semi-matte", "opacity": 0.65, "feather": 8, "season_match": "Cool Winter", "price": 99.0},
    {"sku_id": "SKU_BASE_031", "spu_id": "SPU_BASE_010", "shade_name": "自然色", "hex_color": "#DFC5A8", "render_hex": "#D5B898", "render_mode": 1, "finish_type": "semi-matte", "opacity": 0.65, "feather": 8, "season_match": "Warm Spring", "price": 99.0},
    {"sku_id": "SKU_BASE_032", "spu_id": "SPU_BASE_010", "shade_name": "深色", "hex_color": "#C8A882", "render_hex": "#BC9A72", "render_mode": 1, "finish_type": "semi-matte", "opacity": 0.65, "feather": 8, "season_match": "Warm Autumn", "price": 99.0},

    # ===================== 眉部 (brow) - 32 SKU =====================
    # SPU_BROW_001: 杰威尔 立体塑形眉笔
    {"sku_id": "SKU_BROW_001", "spu_id": "SPU_BROW_001", "shade_name": "自然黑", "hex_color": "#2C2C2C", "render_hex": "#383838", "render_mode": 0, "finish_type": "matte", "opacity": 0.7, "feather": 5, "season_match": "Cool Winter", "price": 109.0},
    {"sku_id": "SKU_BROW_002", "spu_id": "SPU_BROW_001", "shade_name": "深棕", "hex_color": "#4A3728", "render_hex": "#5A4738", "render_mode": 0, "finish_type": "matte", "opacity": 0.7, "feather": 5, "season_match": "Warm Autumn", "price": 109.0},
    {"sku_id": "SKU_BROW_003", "spu_id": "SPU_BROW_001", "shade_name": "灰棕", "hex_color": "#5A5A5A", "render_hex": "#6A6A6A", "render_mode": 0, "finish_type": "matte", "opacity": 0.7, "feather": 5, "season_match": "Cool Spring", "price": 109.0},
    {"sku_id": "SKU_BROW_004", "spu_id": "SPU_BROW_001", "shade_name": "暖棕", "hex_color": "#6B4226", "render_hex": "#7B5236", "render_mode": 0, "finish_type": "matte", "opacity": 0.7, "feather": 5, "season_match": "Warm Spring", "price": 109.0},

    # SPU_BROW_002: MAC 男士自动眉笔
    {"sku_id": "SKU_BROW_005", "spu_id": "SPU_BROW_002", "shade_name": "炭黑", "hex_color": "#333333", "render_hex": "#404040", "render_mode": 0, "finish_type": "matte", "opacity": 0.75, "feather": 4, "season_match": "Deep Winter", "price": 199.0},
    {"sku_id": "SKU_BROW_006", "spu_id": "SPU_BROW_002", "shade_name": "深棕", "hex_color": "#4A3728", "render_hex": "#5A4738", "render_mode": 0, "finish_type": "matte", "opacity": 0.75, "feather": 4, "season_match": "Warm Autumn", "price": 199.0},
    {"sku_id": "SKU_BROW_007", "spu_id": "SPU_BROW_002", "shade_name": "灰棕", "hex_color": "#5A5A5A", "render_hex": "#6A6A6A", "render_mode": 0, "finish_type": "matte", "opacity": 0.75, "feather": 4, "season_match": "Cool Summer", "price": 199.0},
    {"sku_id": "SKU_BROW_008", "spu_id": "SPU_BROW_002", "shade_name": "石墨灰", "hex_color": "#4A4A4A", "render_hex": "#5A5A5A", "render_mode": 0, "finish_type": "matte", "opacity": 0.75, "feather": 4, "season_match": "Cool Winter", "price": 199.0},

    # SPU_BROW_003: 欧莱雅男士 三合一眉笔
    {"sku_id": "SKU_BROW_009", "spu_id": "SPU_BROW_003", "shade_name": "自然黑", "hex_color": "#2C2C2C", "render_hex": "#383838", "render_mode": 0, "finish_type": "natural", "opacity": 0.65, "feather": 6, "season_match": "Cool Winter", "price": 129.0},
    {"sku_id": "SKU_BROW_010", "spu_id": "SPU_BROW_003", "shade_name": "深棕", "hex_color": "#4A3728", "render_hex": "#5A4738", "render_mode": 0, "finish_type": "natural", "opacity": 0.65, "feather": 6, "season_match": "Warm Autumn", "price": 129.0},
    {"sku_id": "SKU_BROW_011", "spu_id": "SPU_BROW_003", "shade_name": "浅棕", "hex_color": "#7A6652", "render_hex": "#8A7662", "render_mode": 0, "finish_type": "natural", "opacity": 0.65, "feather": 6, "season_match": "Warm Spring", "price": 129.0},

    # SPU_BROW_004: 兰蔻 男士眉粉盒
    {"sku_id": "SKU_BROW_012", "spu_id": "SPU_BROW_004", "shade_name": "深棕灰", "hex_color": "#3E2F23", "render_hex": "#4E3F33", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 8, "season_match": "Cool Autumn", "price": 399.0},
    {"sku_id": "SKU_BROW_013", "spu_id": "SPU_BROW_004", "shade_name": "暖棕", "hex_color": "#6B4226", "render_hex": "#7B5236", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 8, "season_match": "Warm Autumn", "price": 399.0},
    {"sku_id": "SKU_BROW_014", "spu_id": "SPU_BROW_004", "shade_name": "灰棕", "hex_color": "#5A5A5A", "render_hex": "#6A6A6A", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 8, "season_match": "Cool Spring", "price": 399.0},

    # SPU_BROW_005: 曼秀雷敦男士 自然眉笔
    {"sku_id": "SKU_BROW_015", "spu_id": "SPU_BROW_005", "shade_name": "自然黑", "hex_color": "#333333", "render_hex": "#404040", "render_mode": 0, "finish_type": "natural", "opacity": 0.6, "feather": 7, "season_match": "Cool Winter", "price": 59.0},
    {"sku_id": "SKU_BROW_016", "spu_id": "SPU_BROW_005", "shade_name": "深棕", "hex_color": "#4A3728", "render_hex": "#5A4738", "render_mode": 0, "finish_type": "natural", "opacity": 0.6, "feather": 7, "season_match": "Warm Autumn", "price": 59.0},
    {"sku_id": "SKU_BROW_017", "spu_id": "SPU_BROW_005", "shade_name": "灰棕", "hex_color": "#5A5A5A", "render_hex": "#6A6A6A", "render_mode": 0, "finish_type": "natural", "opacity": 0.6, "feather": 7, "season_match": "Cool Summer", "price": 59.0},

    # SPU_BROW_006: 科颜氏男士 眉胶
    {"sku_id": "SKU_BROW_018", "spu_id": "SPU_BROW_006", "shade_name": "透明定型", "hex_color": "#C8C0B8", "render_hex": "#D8D0C8", "render_mode": 0, "finish_type": "natural", "opacity": 0.2, "feather": 3, "season_match": "Cool Winter", "price": 219.0},
    {"sku_id": "SKU_BROW_019", "spu_id": "SPU_BROW_006", "shade_name": "棕色定型", "hex_color": "#5A4738", "render_hex": "#6A5748", "render_mode": 0, "finish_type": "natural", "opacity": 0.3, "feather": 3, "season_match": "Warm Autumn", "price": 219.0},

    # SPU_BROW_007: 杰威尔 男士眉部染眉膏
    {"sku_id": "SKU_BROW_020", "spu_id": "SPU_BROW_007", "shade_name": "黑色", "hex_color": "#2C2C2C", "render_hex": "#383838", "render_mode": 0, "finish_type": "natural", "opacity": 0.5, "feather": 4, "season_match": "Cool Winter", "price": 89.0},
    {"sku_id": "SKU_BROW_021", "spu_id": "SPU_BROW_007", "shade_name": "深棕", "hex_color": "#4A3728", "render_hex": "#5A4738", "render_mode": 0, "finish_type": "natural", "opacity": 0.5, "feather": 4, "season_match": "Warm Autumn", "price": 89.0},
    {"sku_id": "SKU_BROW_022", "spu_id": "SPU_BROW_007", "shade_name": "浅棕", "hex_color": "#7A6652", "render_hex": "#8A7662", "render_mode": 0, "finish_type": "natural", "opacity": 0.5, "feather": 4, "season_match": "Warm Spring", "price": 89.0},

    # SPU_BROW_008: 香奈儿男士 精致眉笔
    {"sku_id": "SKU_BROW_023", "spu_id": "SPU_BROW_008", "shade_name": "深灰棕", "hex_color": "#3E2F23", "render_hex": "#4E3F33", "render_mode": 1, "finish_type": "matte", "opacity": 0.7, "feather": 4, "season_match": "Deep Autumn", "price": 459.0},
    {"sku_id": "SKU_BROW_024", "spu_id": "SPU_BROW_008", "shade_name": "炭黑", "hex_color": "#2C2C2C", "render_hex": "#383838", "render_mode": 1, "finish_type": "matte", "opacity": 0.7, "feather": 4, "season_match": "Cool Winter", "price": 459.0},
    {"sku_id": "SKU_BROW_025", "spu_id": "SPU_BROW_008", "shade_name": "暖棕", "hex_color": "#6B4226", "render_hex": "#7B5236", "render_mode": 1, "finish_type": "matte", "opacity": 0.7, "feather": 4, "season_match": "Warm Spring", "price": 459.0},
    {"sku_id": "SKU_BROW_026", "spu_id": "SPU_BROW_008", "shade_name": "石墨灰", "hex_color": "#4A4A4A", "render_hex": "#5A5A5A", "render_mode": 1, "finish_type": "matte", "opacity": 0.7, "feather": 4, "season_match": "Cool Summer", "price": 459.0},

    # ===================== 眼部 (eye) - 30 SKU =====================
    # SPU_EYE_001: MAC 男士大地色眼影盘
    {"sku_id": "SKU_EYE_001", "spu_id": "SPU_EYE_001", "shade_name": "大地色", "hex_color": "#8B7355", "render_hex": "#9A8365", "render_mode": 0, "finish_type": "matte", "opacity": 0.5, "feather": 12, "season_match": "Warm Autumn", "price": 349.0},
    {"sku_id": "SKU_EYE_002", "spu_id": "SPU_EYE_001", "shade_name": "深棕", "hex_color": "#5C4033", "render_hex": "#6C5043", "render_mode": 0, "finish_type": "matte", "opacity": 0.5, "feather": 12, "season_match": "Deep Autumn", "price": 349.0},
    {"sku_id": "SKU_EYE_003", "spu_id": "SPU_EYE_001", "shade_name": "灰棕", "hex_color": "#696969", "render_hex": "#797979", "render_mode": 0, "finish_type": "matte", "opacity": 0.5, "feather": 12, "season_match": "Cool Winter", "price": 349.0},
    {"sku_id": "SKU_EYE_004", "spu_id": "SPU_EYE_001", "shade_name": "暖米", "hex_color": "#C4A882", "render_hex": "#D0B892", "render_mode": 0, "finish_type": "satin", "opacity": 0.4, "feather": 15, "season_match": "Warm Spring", "price": 349.0},

    # SPU_EYE_002: 杰威尔 男士单色眼影
    {"sku_id": "SKU_EYE_005", "spu_id": "SPU_EYE_002", "shade_name": "摩卡", "hex_color": "#7B6B5A", "render_hex": "#8B7B6A", "render_mode": 0, "finish_type": "matte", "opacity": 0.45, "feather": 12, "season_match": "Warm Autumn", "price": 79.0},
    {"sku_id": "SKU_EYE_006", "spu_id": "SPU_EYE_002", "shade_name": "炭灰", "hex_color": "#3C3C3C", "render_hex": "#4C4C4C", "render_mode": 0, "finish_type": "matte", "opacity": 0.45, "feather": 12, "season_match": "Cool Winter", "price": 79.0},
    {"sku_id": "SKU_EYE_007", "spu_id": "SPU_EYE_002", "shade_name": "古铜", "hex_color": "#A0784C", "render_hex": "#B0885C", "render_mode": 0, "finish_type": "shimmer", "opacity": 0.4, "feather": 12, "season_match": "Warm Autumn", "price": 79.0},
    {"sku_id": "SKU_EYE_008", "spu_id": "SPU_EYE_002", "shade_name": "卡其", "hex_color": "#BDB76B", "render_hex": "#C8C278", "render_mode": 0, "finish_type": "matte", "opacity": 0.4, "feather": 12, "season_match": "Warm Spring", "price": 79.0},

    # SPU_EYE_003: 兰蔻 男士深邃眼线笔
    {"sku_id": "SKU_EYE_009", "spu_id": "SPU_EYE_003", "shade_name": "深棕", "hex_color": "#3C2F2F", "render_hex": "#4C3F3F", "render_mode": 1, "finish_type": "matte", "opacity": 0.8, "feather": 3, "season_match": "Deep Autumn", "price": 299.0},
    {"sku_id": "SKU_EYE_010", "spu_id": "SPU_EYE_003", "shade_name": "炭黑", "hex_color": "#2C2C2C", "render_hex": "#3C3C3C", "render_mode": 1, "finish_type": "matte", "opacity": 0.8, "feather": 3, "season_match": "Cool Winter", "price": 299.0},
    {"sku_id": "SKU_EYE_011", "spu_id": "SPU_EYE_003", "shade_name": "深灰", "hex_color": "#4A4A4A", "render_hex": "#5A5A5A", "render_mode": 1, "finish_type": "matte", "opacity": 0.8, "feather": 3, "season_match": "Cool Summer", "price": 299.0},

    # SPU_EYE_004: 欧莱雅男士 眼影笔
    {"sku_id": "SKU_EYE_012", "spu_id": "SPU_EYE_004", "shade_name": "大地色", "hex_color": "#8B7355", "render_hex": "#9A8365", "render_mode": 0, "finish_type": "matte", "opacity": 0.45, "feather": 14, "season_match": "Warm Autumn", "price": 119.0},
    {"sku_id": "SKU_EYE_013", "spu_id": "SPU_EYE_004", "shade_name": "深棕", "hex_color": "#5C4033", "render_hex": "#6C5043", "render_mode": 0, "finish_type": "matte", "opacity": 0.45, "feather": 14, "season_match": "Deep Autumn", "price": 119.0},
    {"sku_id": "SKU_EYE_014", "spu_id": "SPU_EYE_004", "shade_name": "石板灰", "hex_color": "#708090", "render_hex": "#8090A0", "render_mode": 0, "finish_type": "matte", "opacity": 0.45, "feather": 14, "season_match": "Cool Winter", "price": 119.0},

    # SPU_EYE_005: 香奈儿男士 四色眼影盘
    {"sku_id": "SKU_EYE_015", "spu_id": "SPU_EYE_005", "shade_name": "暖米打底", "hex_color": "#C4A882", "render_hex": "#D0B892", "render_mode": 1, "finish_type": "satin", "opacity": 0.35, "feather": 16, "season_match": "Warm Spring", "price": 699.0},
    {"sku_id": "SKU_EYE_016", "spu_id": "SPU_EYE_005", "shade_name": "大地过渡", "hex_color": "#8B7355", "render_hex": "#9A8365", "render_mode": 1, "finish_type": "matte", "opacity": 0.45, "feather": 14, "season_match": "Warm Autumn", "price": 699.0},
    {"sku_id": "SKU_EYE_017", "spu_id": "SPU_EYE_005", "shade_name": "深棕加深", "hex_color": "#5C4033", "render_hex": "#6C5043", "render_mode": 1, "finish_type": "matte", "opacity": 0.55, "feather": 10, "season_match": "Deep Autumn", "price": 699.0},
    {"sku_id": "SKU_EYE_018", "spu_id": "SPU_EYE_005", "shade_name": "铜色点缀", "hex_color": "#B87333", "render_hex": "#C88343", "render_mode": 1, "finish_type": "shimmer", "opacity": 0.4, "feather": 12, "season_match": "Warm Autumn", "price": 699.0},

    # SPU_EYE_006: 科颜氏男士 眼部提亮笔
    {"sku_id": "SKU_EYE_019", "spu_id": "SPU_EYE_006", "shade_name": "自然提亮", "hex_color": "#E8D5B7", "render_hex": "#F0E0C5", "render_mode": 1, "finish_type": "satin", "opacity": 0.3, "feather": 10, "season_match": "Warm Spring", "price": 239.0},
    {"sku_id": "SKU_EYE_020", "spu_id": "SPU_EYE_006", "shade_name": "冷调提亮", "hex_color": "#D8D8E0", "render_hex": "#E0E0E8", "render_mode": 1, "finish_type": "satin", "opacity": 0.3, "feather": 10, "season_match": "Cool Winter", "price": 239.0},

    # SPU_EYE_007: 碧欧泉男士 眼影膏
    {"sku_id": "SKU_EYE_021", "spu_id": "SPU_EYE_007", "shade_name": "大地色", "hex_color": "#8B7355", "render_hex": "#9A8365", "render_mode": 0, "finish_type": "semi-matte", "opacity": 0.4, "feather": 14, "season_match": "Warm Autumn", "price": 319.0},
    {"sku_id": "SKU_EYE_022", "spu_id": "SPU_EYE_007", "shade_name": "古铜", "hex_color": "#A0784C", "render_hex": "#B0885C", "render_mode": 0, "finish_type": "shimmer", "opacity": 0.4, "feather": 14, "season_match": "Warm Autumn", "price": 319.0},
    {"sku_id": "SKU_EYE_023", "spu_id": "SPU_EYE_007", "shade_name": "摩卡", "hex_color": "#7B6B5A", "render_hex": "#8B7B6A", "render_mode": 0, "finish_type": "matte", "opacity": 0.45, "feather": 14, "season_match": "Cool Autumn", "price": 319.0},

    # SPU_EYE_008: 杰威尔 男士内眼线笔
    {"sku_id": "SKU_EYE_024", "spu_id": "SPU_EYE_008", "shade_name": "深棕", "hex_color": "#3C2F2F", "render_hex": "#4C3F3F", "render_mode": 1, "finish_type": "matte", "opacity": 0.75, "feather": 2, "season_match": "Deep Autumn", "price": 69.0},
    {"sku_id": "SKU_EYE_025", "spu_id": "SPU_EYE_008", "shade_name": "炭黑", "hex_color": "#2C2C2C", "render_hex": "#3C3C3C", "render_mode": 1, "finish_type": "matte", "opacity": 0.75, "feather": 2, "season_match": "Cool Winter", "price": 69.0},
    {"sku_id": "SKU_EYE_026", "spu_id": "SPU_EYE_008", "shade_name": "灰棕", "hex_color": "#696969", "render_hex": "#797979", "render_mode": 1, "finish_type": "matte", "opacity": 0.75, "feather": 2, "season_match": "Cool Summer", "price": 69.0},
    {"sku_id": "SKU_EYE_027", "spu_id": "SPU_EYE_008", "shade_name": "铜棕", "hex_color": "#6B4226", "render_hex": "#7B5236", "render_mode": 1, "finish_type": "matte", "opacity": 0.75, "feather": 2, "season_match": "Warm Autumn", "price": 69.0},

    # ===================== 唇部 (lip) - 30 SKU =====================
    # SPU_LIP_001: 杰威尔 男士润色唇膏
    {"sku_id": "SKU_LIP_001", "spu_id": "SPU_LIP_001", "shade_name": "自然裸色", "hex_color": "#C98B7B", "render_hex": "#D09B8B", "render_mode": 0, "finish_type": "natural", "opacity": 0.45, "feather": 8, "season_match": "Warm Spring", "price": 99.0},
    {"sku_id": "SKU_LIP_002", "spu_id": "SPU_LIP_001", "shade_name": "玫瑰豆沙", "hex_color": "#B14A5A", "render_hex": "#C15A6A", "render_mode": 0, "finish_type": "semi-matte", "opacity": 0.5, "feather": 8, "season_match": "Cool Winter", "price": 99.0},
    {"sku_id": "SKU_LIP_003", "spu_id": "SPU_LIP_001", "shade_name": "珊瑚橘", "hex_color": "#E07A5F", "render_hex": "#E88A6F", "render_mode": 0, "finish_type": "semi-matte", "opacity": 0.5, "feather": 8, "season_match": "Warm Autumn", "price": 99.0},
    {"sku_id": "SKU_LIP_004", "spu_id": "SPU_LIP_001", "shade_name": "焦糖", "hex_color": "#B8866B", "render_hex": "#C8967B", "render_mode": 0, "finish_type": "natural", "opacity": 0.45, "feather": 8, "season_match": "Warm Autumn", "price": 99.0},

    # SPU_LIP_002: MAC 男士哑光唇膏
    {"sku_id": "SKU_LIP_005", "spu_id": "SPU_LIP_002", "shade_name": "裸粉", "hex_color": "#D9A9A0", "render_hex": "#E3B9B0", "render_mode": 0, "finish_type": "matte", "opacity": 0.6, "feather": 6, "season_match": "Warm Spring", "price": 229.0},
    {"sku_id": "SKU_LIP_006", "spu_id": "SPU_LIP_002", "shade_name": "玫瑰豆沙", "hex_color": "#B14A5A", "render_hex": "#C15A6A", "render_mode": 0, "finish_type": "matte", "opacity": 0.6, "feather": 6, "season_match": "Cool Winter", "price": 229.0},
    {"sku_id": "SKU_LIP_007", "spu_id": "SPU_LIP_002", "shade_name": "砖红", "hex_color": "#8B3A3A", "render_hex": "#9B4A4A", "render_mode": 0, "finish_type": "matte", "opacity": 0.6, "feather": 6, "season_match": "Deep Winter", "price": 229.0},
    {"sku_id": "SKU_LIP_008", "spu_id": "SPU_LIP_002", "shade_name": "陶土色", "hex_color": "#C4714E", "render_hex": "#D4815E", "render_mode": 0, "finish_type": "matte", "opacity": 0.6, "feather": 6, "season_match": "Warm Autumn", "price": 229.0},

    # SPU_LIP_003: 曼秀雷敦男士 保湿润唇膏
    {"sku_id": "SKU_LIP_009", "spu_id": "SPU_LIP_003", "shade_name": "透明保湿", "hex_color": "#E8C8B8", "render_hex": "#F0D0C0", "render_mode": 0, "finish_type": "gloss", "opacity": 0.25, "feather": 10, "season_match": "Cool Spring", "price": 39.0},
    {"sku_id": "SKU_LIP_010", "spu_id": "SPU_LIP_003", "shade_name": "淡粉", "hex_color": "#D4A0A0", "render_hex": "#DEB0B0", "render_mode": 0, "finish_type": "gloss", "opacity": 0.3, "feather": 10, "season_match": "Cool Summer", "price": 39.0},
    {"sku_id": "SKU_LIP_011", "spu_id": "SPU_LIP_003", "shade_name": "自然裸色", "hex_color": "#C98B7B", "render_hex": "#D09B8B", "render_mode": 0, "finish_type": "gloss", "opacity": 0.3, "feather": 10, "season_match": "Warm Spring", "price": 39.0},

    # SPU_LIP_004: 欧莱雅男士 唇彩笔
    {"sku_id": "SKU_LIP_012", "spu_id": "SPU_LIP_004", "shade_name": "自然裸色", "hex_color": "#C98B7B", "render_hex": "#D09B8B", "render_mode": 0, "finish_type": "semi-matte", "opacity": 0.45, "feather": 7, "season_match": "Warm Spring", "price": 89.0},
    {"sku_id": "SKU_LIP_013", "spu_id": "SPU_LIP_004", "shade_name": "花梨木", "hex_color": "#A0524C", "render_hex": "#B0625C", "render_mode": 0, "finish_type": "semi-matte", "opacity": 0.5, "feather": 7, "season_match": "Warm Autumn", "price": 89.0},
    {"sku_id": "SKU_LIP_014", "spu_id": "SPU_LIP_004", "shade_name": "柔粉", "hex_color": "#D4A0A0", "render_hex": "#DEB0B0", "render_mode": 0, "finish_type": "semi-matte", "opacity": 0.4, "feather": 7, "season_match": "Cool Spring", "price": 89.0},

    # SPU_LIP_005: 兰蔻 男士柔润唇膏
    {"sku_id": "SKU_LIP_015", "spu_id": "SPU_LIP_005", "shade_name": "裸粉", "hex_color": "#D9A9A0", "render_hex": "#E3B9B0", "render_mode": 1, "finish_type": "natural", "opacity": 0.4, "feather": 8, "season_match": "Warm Spring", "price": 359.0},
    {"sku_id": "SKU_LIP_016", "spu_id": "SPU_LIP_005", "shade_name": "玫瑰豆沙", "hex_color": "#B14A5A", "render_hex": "#C15A6A", "render_mode": 1, "finish_type": "semi-matte", "opacity": 0.5, "feather": 8, "season_match": "Cool Winter", "price": 359.0},
    {"sku_id": "SKU_LIP_017", "spu_id": "SPU_LIP_005", "shade_name": "珊瑚橘", "hex_color": "#E07A5F", "render_hex": "#E88A6F", "render_mode": 1, "finish_type": "semi-matte", "opacity": 0.5, "feather": 8, "season_match": "Warm Autumn", "price": 359.0},
    {"sku_id": "SKU_LIP_018", "spu_id": "SPU_LIP_005", "shade_name": "浆果轻染", "hex_color": "#9B3A4E", "render_hex": "#AB4A5E", "render_mode": 1, "finish_type": "semi-matte", "opacity": 0.5, "feather": 8, "season_match": "Deep Winter", "price": 359.0},

    # SPU_LIP_006: 香奈儿男士 丝绒唇釉
    {"sku_id": "SKU_LIP_019", "spu_id": "SPU_LIP_006", "shade_name": "裸粉", "hex_color": "#D9A9A0", "render_hex": "#E3B9B0", "render_mode": 1, "finish_type": "matte", "opacity": 0.55, "feather": 6, "season_match": "Warm Spring", "price": 549.0},
    {"sku_id": "SKU_LIP_020", "spu_id": "SPU_LIP_006", "shade_name": "玫瑰豆沙", "hex_color": "#B14A5A", "render_hex": "#C15A6A", "render_mode": 1, "finish_type": "matte", "opacity": 0.55, "feather": 6, "season_match": "Cool Winter", "price": 549.0},
    {"sku_id": "SKU_LIP_021", "spu_id": "SPU_LIP_006", "shade_name": "砖红", "hex_color": "#8B3A3A", "render_hex": "#9B4A4A", "render_mode": 1, "finish_type": "matte", "opacity": 0.55, "feather": 6, "season_match": "Deep Winter", "price": 549.0},
    {"sku_id": "SKU_LIP_022", "spu_id": "SPU_LIP_006", "shade_name": "陶土色", "hex_color": "#C4714E", "render_hex": "#D4815E", "render_mode": 1, "finish_type": "matte", "opacity": 0.55, "feather": 6, "season_match": "Warm Autumn", "price": 549.0},

    # SPU_LIP_007: 科颜氏男士 自然唇色笔
    {"sku_id": "SKU_LIP_023", "spu_id": "SPU_LIP_007", "shade_name": "自然裸色", "hex_color": "#C98B7B", "render_hex": "#D09B8B", "render_mode": 0, "finish_type": "natural", "opacity": 0.4, "feather": 8, "season_match": "Warm Spring", "price": 199.0},
    {"sku_id": "SKU_LIP_024", "spu_id": "SPU_LIP_007", "shade_name": "焦糖", "hex_color": "#B8866B", "render_hex": "#C8967B", "render_mode": 0, "finish_type": "natural", "opacity": 0.4, "feather": 8, "season_match": "Warm Autumn", "price": 199.0},
    {"sku_id": "SKU_LIP_025", "spu_id": "SPU_LIP_007", "shade_name": "柔粉", "hex_color": "#D4A0A0", "render_hex": "#DEB0B0", "render_mode": 0, "finish_type": "natural", "opacity": 0.4, "feather": 8, "season_match": "Cool Summer", "price": 199.0},

    # SPU_LIP_008: 碧欧泉男士 护色唇膏
    {"sku_id": "SKU_LIP_026", "spu_id": "SPU_LIP_008", "shade_name": "裸粉", "hex_color": "#D9A9A0", "render_hex": "#E3B9B0", "render_mode": 0, "finish_type": "gloss", "opacity": 0.35, "feather": 9, "season_match": "Warm Spring", "price": 279.0},
    {"sku_id": "SKU_LIP_027", "spu_id": "SPU_LIP_008", "shade_name": "花梨木", "hex_color": "#A0524C", "render_hex": "#B0625C", "render_mode": 0, "finish_type": "gloss", "opacity": 0.4, "feather": 9, "season_match": "Warm Autumn", "price": 279.0},
    {"sku_id": "SKU_LIP_028", "spu_id": "SPU_LIP_008", "shade_name": "珊瑚橘", "hex_color": "#E07A5F", "render_hex": "#E88A6F", "render_mode": 0, "finish_type": "gloss", "opacity": 0.4, "feather": 9, "season_match": "Warm Autumn", "price": 279.0},
    {"sku_id": "SKU_LIP_029", "spu_id": "SPU_LIP_008", "shade_name": "浆果轻染", "hex_color": "#9B3A4E", "render_hex": "#AB4A5E", "render_mode": 0, "finish_type": "gloss", "opacity": 0.4, "feather": 9, "season_match": "Deep Winter", "price": 279.0},

    # ===================== 修容 (contour) - 28 SKU =====================
    # SPU_CONT_001: MAC 男士修容盘
    {"sku_id": "SKU_CONT_001", "spu_id": "SPU_CONT_001", "shade_name": "浅古铜", "hex_color": "#C4A882", "render_hex": "#D0B892", "render_mode": 0, "finish_type": "matte", "opacity": 0.4, "feather": 15, "season_match": "Warm Spring", "price": 329.0},
    {"sku_id": "SKU_CONT_002", "spu_id": "SPU_CONT_001", "shade_name": "深棕修容", "hex_color": "#8B6914", "render_hex": "#9B7924", "render_mode": 0, "finish_type": "matte", "opacity": 0.5, "feather": 12, "season_match": "Deep Autumn", "price": 329.0},
    {"sku_id": "SKU_CONT_003", "spu_id": "SPU_CONT_001", "shade_name": "冷灰阴影", "hex_color": "#7A7A7A", "render_hex": "#8A8A8A", "render_mode": 0, "finish_type": "matte", "opacity": 0.45, "feather": 12, "season_match": "Cool Winter", "price": 329.0},
    {"sku_id": "SKU_CONT_004", "spu_id": "SPU_CONT_001", "shade_name": "暖调高光", "hex_color": "#E8D5B7", "render_hex": "#F0E0C5", "render_mode": 0, "finish_type": "satin", "opacity": 0.3, "feather": 18, "season_match": "Warm Spring", "price": 329.0},

    # SPU_CONT_002: 杰威尔 男士立体修容粉
    {"sku_id": "SKU_CONT_005", "spu_id": "SPU_CONT_002", "shade_name": "暖古铜", "hex_color": "#A68B5B", "render_hex": "#B69B6B", "render_mode": 0, "finish_type": "matte", "opacity": 0.45, "feather": 14, "season_match": "Warm Autumn", "price": 139.0},
    {"sku_id": "SKU_CONT_006", "spu_id": "SPU_CONT_002", "shade_name": "自然阴影", "hex_color": "#9E8E7E", "render_hex": "#AE9E8E", "render_mode": 0, "finish_type": "matte", "opacity": 0.45, "feather": 14, "season_match": "Cool Autumn", "price": 139.0},
    {"sku_id": "SKU_CONT_007", "spu_id": "SPU_CONT_002", "shade_name": "柔和塑形", "hex_color": "#B8A088", "render_hex": "#C8B098", "render_mode": 0, "finish_type": "natural", "opacity": 0.4, "feather": 16, "season_match": "Warm Spring", "price": 139.0},

    # SPU_CONT_003: 欧莱雅男士 修容棒
    {"sku_id": "SKU_CONT_008", "spu_id": "SPU_CONT_003", "shade_name": "冷调修容", "hex_color": "#8B7D6B", "render_hex": "#9B8D7B", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 10, "season_match": "Cool Winter", "price": 109.0},
    {"sku_id": "SKU_CONT_009", "spu_id": "SPU_CONT_003", "shade_name": "暖古铜", "hex_color": "#A68B5B", "render_hex": "#B69B6B", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 10, "season_match": "Warm Autumn", "price": 109.0},
    {"sku_id": "SKU_CONT_010", "spu_id": "SPU_CONT_003", "shade_name": "自然阴影", "hex_color": "#9E8E7E", "render_hex": "#AE9E8E", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 10, "season_match": "Cool Autumn", "price": 109.0},

    # SPU_CONT_004: 兰蔻 男士阴影膏
    {"sku_id": "SKU_CONT_011", "spu_id": "SPU_CONT_004", "shade_name": "冷灰阴影", "hex_color": "#7A7A7A", "render_hex": "#8A8A8A", "render_mode": 1, "finish_type": "natural", "opacity": 0.4, "feather": 12, "season_match": "Cool Winter", "price": 429.0},
    {"sku_id": "SKU_CONT_012", "spu_id": "SPU_CONT_004", "shade_name": "深棕修容", "hex_color": "#8B6914", "render_hex": "#9B7924", "render_mode": 1, "finish_type": "natural", "opacity": 0.45, "feather": 12, "season_match": "Deep Autumn", "price": 429.0},
    {"sku_id": "SKU_CONT_013", "spu_id": "SPU_CONT_004", "shade_name": "暖调高光", "hex_color": "#E8D5B7", "render_hex": "#F0E0C5", "render_mode": 1, "finish_type": "satin", "opacity": 0.3, "feather": 16, "season_match": "Warm Spring", "price": 429.0},

    # SPU_CONT_005: 香奈儿男士 双色修容盘
    {"sku_id": "SKU_CONT_014", "spu_id": "SPU_CONT_005", "shade_name": "阴影色", "hex_color": "#8B7D6B", "render_hex": "#9B8D7B", "render_mode": 1, "finish_type": "matte", "opacity": 0.45, "feather": 13, "season_match": "Cool Winter", "price": 799.0},
    {"sku_id": "SKU_CONT_015", "spu_id": "SPU_CONT_005", "shade_name": "高光色", "hex_color": "#E8D5B7", "render_hex": "#F0E0C5", "render_mode": 1, "finish_type": "satin", "opacity": 0.3, "feather": 16, "season_match": "Warm Spring", "price": 799.0},
    {"sku_id": "SKU_CONT_016", "spu_id": "SPU_CONT_005", "shade_name": "古铜色", "hex_color": "#A68B5B", "render_hex": "#B69B6B", "render_mode": 1, "finish_type": "matte", "opacity": 0.45, "feather": 13, "season_match": "Warm Autumn", "price": 799.0},
    {"sku_id": "SKU_CONT_017", "spu_id": "SPU_CONT_005", "shade_name": "冷灰阴影", "hex_color": "#7A7A7A", "render_hex": "#8A8A8A", "render_mode": 1, "finish_type": "matte", "opacity": 0.45, "feather": 13, "season_match": "Cool Summer", "price": 799.0},

    # SPU_CONT_006: 科颜氏男士 古铜粉
    {"sku_id": "SKU_CONT_018", "spu_id": "SPU_CONT_006", "shade_name": "浅古铜", "hex_color": "#C4A882", "render_hex": "#D0B892", "render_mode": 0, "finish_type": "natural", "opacity": 0.35, "feather": 18, "season_match": "Warm Spring", "price": 289.0},
    {"sku_id": "SKU_CONT_019", "spu_id": "SPU_CONT_006", "shade_name": "暖古铜", "hex_color": "#A68B5B", "render_hex": "#B69B6B", "render_mode": 0, "finish_type": "natural", "opacity": 0.4, "feather": 16, "season_match": "Warm Autumn", "price": 289.0},

    # SPU_CONT_007: 碧欧泉男士 高光修容笔
    {"sku_id": "SKU_CONT_020", "spu_id": "SPU_CONT_007", "shade_name": "冷调高光", "hex_color": "#E0D8D0", "render_hex": "#EAE2DA", "render_mode": 1, "finish_type": "satin", "opacity": 0.3, "feather": 12, "season_match": "Cool Winter", "price": 369.0},
    {"sku_id": "SKU_CONT_021", "spu_id": "SPU_CONT_007", "shade_name": "暖调高光", "hex_color": "#E8D5B7", "render_hex": "#F0E0C5", "render_mode": 1, "finish_type": "satin", "opacity": 0.3, "feather": 12, "season_match": "Warm Spring", "price": 369.0},

    # SPU_CONT_008: 曼秀雷敦男士 修容笔
    {"sku_id": "SKU_CONT_022", "spu_id": "SPU_CONT_008", "shade_name": "自然阴影", "hex_color": "#9E8E7E", "render_hex": "#AE9E8E", "render_mode": 0, "finish_type": "matte", "opacity": 0.5, "feather": 10, "season_match": "Cool Autumn", "price": 69.0},
    {"sku_id": "SKU_CONT_023", "spu_id": "SPU_CONT_008", "shade_name": "暖古铜", "hex_color": "#A68B5B", "render_hex": "#B69B6B", "render_mode": 0, "finish_type": "matte", "opacity": 0.5, "feather": 10, "season_match": "Warm Autumn", "price": 69.0},
    {"sku_id": "SKU_CONT_024", "spu_id": "SPU_CONT_008", "shade_name": "冷灰阴影", "hex_color": "#7A7A7A", "render_hex": "#8A8A8A", "render_mode": 0, "finish_type": "matte", "opacity": 0.5, "feather": 10, "season_match": "Cool Winter", "price": 69.0},
    {"sku_id": "SKU_CONT_025", "spu_id": "SPU_CONT_008", "shade_name": "柔和塑形", "hex_color": "#B8A088", "render_hex": "#C8B098", "render_mode": 0, "finish_type": "natural", "opacity": 0.45, "feather": 12, "season_match": "Warm Spring", "price": 69.0},
    {"sku_id": "SKU_CONT_026", "spu_id": "SPU_CONT_008", "shade_name": "深棕修容", "hex_color": "#8B6914", "render_hex": "#9B7924", "render_mode": 0, "finish_type": "matte", "opacity": 0.5, "feather": 10, "season_match": "Deep Autumn", "price": 69.0},
    {"sku_id": "SKU_CONT_027", "spu_id": "SPU_CONT_008", "shade_name": "冷调修容", "hex_color": "#8B7D6B", "render_hex": "#9B8D7B", "render_mode": 0, "finish_type": "matte", "opacity": 0.5, "feather": 10, "season_match": "Cool Summer", "price": 69.0},
    {"sku_id": "SKU_CONT_028", "spu_id": "SPU_CONT_008", "shade_name": "浅古铜", "hex_color": "#C4A882", "render_hex": "#D0B892", "render_mode": 0, "finish_type": "natural", "opacity": 0.4, "feather": 14, "season_match": "Warm Spring", "price": 69.0},
    # 额外补充 SKU - 杰威尔 男士多效遮瑕盘
    {"sku_id": "SKU_BASE_033", "spu_id": "SPU_BASE_010", "shade_name": "象牙遮瑕", "hex_color": "#F0DFC8", "render_hex": "#E8D4BC", "render_mode": 1, "finish_type": "semi-matte", "opacity": 0.65, "feather": 8, "season_match": "Cool Spring", "price": 109.0},
    {"sku_id": "SKU_BASE_034", "spu_id": "SPU_BASE_007", "shade_name": "小麦遮瑕", "hex_color": "#D4B896", "render_hex": "#C8A880", "render_mode": 1, "finish_type": "semi-matte", "opacity": 0.7, "feather": 10, "season_match": "Cool Autumn", "price": 349.0},
    {"sku_id": "SKU_BASE_035", "spu_id": "SPU_BASE_005", "shade_name": "N4 沙色", "hex_color": "#DFC5A8", "render_hex": "#D5B898", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 15, "season_match": "Cool Autumn", "price": 299.0},
    # 额外补充 SKU - 眉部
    {"sku_id": "SKU_BROW_027", "spu_id": "SPU_BROW_001", "shade_name": "石墨灰", "hex_color": "#4A4A4A", "render_hex": "#5A5A5A", "render_mode": 0, "finish_type": "matte", "opacity": 0.7, "feather": 5, "season_match": "Cool Summer", "price": 109.0},
    {"sku_id": "SKU_BROW_028", "spu_id": "SPU_BROW_002", "shade_name": "暖棕", "hex_color": "#6B4226", "render_hex": "#7B5236", "render_mode": 0, "finish_type": "matte", "opacity": 0.75, "feather": 4, "season_match": "Warm Spring", "price": 199.0},
    {"sku_id": "SKU_BROW_029", "spu_id": "SPU_BROW_003", "shade_name": "灰棕", "hex_color": "#5A5A5A", "render_hex": "#6A6A6A", "render_mode": 0, "finish_type": "natural", "opacity": 0.65, "feather": 6, "season_match": "Cool Summer", "price": 129.0},
    {"sku_id": "SKU_BROW_030", "spu_id": "SPU_BROW_004", "shade_name": "自然黑", "hex_color": "#2C2C2C", "render_hex": "#383838", "render_mode": 0, "finish_type": "matte", "opacity": 0.55, "feather": 8, "season_match": "Cool Winter", "price": 399.0},
    # 额外补充 SKU - 眼部
    {"sku_id": "SKU_EYE_028", "spu_id": "SPU_EYE_002", "shade_name": "深棕", "hex_color": "#5C4033", "render_hex": "#6C5043", "render_mode": 0, "finish_type": "matte", "opacity": 0.45, "feather": 12, "season_match": "Deep Autumn", "price": 79.0},
    {"sku_id": "SKU_EYE_029", "spu_id": "SPU_EYE_004", "shade_name": "暖米", "hex_color": "#C4A882", "render_hex": "#D0B892", "render_mode": 0, "finish_type": "satin", "opacity": 0.4, "feather": 14, "season_match": "Warm Spring", "price": 119.0},
    {"sku_id": "SKU_EYE_030", "spu_id": "SPU_EYE_007", "shade_name": "铜色", "hex_color": "#B87333", "render_hex": "#C88343", "render_mode": 0, "finish_type": "shimmer", "opacity": 0.4, "feather": 14, "season_match": "Warm Autumn", "price": 319.0},
    # 额外补充 SKU - 唇部
    {"sku_id": "SKU_LIP_030", "spu_id": "SPU_LIP_001", "shade_name": "花梨木", "hex_color": "#A0524C", "render_hex": "#B0625C", "render_mode": 0, "finish_type": "semi-matte", "opacity": 0.5, "feather": 8, "season_match": "Warm Autumn", "price": 99.0},
    {"sku_id": "SKU_LIP_031", "spu_id": "SPU_LIP_002", "shade_name": "自然裸色", "hex_color": "#C98B7B", "render_hex": "#D09B8B", "render_mode": 0, "finish_type": "matte", "opacity": 0.6, "feather": 6, "season_match": "Warm Spring", "price": 229.0},
    {"sku_id": "SKU_LIP_032", "spu_id": "SPU_LIP_005", "shade_name": "花梨木", "hex_color": "#A0524C", "render_hex": "#B0625C", "render_mode": 1, "finish_type": "semi-matte", "opacity": 0.5, "feather": 8, "season_match": "Warm Autumn", "price": 359.0},
    {"sku_id": "SKU_LIP_033", "spu_id": "SPU_LIP_006", "shade_name": "珊瑚橘", "hex_color": "#E07A5F", "render_hex": "#E88A6F", "render_mode": 1, "finish_type": "matte", "opacity": 0.55, "feather": 6, "season_match": "Warm Autumn", "price": 549.0},
    {"sku_id": "SKU_LIP_034", "spu_id": "SPU_LIP_007", "shade_name": "玫瑰豆沙", "hex_color": "#B14A5A", "render_hex": "#C15A6A", "render_mode": 0, "finish_type": "natural", "opacity": 0.4, "feather": 8, "season_match": "Cool Winter", "price": 199.0},
    {"sku_id": "SKU_LIP_035", "spu_id": "SPU_LIP_008", "shade_name": "裸粉", "hex_color": "#D9A9A0", "render_hex": "#E3B9B0", "render_mode": 0, "finish_type": "gloss", "opacity": 0.35, "feather": 9, "season_match": "Warm Spring", "price": 279.0},
    # 额外补充 SKU - 修容
    {"sku_id": "SKU_CONT_029", "spu_id": "SPU_CONT_002", "shade_name": "冷调修容", "hex_color": "#8B7D6B", "render_hex": "#9B8D7B", "render_mode": 0, "finish_type": "matte", "opacity": 0.45, "feather": 14, "season_match": "Cool Summer", "price": 139.0},
    {"sku_id": "SKU_CONT_030", "spu_id": "SPU_CONT_001", "shade_name": "自然阴影", "hex_color": "#9E8E7E", "render_hex": "#AE9E8E", "render_mode": 0, "finish_type": "matte", "opacity": 0.45, "feather": 12, "season_match": "Cool Autumn", "price": 329.0},
    {"sku_id": "SKU_CONT_031", "spu_id": "SPU_CONT_004", "shade_name": "自然阴影", "hex_color": "#9E8E7E", "render_hex": "#AE9E8E", "render_mode": 1, "finish_type": "natural", "opacity": 0.4, "feather": 12, "season_match": "Cool Autumn", "price": 429.0},
    {"sku_id": "SKU_CONT_032", "spu_id": "SPU_CONT_006", "shade_name": "冷灰阴影", "hex_color": "#7A7A7A", "render_hex": "#8A8A8A", "render_mode": 0, "finish_type": "natural", "opacity": 0.4, "feather": 16, "season_match": "Cool Winter", "price": 289.0},
]

# ============================================================
# 季型规则数据 (season_rules)
# ============================================================
SEASON_RULES_DATA = [
    {
        "season_type": "Warm Spring",
        "tone": "warm",
        "lips_palette": ["#C98B7B", "#E07A5F", "#D9A9A0", "#B8866B"],
        "cheeks_palette": ["#C4A882", "#B8A088", "#E8D5B7", "#A68B5B"],
        "brow_palette": ["#4A3728", "#6B4226", "#7A6652", "#5A5A5A"],
        "avoid_palette": ["#9B3A4E", "#3C3C3C", "#708090", "#7A7A7A"],
        "recommended_palette": ["#C98B7B", "#E07A5F", "#D9A9A0", "#B8866B", "#C4A882", "#B8A088", "#E8D5B7", "#4A3728", "#6B4226", "#7A6652"],
    },
    {
        "season_type": "Cool Winter",
        "tone": "cool",
        "lips_palette": ["#B14A5A", "#9B3A4E", "#8B3A3A", "#D4A0A0"],
        "cheeks_palette": ["#8B7D6B", "#7A7A7A", "#9E8E7E", "#8B6914"],
        "brow_palette": ["#2C2C2C", "#333333", "#4A4A4A", "#5A5A5A"],
        "avoid_palette": ["#E07A5F", "#B87333", "#C4A882", "#E8D5B7"],
        "recommended_palette": ["#B14A5A", "#9B3A4E", "#8B3A3A", "#D4A0A0", "#8B7D6B", "#7A7A7A", "#2C2C2C", "#333333", "#4A4A4A", "#5A5A5A"],
    },
    {
        "season_type": "Warm Autumn",
        "tone": "warm",
        "lips_palette": ["#C98B7B", "#C4714E", "#A0524C", "#B8866B"],
        "cheeks_palette": ["#A68B5B", "#C4A882", "#9E8E7E", "#8B6914"],
        "brow_palette": ["#4A3728", "#6B4226", "#3E2F23", "#7A6652"],
        "avoid_palette": ["#D4A0A0", "#708090", "#B14A5A", "#7A7A7A"],
        "recommended_palette": ["#C98B7B", "#C4714E", "#A0524C", "#B8866B", "#A68B5B", "#C4A882", "#9E8E7E", "#4A3728", "#6B4226", "#3E2F23"],
    },
    {
        "season_type": "Cool Summer",
        "tone": "cool",
        "lips_palette": ["#B14A5A", "#D4A0A0", "#D9A9A0", "#A0524C"],
        "cheeks_palette": ["#8B7D6B", "#B8A088", "#7A7A7A", "#9E8E7E"],
        "brow_palette": ["#5A5A5A", "#4A4A4A", "#7A6652", "#3E2F23"],
        "avoid_palette": ["#E07A5F", "#8B3A3A", "#B87333", "#8B6914"],
        "recommended_palette": ["#B14A5A", "#D4A0A0", "#D9A9A0", "#A0524C", "#8B7D6B", "#B8A088", "#5A5A5A", "#4A4A4A", "#7A6652", "#3E2F23"],
    },
]

# ============================================================
# 季型到 SKU 映射数据 (season_sku_map)
# ============================================================
SEASON_SKU_MAP_DATA = [
    # Warm Spring 推荐
    {"season_type": "Warm Spring", "sku_id": "SKU_BASE_002"},
    {"season_type": "Warm Spring", "sku_id": "SKU_BASE_009"},
    {"season_type": "Warm Spring", "sku_id": "SKU_BASE_012"},
    {"season_type": "Warm Spring", "sku_id": "SKU_BASE_016"},
    {"season_type": "Warm Spring", "sku_id": "SKU_BASE_021"},
    {"season_type": "Warm Spring", "sku_id": "SKU_BASE_022"},
    {"season_type": "Warm Spring", "sku_id": "SKU_BASE_029"},
    {"season_type": "Warm Spring", "sku_id": "SKU_BASE_031"},
    {"season_type": "Warm Spring", "sku_id": "SKU_BROW_004"},
    {"season_type": "Warm Spring", "sku_id": "SKU_BROW_011"},
    {"season_type": "Warm Spring", "sku_id": "SKU_BROW_014"},
    {"season_type": "Warm Spring", "sku_id": "SKU_BROW_022"},
    {"season_type": "Warm Spring", "sku_id": "SKU_BROW_025"},
    {"season_type": "Warm Spring", "sku_id": "SKU_EYE_004"},
    {"season_type": "Warm Spring", "sku_id": "SKU_EYE_008"},
    {"season_type": "Warm Spring", "sku_id": "SKU_EYE_015"},
    {"season_type": "Warm Spring", "sku_id": "SKU_EYE_019"},
    {"season_type": "Warm Spring", "sku_id": "SKU_LIP_001"},
    {"season_type": "Warm Spring", "sku_id": "SKU_LIP_003"},
    {"season_type": "Warm Spring", "sku_id": "SKU_LIP_005"},
    {"season_type": "Warm Spring", "sku_id": "SKU_LIP_011"},
    {"season_type": "Warm Spring", "sku_id": "SKU_LIP_012"},
    {"season_type": "Warm Spring", "sku_id": "SKU_LIP_015"},
    {"season_type": "Warm Spring", "sku_id": "SKU_LIP_019"},
    {"season_type": "Warm Spring", "sku_id": "SKU_LIP_023"},
    {"season_type": "Warm Spring", "sku_id": "SKU_LIP_026"},
    {"season_type": "Warm Spring", "sku_id": "SKU_CONT_001"},
    {"season_type": "Warm Spring", "sku_id": "SKU_CONT_004"},
    {"season_type": "Warm Spring", "sku_id": "SKU_CONT_007"},
    {"season_type": "Warm Spring", "sku_id": "SKU_CONT_015"},
    {"season_type": "Warm Spring", "sku_id": "SKU_CONT_018"},
    {"season_type": "Warm Spring", "sku_id": "SKU_CONT_021"},
    {"season_type": "Warm Spring", "sku_id": "SKU_CONT_025"},
    {"season_type": "Warm Spring", "sku_id": "SKU_CONT_028"},

    # Cool Winter 推荐
    {"season_type": "Cool Winter", "sku_id": "SKU_BASE_001"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BASE_005"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BASE_011"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BASE_015"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BASE_020"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BASE_023"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BASE_026"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BASE_030"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BROW_001"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BROW_005"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BROW_008"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BROW_009"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BROW_015"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BROW_018"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BROW_020"},
    {"season_type": "Cool Winter", "sku_id": "SKU_BROW_024"},
    {"season_type": "Cool Winter", "sku_id": "SKU_EYE_003"},
    {"season_type": "Cool Winter", "sku_id": "SKU_EYE_006"},
    {"season_type": "Cool Winter", "sku_id": "SKU_EYE_010"},
    {"season_type": "Cool Winter", "sku_id": "SKU_EYE_014"},
    {"season_type": "Cool Winter", "sku_id": "SKU_EYE_020"},
    {"season_type": "Cool Winter", "sku_id": "SKU_EYE_025"},
    {"season_type": "Cool Winter", "sku_id": "SKU_LIP_002"},
    {"season_type": "Cool Winter", "sku_id": "SKU_LIP_006"},
    {"season_type": "Cool Winter", "sku_id": "SKU_LIP_007"},
    {"season_type": "Cool Winter", "sku_id": "SKU_LIP_016"},
    {"season_type": "Cool Winter", "sku_id": "SKU_LIP_020"},
    {"season_type": "Cool Winter", "sku_id": "SKU_LIP_029"},
    {"season_type": "Cool Winter", "sku_id": "SKU_CONT_003"},
    {"season_type": "Cool Winter", "sku_id": "SKU_CONT_008"},
    {"season_type": "Cool Winter", "sku_id": "SKU_CONT_011"},
    {"season_type": "Cool Winter", "sku_id": "SKU_CONT_014"},
    {"season_type": "Cool Winter", "sku_id": "SKU_CONT_020"},
    {"season_type": "Cool Winter", "sku_id": "SKU_CONT_024"},

    # Warm Autumn 推荐
    {"season_type": "Warm Autumn", "sku_id": "SKU_BASE_003"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BASE_004"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BASE_007"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BASE_010"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BASE_013"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BASE_017"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BASE_022"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BASE_025"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BASE_032"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BROW_002"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BROW_006"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BROW_010"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BROW_012"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BROW_013"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BROW_016"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BROW_019"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BROW_021"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_BROW_023"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_EYE_001"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_EYE_002"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_EYE_005"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_EYE_007"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_EYE_012"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_EYE_016"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_EYE_017"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_EYE_018"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_EYE_021"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_EYE_022"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_EYE_024"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_EYE_027"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_LIP_003"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_LIP_004"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_LIP_008"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_LIP_013"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_LIP_017"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_LIP_022"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_LIP_024"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_LIP_027"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_LIP_028"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_CONT_002"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_CONT_005"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_CONT_006"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_CONT_009"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_CONT_012"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_CONT_016"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_CONT_019"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_CONT_023"},
    {"season_type": "Warm Autumn", "sku_id": "SKU_CONT_026"},

    # Cool Summer 推荐
    {"season_type": "Cool Summer", "sku_id": "SKU_BASE_008"},
    {"season_type": "Cool Summer", "sku_id": "SKU_BASE_020"},
    {"season_type": "Cool Summer", "sku_id": "SKU_BASE_021"},
    {"season_type": "Cool Summer", "sku_id": "SKU_BASE_028"},
    {"season_type": "Cool Summer", "sku_id": "SKU_BROW_003"},
    {"season_type": "Cool Summer", "sku_id": "SKU_BROW_007"},
    {"season_type": "Cool Summer", "sku_id": "SKU_BROW_014"},
    {"season_type": "Cool Summer", "sku_id": "SKU_BROW_017"},
    {"season_type": "Cool Summer", "sku_id": "SKU_BROW_026"},
    {"season_type": "Cool Summer", "sku_id": "SKU_EYE_003"},
    {"season_type": "Cool Summer", "sku_id": "SKU_EYE_011"},
    {"season_type": "Cool Summer", "sku_id": "SKU_EYE_014"},
    {"season_type": "Cool Summer", "sku_id": "SKU_EYE_023"},
    {"season_type": "Cool Summer", "sku_id": "SKU_EYE_026"},
    {"season_type": "Cool Summer", "sku_id": "SKU_LIP_002"},
    {"season_type": "Cool Summer", "sku_id": "SKU_LIP_010"},
    {"season_type": "Cool Summer", "sku_id": "SKU_LIP_014"},
    {"season_type": "Cool Summer", "sku_id": "SKU_LIP_025"},
    {"season_type": "Cool Summer", "sku_id": "SKU_CONT_003"},
    {"season_type": "Cool Summer", "sku_id": "SKU_CONT_010"},
    {"season_type": "Cool Summer", "sku_id": "SKU_CONT_017"},
    {"season_type": "Cool Summer", "sku_id": "SKU_CONT_022"},
    {"season_type": "Cool Summer", "sku_id": "SKU_CONT_024"},
    {"season_type": "Cool Summer", "sku_id": "SKU_CONT_027"},
]

# ============================================================
# 套装推荐数据 (bundle_recommendations + bundle_items)
# ============================================================
BUNDLE_DATA = [
    {
        "bundle_id": "bundle_warm_spring_daily",
        "season_type": "Warm Spring",
        "bundle_name": "暖春日常自然妆",
        "description": "适合暖春季型的日常自然妆容组合，打造清爽阳光的男士形象",
        "items": [
            ("SKU_BASE_002", 1),  # 自然色粉底
            ("SKU_BROW_004", 2),  # 暖棕眉笔
            ("SKU_EYE_004", 3),   # 暖米眼影
            ("SKU_LIP_001", 4),   # 自然裸色唇膏
            ("SKU_CONT_001", 5),  # 浅古铜修容
        ]
    },
    {
        "bundle_id": "bundle_cool_winter_business",
        "season_type": "Cool Winter",
        "bundle_name": "冷冬商务精英妆",
        "description": "适合冷冬季型的商务妆容组合，沉稳大气展现专业形象",
        "items": [
            ("SKU_BASE_001", 1),  # 象牙白粉底
            ("SKU_BROW_001", 2),  # 自然黑眉笔
            ("SKU_EYE_003", 3),   # 灰棕眼影
            ("SKU_LIP_002", 4),   # 玫瑰豆沙唇膏
            ("SKU_CONT_003", 5),  # 冷灰阴影修容
        ]
    },
    {
        "bundle_id": "bundle_warm_autumn_outdoor",
        "season_type": "Warm Autumn",
        "bundle_name": "暖秋户外活力妆",
        "description": "适合暖秋季型的户外活力妆容，温暖自然展现阳刚之气",
        "items": [
            ("SKU_BASE_003", 1),  # 小麦色粉底
            ("SKU_BROW_002", 2),  # 深棕眉笔
            ("SKU_EYE_001", 3),   # 大地色眼影
            ("SKU_LIP_003", 4),   # 珊瑚橘唇膏
            ("SKU_CONT_005", 5),  # 暖古铜修容
        ]
    },
    {
        "bundle_id": "bundle_cool_summer_casual",
        "season_type": "Cool Summer",
        "bundle_name": "冷夏休闲清爽妆",
        "description": "适合冷夏季型的休闲妆容，清爽低调展现绅士风度",
        "items": [
            ("SKU_BASE_008", 1),  # 自然白皙BB霜
            ("SKU_BROW_003", 2),  # 灰棕眉笔
            ("SKU_EYE_014", 3),   # 石板灰眼影
            ("SKU_LIP_010", 4),   # 淡粉润唇膏
            ("SKU_CONT_022", 5),  # 自然阴影修容
        ]
    },
    {
        "bundle_id": "bundle_warm_spring_date",
        "season_type": "Warm Spring",
        "bundle_name": "暖春约会精致妆",
        "description": "适合暖春季型的约会妆容，精致有型提升个人魅力",
        "items": [
            ("SKU_BASE_012", 1),  # 兰蔻自然色气垫
            ("SKU_BROW_011", 2),  # 浅棕三合一眉笔
            ("SKU_EYE_008", 3),   # 卡其单色眼影
            ("SKU_LIP_005", 4),   # MAC裸粉唇膏
            ("SKU_CONT_004", 5),  # 暖调高光
        ]
    },
    {
        "bundle_id": "bundle_cool_winter_party",
        "season_type": "Cool Winter",
        "bundle_name": "冷冬派对型格妆",
        "description": "适合冷冬季型的派对妆容，深邃有型展现独特品味",
        "items": [
            ("SKU_BASE_015", 1),  # MAC白皙粉底
            ("SKU_BROW_005", 2),  # MAC炭黑眉笔
            ("SKU_EYE_006", 3),   # 炭灰眼影
            ("SKU_LIP_007", 4),   # MAC砖红唇膏
            ("SKU_CONT_011", 5),  # 冷灰阴影膏
        ]
    },
    {
        "bundle_id": "bundle_warm_autumn_interview",
        "season_type": "Warm Autumn",
        "bundle_name": "暖秋面试干练妆",
        "description": "适合暖秋季型的面试妆容，干净利落给人可靠印象",
        "items": [
            ("SKU_BASE_007", 1),  # 深色BB霜
            ("SKU_BROW_010", 2),  # 欧莱雅深棕眉笔
            ("SKU_EYE_005", 3),   # 摩卡单色眼影
            ("SKU_LIP_004", 4),   # 焦糖润色唇膏
            ("SKU_CONT_006", 5),  # 自然阴影修容
        ]
    },
    {
        "bundle_id": "bundle_cool_summer_wedding",
        "season_type": "Cool Summer",
        "bundle_name": "冷夏婚礼优雅妆",
        "description": "适合冷夏季型的婚礼妆容，优雅得体展现绅士气质",
        "items": [
            ("SKU_BASE_022", 1),  # 科颜氏肤色隔离
            ("SKU_BROW_007", 2),  # MAC灰棕眉笔
            ("SKU_EYE_020", 3),   # 冷调提亮笔
            ("SKU_LIP_014", 4),   # 欧莱雅柔粉唇彩
            ("SKU_CONT_017", 5),  # 香奈儿冷灰阴影
        ]
    },
    {
        "bundle_id": "bundle_entry_starter",
        "season_type": "Warm Spring",
        "bundle_name": "新手入门基础套装",
        "description": "适合彩妆新手的入门套装，简单易用快速上手",
        "items": [
            ("SKU_BASE_009", 1),  # 曼秀雷敦自然健康BB霜
            ("SKU_BROW_016", 2),  # 曼秀雷敦深棕眉笔
            ("SKU_LIP_011", 3),   # 曼秀雷敦自然裸色润唇膏
            ("SKU_CONT_025", 4),  # 曼秀雷敦柔和塑形修容
        ]
    },
    {
        "bundle_id": "bundle_premium_luxury",
        "season_type": "Cool Winter",
        "bundle_name": "高端奢享全系列",
        "description": "汇集顶级品牌的高端男士彩妆套装，尽享奢华体验",
        "items": [
            ("SKU_BASE_011", 1),  # 兰蔻明亮白气垫
            ("SKU_BROW_024", 2),  # 香奈儿炭黑眉笔
            ("SKU_EYE_015", 3),   # 香奈儿暖米打底眼影
            ("SKU_EYE_016", 4),   # 香奈儿大地过渡眼影
            ("SKU_LIP_020", 5),   # 香奈儿玫瑰豆沙唇釉
            ("SKU_CONT_014", 6),  # 香奈儿阴影色修容
            ("SKU_CONT_015", 7),  # 香奈儿高光色修容
        ]
    },
]


# ============================================================
# 数据库写入函数
# ============================================================

def seed_all():
    """执行完整的种子数据写入"""
    print("=" * 60)
    print("智颜方正 - 商品种子数据初始化")
    print("=" * 60)

    conn = db_manager.get_db_connection()
    now = db_manager.now_iso()

    try:
        # 1. 清理旧的 seed_v2 数据
        print("\n[1/6] 清理旧种子数据...")
        conn.execute("DELETE FROM product_color_profiles WHERE source = ?", (SOURCE_TAG,))
        conn.execute("DELETE FROM bundle_items WHERE bundle_id IN (SELECT bundle_id FROM bundle_recommendations WHERE description LIKE '%seed_v2%')")
        # 先删除 bundle_items（有外键约束）
        bundle_ids = [b['bundle_id'] for b in BUNDLE_DATA]
        if bundle_ids:
            placeholders = ','.join(['?'] * len(bundle_ids))
            conn.execute(f"DELETE FROM bundle_items WHERE bundle_id IN ({placeholders})", bundle_ids)
        conn.execute("DELETE FROM bundle_recommendations WHERE bundle_id IN (SELECT bundle_id FROM bundle_recommendations WHERE bundle_id LIKE 'bundle_%')")
        conn.execute("DELETE FROM season_sku_map WHERE source = ?", (SOURCE_TAG,))
        conn.execute("DELETE FROM season_rules WHERE source = ?", (SOURCE_TAG,))
        # 获取要删除的 SKU 对应的 SPU
        seed_sku_ids = [s['sku_id'] for s in SKU_DATA]
        if seed_sku_ids:
            placeholders = ','.join(['?'] * len(seed_sku_ids))
            seed_spu_rows = conn.execute(
                f"SELECT DISTINCT spu_id FROM product_sku WHERE sku_id IN ({placeholders}) AND source = ?",
                seed_sku_ids + [SOURCE_TAG]
            ).fetchall()
            seed_spu_ids = [row['spu_id'] for row in seed_spu_rows]
            conn.execute(f"DELETE FROM product_sku WHERE source = ?", (SOURCE_TAG,))
            for spu_id in seed_spu_ids:
                still_used = conn.execute("SELECT 1 FROM product_sku WHERE spu_id = ? LIMIT 1", (spu_id,)).fetchone()
                if not still_used:
                    conn.execute("DELETE FROM product_spu WHERE spu_id = ?", (spu_id,))
        conn.commit()
        print(f"   旧数据清理完成")

        # 2. 写入 SPU 数据
        print("\n[2/6] 写入 SPU 数据...")
        spu_count = 0
        for spu in SPU_DATA:
            conn.execute(
                '''
                INSERT INTO product_spu (
                    spu_id, brand, product_name, category, apply_area, image_url, status, created_at
                ) VALUES (?, ?, ?, ?, ?, NULL, 'active', ?)
                ON CONFLICT(spu_id) DO UPDATE SET
                    brand = excluded.brand,
                    product_name = excluded.product_name,
                    category = excluded.category,
                    apply_area = excluded.apply_area,
                    status = 'active'
                ''',
                (spu['spu_id'], spu['brand'], spu['product_name'], spu['category'], spu['apply_area'], now)
            )
            spu_count += 1
        conn.commit()
        print(f"   写入 {spu_count} 个 SPU")

        # 3. 写入 SKU 数据
        print("\n[3/6] 写入 SKU 数据...")
        sku_count = 0
        for sku in SKU_DATA:
            mask_params = json.dumps({"apply_area": sku.get('apply_area', 'skin')}, ensure_ascii=False)
            render_params = json.dumps({
                "source": SOURCE_TAG,
                "shade_name": sku['shade_name'],
                "brand": next((s['brand'] for s in SPU_DATA if s['spu_id'] == sku['spu_id']), ''),
            }, ensure_ascii=False)
            conn.execute(
                '''
                INSERT INTO product_sku (
                    sku_id, spu_id, shade_name, hex_color, render_hex, render_mode, finish_type,
                    opacity, feather, transparency_max, season_match, price, stock, source,
                    mask_params, render_params, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 100, ?, ?, ?, ?)
                ON CONFLICT(sku_id) DO UPDATE SET
                    spu_id = excluded.spu_id,
                    shade_name = excluded.shade_name,
                    hex_color = excluded.hex_color,
                    render_hex = excluded.render_hex,
                    render_mode = excluded.render_mode,
                    finish_type = excluded.finish_type,
                    opacity = excluded.opacity,
                    feather = excluded.feather,
                    transparency_max = excluded.transparency_max,
                    season_match = excluded.season_match,
                    price = excluded.price,
                    stock = excluded.stock,
                    source = excluded.source,
                    mask_params = excluded.mask_params,
                    render_params = excluded.render_params
                ''',
                (
                    sku['sku_id'], sku['spu_id'], sku['shade_name'],
                    sku['hex_color'], sku['render_hex'], sku['render_mode'],
                    sku['finish_type'], sku['opacity'], sku['feather'],
                    min(sku['opacity'] + 0.1, 1.0),  # transparency_max
                    sku['season_match'], sku['price'], SOURCE_TAG,
                    mask_params, render_params, now
                )
            )
            # 同时写入 color_profile
            conn.execute(
                '''
                INSERT INTO product_color_profiles (sku_id, shade_name, hex_color, color_role, source, created_at)
                VALUES (?, ?, ?, 'primary', ?, ?)
                ''',
                (sku['sku_id'], sku['shade_name'], sku['hex_color'], SOURCE_TAG, now)
            )
            sku_count += 1
        conn.commit()
        print(f"   写入 {sku_count} 个 SKU")

        # 4. 写入季型规则
        print("\n[4/6] 写入季型规则...")
        rule_count = 0
        for rule in SEASON_RULES_DATA:
            conn.execute(
                '''
                INSERT OR REPLACE INTO season_rules (
                    season_type, tone, lips_palette, cheeks_palette, brow_palette,
                    avoid_palette, recommended_palette, source, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    rule['season_type'],
                    rule.get('tone'),
                    json.dumps(rule.get('lips_palette', []), ensure_ascii=False),
                    json.dumps(rule.get('cheeks_palette', []), ensure_ascii=False),
                    json.dumps(rule.get('brow_palette', []), ensure_ascii=False),
                    json.dumps(rule.get('avoid_palette', []), ensure_ascii=False),
                    json.dumps(rule.get('recommended_palette', []), ensure_ascii=False),
                    SOURCE_TAG,
                    now
                )
            )
            rule_count += 1
        conn.commit()
        print(f"   写入 {rule_count} 条季型规则")

        # 5. 写入季型 SKU 映射
        print("\n[5/6] 写入季型 SKU 映射...")
        map_count = 0
        for mapping in SEASON_SKU_MAP_DATA:
            conn.execute(
                '''
                INSERT INTO season_sku_map (season_type, sku_id, source, created_at)
                VALUES (?, ?, ?, ?)
                ''',
                (mapping['season_type'], mapping['sku_id'], SOURCE_TAG, now)
            )
            map_count += 1
        conn.commit()
        print(f"   写入 {map_count} 条季型映射")

        # 6. 写入套装推荐
        print("\n[6/6] 写入套装推荐...")
        bundle_count = 0
        item_count = 0
        for bundle in BUNDLE_DATA:
            conn.execute(
                '''
                INSERT INTO bundle_recommendations (bundle_id, season_type, bundle_name, description, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(bundle_id) DO UPDATE SET
                    season_type = excluded.season_type,
                    bundle_name = excluded.bundle_name,
                    description = excluded.description
                ''',
                (bundle['bundle_id'], bundle['season_type'], bundle['bundle_name'],
                 bundle['description'] + f' [{SOURCE_TAG}]', now)
            )
            bundle_count += 1
            for sku_id, sort_order in bundle['items']:
                conn.execute(
                    '''
                    INSERT INTO bundle_items (bundle_id, sku_id, sort_order)
                    VALUES (?, ?, ?)
                    ''',
                    (bundle['bundle_id'], sku_id, sort_order)
                )
                item_count += 1
        conn.commit()
        print(f"   写入 {bundle_count} 个套装，共 {item_count} 个套装项")

        # 汇总
        print("\n" + "=" * 60)
        print("种子数据写入完成!")
        print(f"  SPU:  {spu_count}")
        print(f"  SKU:  {sku_count}")
        print(f"  季型规则:  {rule_count}")
        print(f"  季型映射:  {map_count}")
        print(f"  套装推荐:  {bundle_count} (含 {item_count} 个商品)")
        print("=" * 60)

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] 种子数据写入失败: {e}")
        raise
    finally:
        conn.close()


def get_stats():
    """获取当前数据库中的种子数据统计"""
    conn = db_manager.get_db_connection()
    try:
        spu_count = conn.execute("SELECT COUNT(*) FROM product_spu").fetchone()[0]
        sku_count = conn.execute("SELECT COUNT(*) FROM product_sku").fetchone()[0]
        seed_sku_count = conn.execute("SELECT COUNT(*) FROM product_sku WHERE source = ?", (SOURCE_TAG,)).fetchone()[0]
        rule_count = conn.execute("SELECT COUNT(*) FROM season_rules").fetchone()[0]
        map_count = conn.execute("SELECT COUNT(*) FROM season_sku_map").fetchone()[0]
        bundle_count = conn.execute("SELECT COUNT(*) FROM bundle_recommendations").fetchone()[0]

        # 按品类统计
        category_stats = conn.execute(
            "SELECT spu.category, COUNT(sku.sku_id) FROM product_sku sku JOIN product_spu spu ON sku.spu_id = spu.spu_id GROUP BY spu.category"
        ).fetchall()

        print("\n数据库商品统计:")
        print(f"  SPU 总数: {spu_count}")
        print(f"  SKU 总数: {sku_count} (其中 seed_v2: {seed_sku_count})")
        print(f"  季型规则: {rule_count}")
        print(f"  季型映射: {map_count}")
        print(f"  套装推荐: {bundle_count}")
        print("\n  品类分布:")
        for row in category_stats:
            print(f"    {row[0]}: {row[1]} SKU")
    finally:
        conn.close()


if __name__ == '__main__':
    seed_all()
    get_stats()
