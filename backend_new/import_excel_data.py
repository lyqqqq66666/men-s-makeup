"""
将 Excel 真实商品数据导入 SQLite 数据库
数据来源: ZhiYan_split_frontend_backend_catalog.xlsx
"""
import sqlite3
import pandas as pd
import json
from datetime import datetime

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "database", "app_data.db")
EXCEL_PATH = os.path.join(PROJECT_DIR, "ZhiYan_split_frontend_backend_catalog.xlsx")

# 分类到 category 的映射
CATEGORY_MAP = {
    "底妆": "base",
    "眉毛": "brow",
    "眼妆": "eye",
    "修容": "contour",
    "唇部": "lip",
}

# 分类到 apply_area 的映射
APPLY_AREA_MAP = {
    "底妆": "skin",
    "眉毛": "brow",
    "眼妆": "eyes",
    "修容": "face",
    "唇部": "lips",
}

# 风格标签到 finish_type 的映射
FINISH_MAP = {
    "clean": "natural",
    "office": "semi-matte",
    "trendy": "glossy",
    "party": "matte",
}

def main():
    xlsx = pd.ExcelFile(EXCEL_PATH)
    df_front = pd.read_excel(xlsx, sheet_name='Frontend_Catalog', header=1)
    df_back = pd.read_excel(xlsx, sheet_name='Backend_Render_Params', header=1)

    # 合并前后端数据
    df = df_front.merge(df_back[["SKU ID", "上妆区域", "渲染HEX", "透明度/强度", "羽化值", "最大透明度", "备注"]],
                         on="SKU ID", how="left")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 收集所有 SPU（按 品牌+产品名 分组）
    spu_map = {}  # (brand, product_name) -> spu_id
    spu_list = []

    # 收集所有 SKU
    sku_list = []
    season_sku_list = []

    for _, row in df.iterrows():
        category_cn = str(row["分类"]).strip()
        category = CATEGORY_MAP.get(category_cn, "base")
        apply_area = APPLY_AREA_MAP.get(category_cn, "skin")
        sku_id = str(row["SKU ID"]).strip()
        brand = str(row["品牌"]).strip()
        product_name = str(row["产品名"]).strip()
        shade_name = str(row["色号"]).strip()
        hex_color = str(row["色卡HEX"]).strip()
        price = float(row["价格"]) if pd.notna(row["价格"]) else 0
        season_match = str(row["适配季型"]).strip() if pd.notna(row["适配季型"]) else ""
        style_tag = str(row["风格标签"]).strip() if pd.notna(row["风格标签"]) else ""
        source_url = str(row["官方来源"]).strip() if pd.notna(row["官方来源"]) else ""

        # 后端渲染参数
        render_hex = str(row.get("渲染HEX", hex_color)).strip()
        opacity = float(row["透明度/强度"]) if pd.notna(row.get("透明度/强度")) else 0.5
        feather = float(row["羽化值"]) if pd.notna(row.get("羽化值")) else 0.3
        transparency_max = float(row["最大透明度"]) if pd.notna(row.get("最大透明度")) else 0.95
        render_area = str(row.get("上妆区域", apply_area)).strip()

        finish_type = FINISH_MAP.get(style_tag, "natural")
        render_mode = 0

        # SPU
        spu_key = (brand, product_name)
        if spu_key not in spu_map:
            spu_id = f"SPU_{sku_id}"
            spu_map[spu_key] = spu_id
            spu_list.append((spu_id, brand, product_name, category, apply_area, "", "active", now))

        spu_id = spu_map[spu_key]

        # mask_params 和 render_params
        mask_params = json.dumps({"apply_area": render_area})
        render_params = json.dumps({"render_mode": render_mode, "blend_mode": "normal"})

        # SKU
        sku_list.append((
            sku_id, spu_id, shade_name, hex_color, render_hex,
            render_mode, finish_type, opacity, feather, transparency_max,
            season_match, price, 100, "excel_real", mask_params, render_params, now
        ))

        # 季型映射
        if season_match:
            season_sku_list.append((season_match, sku_id, "excel_real", now))

    # 插入 SPU
    cur.executemany("""
        INSERT OR IGNORE INTO product_spu (spu_id, brand, product_name, category, apply_area, image_url, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, spu_list)
    print(f"插入 SPU: {cur.rowcount} 条")

    # 插入 SKU
    cur.executemany("""
        INSERT OR IGNORE INTO product_sku (sku_id, spu_id, shade_name, hex_color, render_hex,
            render_mode, finish_type, opacity, feather, transparency_max,
            season_match, price, stock, source, mask_params, render_params, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, sku_list)
    print(f"插入 SKU: {cur.rowcount} 条")

    # 插入季型-SKU映射
    cur.executemany("""
        INSERT OR IGNORE INTO season_sku_map (season_type, sku_id, source, created_at)
        VALUES (?, ?, ?, ?)
    """, season_sku_list)
    print(f"插入季型映射: {cur.rowcount} 条")

    # 重建季型规则
    rebuild_season_rules(cur, now)

    conn.commit()

    # 验证
    cur.execute("SELECT COUNT(*) FROM product_sku")
    print(f"\n数据库 SKU 总数: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM product_spu")
    print(f"数据库 SPU 总数: {cur.fetchone()[0]}")
    cur.execute("""
        SELECT s.category, COUNT(sk.sku_id) 
        FROM product_spu s JOIN product_sku sk ON s.spu_id = sk.spu_id 
        GROUP BY s.category
    """)
    print("\n品类分布:")
    for r in cur.fetchall():
        print(f"  {r[0]}: {r[1]}")
    cur.execute("SELECT DISTINCT brand FROM product_spu ORDER BY brand")
    print("\n品牌列表:")
    for r in cur.fetchall():
        print(f"  {r[0]}")

    conn.close()
    print("\n导入完成！")


def rebuild_season_rules(cur, now):
    cur.execute("DELETE FROM season_rules")
    season_tones = {
        "Warm Spring": "warm",
        "Warm Autumn": "warm",
        "Cool Summer": "cool",
        "Cool Winter": "cool",
    }
    for season, tone in season_tones.items():
        cur.execute("""
            INSERT OR IGNORE INTO season_rules (season_type, tone, lips_palette, cheeks_palette, brow_palette,
                avoid_palette, recommended_palette, source, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            season, tone,
            json.dumps([]), json.dumps([]), json.dumps([]),
            json.dumps([]), json.dumps([]),
            "excel_real", now
        ))
    print(f"重建季型规则: {len(season_tones)} 条")


if __name__ == "__main__":
    main()
