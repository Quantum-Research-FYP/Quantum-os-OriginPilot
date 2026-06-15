#!/usr/bin/env python3
# AutoDeploy.py - 一键部署 PilotOS 系统

import os
import sys
import subprocess
import logging
import yaml
from pathlib import Path
from datetime import datetime

# 创建 logs 目录（可选）
# LOGS_DIR = Path("./mysqlInit/logs")
# LOGS_DIR.mkdir(exist_ok=True)

# # 生成带时间戳的日志文件名
# timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# log_file = LOGS_DIR / f"pilotos_deploy_{timestamp}.log"

# # 配置日志
# #logging.basicConfig(
# #    level=logging.INFO,
# #    format="%(asctime)s [%(levelname)s] %(message)s",
# #    handlers=[logging.StreamHandler()]
# #)

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

# # 创建 formatter
# formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# # 控制台处理器（StreamHandler）
# console_handler = logging.StreamHandler()
# console_handler.setFormatter(formatter)

# # 文件处理器（FileHandler）
# file_handler = logging.FileHandler(log_file, encoding="utf-8")
# file_handler.setFormatter(formatter)

# # 添加处理器
# logger.addHandler(console_handler)
# logger.addHandler(file_handler)

logger = logging.getLogger(__name__)


# 项目根目录（假设 AutoDeploy.py 在根目录）
PROJECT_ROOT = Path(__file__).parent.resolve()


import pymysql

def ensure_database_exists(db_config):
    """确保目标数据库存在，不存在则创建"""
    logger.info(f"🔍 检查数据库 {db_config['database']} 是否存在...")

    # 连接时不指定数据库（连接到 MySQL 默认库）
    conn = pymysql.connect(
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["username"],
        password=db_config["password"],
        charset="utf8mb4"
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute("SHOW DATABASES LIKE %s", (db_config["database"],))
            if not cursor.fetchone():
                logger.info(f"🆕 正在创建数据库: {db_config['database']}")
                cursor.execute(f"CREATE DATABASE `{db_config['database']}` "
                               f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                conn.commit()
            else:
                logger.info(f"✅ 数据库 {db_config['database']} 已存在")
                raise RuntimeError("数据库已存在")
    finally:
        conn.close()
        

def load_config(config_path="config.yaml"):
    """加载配置文件"""
    if not Path(config_path).exists():
        logger.error(f"配置文件 {config_path} 不存在！请先创建。")
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_database_url(db_config):
    """构建 SQLAlchemy 兼容的 DATABASE_URL"""
    from urllib.parse import quote_plus
    safe_username = quote_plus(str(db_config['username']))
    safe_password = quote_plus(str(db_config['password']))
    return (
        f"mysql+pymysql://{safe_username}:{safe_password}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )


def run_alembic_upgrade(database_url):
    """在当前环境中执行 alembic upgrade head"""
    logger.info("🔧 正在执行数据库迁移（Alembic）...")

    # 设置环境变量供 alembic/env.py 读取
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    try:
        # 调用 alembic 命令（确保 alembic 在 PATH 中，或使用 python -m alembic）
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("✅ 数据库迁移成功完成。")
        logger.info("Alembic 输出:\n%s", result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error("❌ 数据库迁移失败！")
        logger.error("标准输出:\n%s", e.stdout)
        logger.error("错误输出:\n%s", e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        logger.error("❌ 未找到 'alembic' 命令。请先安装依赖：pip install -r requirements.txt")
        sys.exit(1)


# def start_docker_container(docker_config, database_url):
#     """启动 Docker 容器"""
#     logger.info("🚀 正在启动 Docker 服务...")

#     cmd = [
#         "docker", "run", "-d",
#         "--name", docker_config["container_name"],
#         "--restart", "unless-stopped",
#         "-p", f"{docker_config['app_port']}:{docker_config['app_port']}",
#         "-e", f"DATABASE_URL={database_url}",
#         docker_config["image"]
#     ]

#     try:
#         result = subprocess.run(cmd, capture_output=True, text=True, check=True)
#         container_id = result.stdout.strip()
#         logger.info(f"✅ 服务已启动，容器 ID: {container_id}")
#         logger.info(f"应用查看地址: http://localhost:{docker_config['app_port']}")
#     except subprocess.CalledProcessError as e:
#         logger.error("❌ 启动 Docker 容器失败！")
#         logger.error("错误: %s", e.stderr)
#         sys.exit(1)
#     except FileNotFoundError:
#         logger.error("❌ 未找到 'docker' 命令，请先安装 Docker 并确保其在 PATH 中。")
#         sys.exit(1)

def insert_admin_user(db_config):
    """迁移完成后插入初始管理员账号（如果不存在）"""
    logger.info("👤 正在检查并创建初始管理员账户...")
    
    # 注意：这里需要连接到具体的 database
    conn = pymysql.connect(
        host=db_config["host"],
        port=db_config["port"],
        user=db_config["username"],
        password=db_config["password"],
        database=db_config["database"],
        charset="utf8mb4"
    )
    
    # 你的 SQL 语句（已根据你提供的代码进行了格式化）
    # 提示：请核对字段数量，你提供的 SQL 中 VALUES 比字段多了一个 'bylz'，
    # 我在这里将 'bylz' 对应到了最后一个字段。
    admin_sql = """
    INSERT INTO sys_user (
        username, password, status, role_ids, vip, api_key, realname, 
        company, salt, mark, first_name, last_name, email, 
        phone_number, passport_number, national_id, institution
    )
    SELECT 
        'admin', 'c218ae145e4f6a761fac4b67fb0276435f6e099828d1cd68deb8ff926577b18c', 
        1, '2', 1, '', '', '', 'ZWbTXy', 1, '', '', '', 'N/A', '', '', 'bylz'
    FROM dual
    WHERE NOT EXISTS (
        SELECT 1 FROM sys_user WHERE username = 'admin'
    );
    """

    try:
        with conn.cursor() as cursor:
            affected_rows = cursor.execute(admin_sql)
            conn.commit()
            if affected_rows > 0:
                logger.info("✅ 初始管理员账户 'admin' 创建成功。")
            else:
                logger.info("ℹ️ 管理员账户 'admin' 已存在，跳过插入。")
    except Exception as e:
        logger.error(f"❌ 插入管理员账户失败: {e}")
        # 这里可以选择是否退出程序，通常初始数据失败建议记录但不中断
    finally:
        conn.close()

def deploy_db():
    logger.info("🚀 开始自动部署 PilotOS 系统...")

    # 1. 加载配置
    config = load_config(config_path = './mysqlInit/config.yaml')
    db_config = config["database"]
    
    # 👇 新增：自动创建数据库
    ensure_database_exists(db_config)

    # 2. 构建数据库 URL
    database_url = build_database_url(db_config)
    database_url = database_url.replace("%", "%%")
    logger.info(f"📡 数据库地址: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url 

    # 3. 执行数据库迁移（建表/升级）
    run_alembic_upgrade(database_url)

    # === 新增步骤：插入初始数据 ===
    insert_admin_user(db_config)
    # ===========================

    # 4. 启动 Docker 服务
    #docker_config = config["docker"]
    #start_docker_container(docker_config, database_url)

    logger.info("🎉 数据库初始化完成！")


# if __name__ == "__main__":
#     main()