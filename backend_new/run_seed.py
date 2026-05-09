# -*- coding: utf-8 -*-
"""
智颜方正 - 数据库种子数据初始化脚本

用法:
    python run_seed.py              # 初始化数据库结构 + 写入种子数据
    python run_seed.py --seed-only  # 仅写入种子数据（不重建表结构）
    python run_seed.py --stats      # 仅查看当前数据库统计
"""

import os
import sys

# 将 backend_new 目录加入 path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

import db_manager
from data.seed_products import seed_all, get_stats


def main():
    args = sys.argv[1:]

    if '--stats' in args:
        print("查看数据库统计...")
        get_stats()
        return

    if '--seed-only' not in args:
        # 先初始化数据库结构
        print("初始化数据库表结构...")
        db_manager.init_db()

    # 写入种子数据
    seed_all()

    # 显示统计
    get_stats()


if __name__ == '__main__':
    main()
