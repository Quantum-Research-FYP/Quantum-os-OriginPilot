#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import yaml
import re
import threading
import json
import tarfile
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from Util import run_cmd, docker_compose_up, check_service_running, SERVICE_NAME, COMPOSE_FILE, PID_FILE
import signal
import sys
import logging

logger = logging.getLogger(__name__)
server = None
exit_event = threading.Event()

HTTP_PORT = 18080
upgrade_lock = threading.Lock()
UPGRADE_DIR = Path("/opt/PilotOS-Upgrade")


def handle_exit(signum, frame):
    print(f"[INFO] 收到信号 {signum}，准备退出")

    exit_event.set()   # 通知主线程退出
    
    global server
    if server:
        # 让 serve_forever() 立刻返回
        server.shutdown()
        server.server_close()

    # 给后台线程一点时间收尾
    threading.Timer(0.5, sys.exit, args=(0,)).start()

def load_docker(dst):
    run_cmd(["sudo", "docker", "load", "-i", str(dst)])

def load_image_from_upgrade_dir(package_name):
    archive = UPGRADE_DIR / package_name

    if not archive.exists():
        raise RuntimeError(f"升级包不存在: {archive}")

    logger.info(f"使用升级包: {archive}")

    tmp_dir = Path("/tmp/pilotos_upgrade")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(tmp_dir)

    image_files = list(tmp_dir.glob("*.iso"))
    if not image_files:
        raise RuntimeError("升级包中未找到镜像 iso 文件")

    image = image_files[0]
    dst = Path.cwd() / image.name
    shutil.copy(image, dst)

    logger.info(f" 加载镜像: {dst}")
    load_docker(dst)
    
def load_compose():
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
    
def save_compose(data):
    with open(COMPOSE_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False)


def increment_image_version(package_name):
    """
    根据升级包名解析镜像版本
    返回格式保持不变：name:version

    例如：
    pilotos-3.17-260108.tar.gz -> pilotos:3.18
    """
    filename = Path(package_name).name

    m = re.match(r"^(?P<name>[^-]+)-(?P<version>\d+\.\d+)-(?P<date>\d+)\.", filename)
    if not m:
        raise RuntimeError(f"无法从升级包名解析版本: {filename}")

    name = m.group("name")
    version = m.group("version")

    return f"{name}:{version}"


def do_upgrade(package_name):
    with upgrade_lock:
        logger.info(f"=== 开始升级，升级包: {package_name} ===")

        load_image_from_upgrade_dir(package_name)

        data = load_compose()
        old_image = data["services"][SERVICE_NAME]["image"]
        new_image = increment_image_version(package_name)

        data["services"][SERVICE_NAME]["image"] = new_image
        save_compose(data)

        logger.info(f" 镜像升级: {old_image} -> {new_image}")

        docker_compose_up()
        check_service_running()

        logger.info("=== 升级完成 ===")

class UpgradeHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global count
        if self.path != "/upgrade":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        
        data = json.loads(body or "{}")

        package = data.get("package")
        if not package:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(
                json.dumps({"status": "error", "msg": "missing package field"}).encode()
            )
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        # self.wfile.write(json.dumps({"status": "accepted", "msg": "package received, upgrade started"}).encode())
        self.wfile.write(json.dumps({"status": "success"}).encode())

        try:
            
            threading.Thread(
                target=do_upgrade,
                args=(package,),
                daemon=True
            ).start()
            # do_upgrade(package)
            # self.wfile.write(json.dumps({"status": "success"}).encode())
        except Exception as e:
            # self.wfile.write(
            #     json.dumps({"status": "error", "msg": str(e)}).encode()
            # )
            logger.info(f"[ERROR] 镜像升级失败")

def heartbeat_loop(interval=30):
    """
    周期性心跳，证明进程仍然存活
    """
    while not exit_event.is_set():
        logger.info("heartbeat: upgrade daemon alive")
        exit_event.wait(interval)

def start_http_server():
    global server
    server = HTTPServer(("0.0.0.0", HTTP_PORT), UpgradeHandler)
    logger.info(f" 升级监听服务启动，端口 {HTTP_PORT}")
    server.serve_forever()
    
LOCK_FILE = "/tmp/pilotos-upgrade.lock"

def acquire_lock():
    import fcntl
    lock_fd = open(LOCK_FILE, "w")
    logger.error(f"lock file realpath: {os.path.realpath(LOCK_FILE)} pid={os.getpid()}")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        logger.info("获取锁成功，准备启动升级服务")
    except BlockingIOError:
        logger.error("升级服务已在运行")
        raise RuntimeError("服务已在运行")
    return lock_fd

def daemonize():
    if os.path.exists(PID_FILE):
        raise RuntimeError("升级服务已经在运行")

    if os.fork() > 0:
        sys.exit(0)   # 父进程退出

    os.setsid()       # 脱离终端

    if os.fork() > 0:
        sys.exit(0)   # 防止重新获取终端

    sys.stdout.flush()
    sys.stderr.flush()

    with open("/dev/null", "rb", 0) as f:
        os.dup2(f.fileno(), sys.stdin.fileno())
    with open("/dev/null", "ab", 0) as f:
        os.dup2(f.fileno(), sys.stdout.fileno())
        os.dup2(f.fileno(), sys.stderr.fileno())
    
    # 写 pid
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    # 进程退出时删除 pid
    import atexit
    atexit.register(lambda: os.remove(PID_FILE))
    logger.info("=== 已转换为守护进程 ===")

def start_Upgrade_process():
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)
    t = threading.Thread(target=start_http_server, daemon=True)
    t.start()
    
    # 心跳线程
    t_heartbeat = threading.Thread(
        target=heartbeat_loop,
        name="heartbeat",
        daemon=True
    )
    t_heartbeat.start()
    logger.info("=== 升级服务启动成功 ===")

    while not exit_event.is_set():
        time.sleep(1)

    logger.info("主线程退出")
    sys.exit(0)
    # logger.info("进入监听状态")
    # while True:
    #     time.sleep(3600)