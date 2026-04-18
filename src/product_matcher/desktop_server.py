from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn

from product_matcher.app import app


def main() -> None:
    parser = argparse.ArgumentParser(description="商品智能匹配系统桌面后端服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18765)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    os.chdir(repo_root)
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
