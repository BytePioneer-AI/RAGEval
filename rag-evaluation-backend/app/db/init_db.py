#!/usr/bin/env python3

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import subprocess
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.config import settings

def run_alembic_upgrade():
    """运行 Alembic 迁移"""
    print("运行 Alembic 迁移: alembic upgrade head")
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        print("Alembic 迁移执行成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Alembic 迁移执行失败: {e}")
        return False

def create_database():
    """创建数据库"""
    try:
        # 连接到PostgreSQL服务器
        conn = psycopg2.connect(
            host=settings.POSTGRES_SERVER,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 检查数据库是否存在
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{settings.POSTGRES_DB}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"创建数据库 {settings.POSTGRES_DB}...")
            cursor.execute(f"CREATE DATABASE {settings.POSTGRES_DB}")
            print(f"数据库 {settings.POSTGRES_DB} 创建成功")
        else:
            print(f"数据库 {settings.POSTGRES_DB} 已存在")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"创建数据库时出错: {e}")
        return False

def init_schema():
    """使用 Alembic 初始化/更新表结构"""
    return run_alembic_upgrade()

def reset_database():
    """重置数据库(删除并重新创建)"""
    try:
        # 连接到PostgreSQL服务器
        conn = psycopg2.connect(
            host=settings.POSTGRES_SERVER,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 终止所有与数据库的连接
        cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{settings.POSTGRES_DB}'
            AND pid <> pg_backend_pid();
        """)
        
        # 删除数据库
        print(f"删除数据库 {settings.POSTGRES_DB}...")
        cursor.execute(f"DROP DATABASE IF EXISTS {settings.POSTGRES_DB}")
        
        cursor.close()
        conn.close()
        
        # 重新创建数据库和表
        return create_database() and init_schema()
    except Exception as e:
        print(f"重置数据库时出错: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        print("重置数据库...")
        reset_database()
    else:
        if create_database():
            init_schema()
