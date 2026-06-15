#!/usr/bin/env python3
import subprocess
import time
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)


# ================== 配置 ==================
SERVICE_NAME = "pilotos"
COMPOSE_FILE = Path("docker-compose.yml")
PID_FILE = "/var/run/autodeploy_upgrade.pid"
# ==========================================

def run_cmd(cmd, check=True):
    logger.info(f"[CMD] {' '.join(cmd)}")
    p = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if check and p.returncode != 0:
        logger.info(p.stderr)
        raise RuntimeError(p.stderr)
    return p.stdout.strip()


def docker_compose_up():
    # run_cmd(["sudo", "docker", "stop", "pilotos-server"])
    # run_cmd(["sudo", "docker", "rm", "pilotos-server"])
    run_cmd(["sudo", "docker", "compose", "down"])
    run_cmd(["sudo", "docker", "compose", "up", "-d"])


def check_service_running():
    time.sleep(3)
    out = run_cmd(
        ["sudo", "docker", "compose", "ps", "--services", "--filter", "status=running"],
        check=False
    )
    if SERVICE_NAME not in out.splitlines():
        return False
    logger.info(f"[OK] {SERVICE_NAME} 正在运行")
    return True
    

def run_with_retry(func, run_stage, max_retry=3):
    for i in range(1, max_retry + 1):
        try:
            return func()   # 成功直接返回
        except Exception as e:
            logger.info(f"第 {i} 次运行 {run_stage} 失败：{e}")
            if i == max_retry:
                raise       # 最后一次失败，抛出异常
            time.sleep(1)   # 可选：重试前等待

def is_autodeploy_running():
    if not os.path.exists(PID_FILE):
        return False
    return True