#!/usr/bin/env python3
import sys

import yaml
import re
import threading
import json
import tarfile
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from mysqlInit.DeployDB import deploy_db
from Upgrade import start_Upgrade_process, daemonize, acquire_lock, load_compose, load_docker, SERVICE_NAME
from Util import docker_compose_up, check_service_running, run_with_retry, is_autodeploy_running, run_cmd
from datetime import datetime
import logging
import os
import pymysql
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


# 创建 logs 目录（可选）
LOGS_DIR = Path("./deployLogs")
LOGS_DIR.mkdir(exist_ok=True)

# 生成带时间戳的日志文件名
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = LOGS_DIR / f"pilotos_deploy_{timestamp}.log"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 创建 formatter
# formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] "
    "[PID:%(process)d TID:%(thread)d %(threadName)s] "
    "%(name)s: %(message)s"
)

# 控制台处理器（StreamHandler）
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# 文件处理器（FileHandler）
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setFormatter(formatter)

# 添加处理器
logger.addHandler(console_handler)
logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

def init_db():
    logger.info("start init_db")
    run_with_retry(deploy_db, "init_db")

def check_db_connections():
    """检查 MySQL 和 MongoDB 连接"""
    config_path = Path("PilotOS-Config/config.json")
    
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_path}")
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    logger.info(f"读取配置文件: {config_path}")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 检查 MySQL 连接
    logger.info("开始检查 MySQL 连接...")
    mysql_config = config.get("mysql", {})
    mysql_host = mysql_config.get("host")
    mysql_port = mysql_config.get("port", 3306)
    mysql_user = mysql_config.get("user")
    mysql_password = mysql_config.get("password")
    mysql_db = mysql_config.get("db")
    
    try:
        connection = pymysql.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password,
            database=mysql_db,
            connect_timeout=5
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        connection.close()
        logger.info(f"✓ MySQL 连接成功: {mysql_host}:{mysql_port}/{mysql_db}")
    except Exception as e:
        logger.error(f"✗ MySQL 连接失败: {mysql_host}:{mysql_port}/{mysql_db}")
        logger.error(f"错误详情: {str(e)}")
        logger.error("请检查 MySQL 配置和服务状态后重试")
        raise RuntimeError(f"MySQL 连接失败: {str(e)}")
    
    # 检查 MongoDB 连接
    logger.info("开始检查 MongoDB 连接...")
    mongodb_config = config.get("mongodb", {})
    mongodb_host = mongodb_config.get("host")
    mongodb_port = mongodb_config.get("port", 27017)
    mongodb_user = mongodb_config.get("user")
    mongodb_password = mongodb_config.get("password")
    mongodb_db = mongodb_config.get("db")
    
    try:
        # 构建连接 URI
        if mongodb_user and mongodb_password:
            uri = f"mongodb://{mongodb_user}:{mongodb_password}@{mongodb_host}:{mongodb_port}/{mongodb_db}"
        else:
            uri = f"mongodb://{mongodb_host}:{mongodb_port}/{mongodb_db}"
        
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # 测试连接
        client.server_info()
        client.close()
        logger.info(f"✓ MongoDB 连接成功: {mongodb_host}:{mongodb_port}/{mongodb_db}")
    except ConnectionFailure as e:
        logger.error(f"✗ MongoDB 连接失败: {mongodb_host}:{mongodb_port}/{mongodb_db}")
        logger.error(f"错误详情: {str(e)}")
        logger.error("请检查 MongoDB 配置和服务状态后重试")
        raise RuntimeError(f"MongoDB 连接失败: {str(e)}")
    except Exception as e:
        logger.error(f"✗ MongoDB 连接失败: {mongodb_host}:{mongodb_port}/{mongodb_db}")
        logger.error(f"错误详情: {str(e)}")
        logger.error("请检查 MongoDB 配置和服务状态后重试")
        raise RuntimeError(f"MongoDB 连接失败: {str(e)}")
    
    logger.info("数据库连接检查全部通过！")

def start_services():
    logger.info("=== 启动 ===")
    # 首先检查数据库连接
    check_db_connections()
    
    if check_service_running():
        logger.info("司南镜像服务已经启动，无需再次启动")
    else:
        logger.info("正在启动司南服务")
        docker_compose_up()
        flag = check_service_running()
        if not flag:
            raise RuntimeError("服务未正常运行")
        logger.info("司南镜像服务启动成功")
    #如果升级服务没有启动，启动升级服务
    if not is_autodeploy_running():
        # 启动升级服务
        logger.info("开始启动升级服务，其余输出见日志文件")
        daemonize()
        start_Upgrade_process()
    else:
        logger.info(f"[PID={os.getpid()}]升级服务已经启动，无需再次启动")

# def run_core_config():
#     run_cmd(["ulimit", "-c", "unlimited"])
#     run_cmd(["sudo", "sysctl", "-w", "kernel.core_uses_pid=1"])
#     run_cmd(["sudo", "sysctl", "-w", "kernel.core_pattern=./core-%e-%p-%t"])

def enable_system_core_dump():
    # 1. limits (core size)
    run_cmd([
        "bash", "-c",
        """
sudo tee /etc/security/limits.d/99-core.conf <<'EOF'
* soft core unlimited
* hard core unlimited
EOF
"""
    ])

    # 2. systemd directory (FIX)
    run_cmd(["sudo", "mkdir", "-p", "/etc/systemd/system.conf.d"])

    # 3. systemd core limit
    run_cmd([
        "bash", "-c",
        """
sudo tee /etc/systemd/system.conf.d/99-core.conf <<'EOF'
[Manager]
DefaultLimitCORE=infinity
EOF
"""
    ])

    run_cmd(["sudo", "systemctl", "daemon-reexec"])

    # 4. sysctl directory
    run_cmd(["sudo", "mkdir", "-p", "/etc/sysctl.d"])

    # 5. sysctl core pattern
    run_cmd([
        "bash", "-c",
        """
sudo tee /etc/sysctl.d/99-core.conf <<'EOF'
kernel.core_uses_pid=1
kernel.core_pattern=/var/coredump/core-%e-%p-%t
EOF
"""
    ])

    run_cmd(["sudo", "sysctl", "--system"])

    # 6. core directory
    run_cmd(["sudo", "mkdir", "-p", "/var/coredump"])
    run_cmd(["sudo", "chmod", "1777", "/var/coredump"])

    # 7. optional: disable systemd-coredump
    run_cmd(["sudo", "systemctl", "disable", "systemd-coredump.socket"], check=False)
    run_cmd(["sudo", "systemctl", "stop", "systemd-coredump.socket"], check=False)



def init_docker():
    data = load_compose()
    image = data["services"][SERVICE_NAME]["image"] + '.iso'
    load_docker(image)

def print_usage():
    print("示例用法:")
    print("  python AutoDeploy.py initDB    # 初始化数据库")
    print("  python AutoDeploy.py start   # 启动镜像和升级服务")    


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "initDB":
        init_db()
    elif cmd == "loadImage":
        init_docker()
    elif cmd == "start":
        enable_system_core_dump()
        start_services()
    else:
        print(f"未知命令: {cmd}")
        print_usage()
        sys.exit(1)
