# 数据库配置
# 支持 SQLite 和 MySQL 两种模式

import os

# 默认使用 SQLite（开发环境）
DATABASE_TYPE = os.environ.get('DATABASE_TYPE', 'sqlite')

# SQLite 配置
SQLITE_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'database', 'app_data.db'
)

# MySQL 配置
MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', '3306')),
    'database': os.environ.get('MYSQL_DATABASE', 'menx'),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', 'Liyaq0427'),
    'charset': 'utf8mb4',
    'connect_timeout': 10
}

# 数据库连接 URL（SQLAlchemy 格式）
def get_database_url():
    if DATABASE_TYPE == 'mysql':
        return f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}?charset=utf8mb4"
    else:
        return f"sqlite:///{SQLITE_DB_PATH}"
