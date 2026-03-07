import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'app_data.db')
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'schema.sql')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表结构"""
    # 确保存储目录已建立
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_db_connection()
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"数据库初始化完成，路径: {DB_PATH}")

def insert_upload(group_id, filename, file_path):
    """插入原图记录"""
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO uploads (group_id, filename, file_path) VALUES (?, ?, ?)',
        (group_id, filename, file_path)
    )
    conn.commit()
    conn.close()

def insert_debug(group_id, filename, file_path, blur_score=None):
    """插入调试图片记录"""
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO debug_images (group_id, filename, file_path, blur_score) VALUES (?, ?, ?, ?)',
        (group_id, filename, file_path, blur_score)
    )
    conn.commit()
    conn.close()

def insert_corrected(group_id, filename, file_path, correction_angle=None):
    """插入矫正结果记录"""
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO corrected_images (group_id, filename, file_path, correction_angle) VALUES (?, ?, ?, ?)',
        (group_id, filename, file_path, correction_angle)
    )
    conn.commit()
    conn.close()

def insert_makeup(group_id, style, filename, file_path):
    """插入美妆结果记录"""
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO makeup_images (group_id, style, filename, file_path) VALUES (?, ?, ?, ?)',
        (group_id, style, filename, file_path)
    )
    conn.commit()
    conn.close()

def get_full_history(group_id):
    """根据 Group ID 查询该次处理流程的所有关联记录"""
    conn = get_db_connection()
    
    upload = conn.execute('SELECT * FROM uploads WHERE group_id = ?', (group_id,)).fetchone()
    debugs = conn.execute('SELECT * FROM debug_images WHERE group_id = ?', (group_id,)).fetchall()
    corrected = conn.execute('SELECT * FROM corrected_images WHERE group_id = ?', (group_id,)).fetchone()
    
    conn.close()
    
    return {
        'upload': dict(upload) if upload else None,
        'debug_images': [dict(row) for row in debugs],
        'corrected': dict(corrected) if corrected else None
    }
