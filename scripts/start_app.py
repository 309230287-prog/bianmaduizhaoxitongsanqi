from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_URL = "http://127.0.0.1:8000/phase2"


def main() -> None:
    parser = argparse.ArgumentParser(description="启动商品智能匹配系统")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--no-browser", action="store_true", help="只启动服务，不自动打开浏览器")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    if _is_port_open(args.host, args.port):
        print(f"服务已经在运行：{args.url}")
        if not args.no_browser:
            webbrowser.open(args.url)
        return

    if not args.no_browser:
        threading.Thread(
            target=_open_browser_when_ready,
            args=(args.host, args.port, args.url),
            daemon=True,
        ).start()

    print(f"正在启动商品智能匹配系统：{args.url}")
    print("关闭这个窗口，服务就会停止。")

    import uvicorn
    from product_matcher.app import app

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,
        log_level="warning",
    )


def _open_browser_when_ready(host: str, port: int, url: str) -> None:
    for _ in range(80):
        if _is_port_open(host, port):
            webbrowser.open(url)
            return
        time.sleep(0.25)
    print(f"服务启动较慢，请稍后手动打开：{url}")


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


if __name__ == "__main__":
    main()
