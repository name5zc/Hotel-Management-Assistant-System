from __future__ import annotations

import argparse
import os
import sys

from .store import HotelStore
from .agent import run_demo_reply, run_llm_turn

DEFAULT_DATA_DIR = "hotel_data"


def _has_llm_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("ARK_API_KEY"))


def _new_store() -> HotelStore:
    data_path = os.environ.get("HOTEL_DATA_DIR") or os.environ.get("HOTEL_DATA_FILE") or DEFAULT_DATA_DIR
    store = HotelStore(data_path=data_path)
    store.load_or_seed_demo()
    return store


def cmd_demo() -> None:
    store = _new_store()
    print("酒店管理 Agent — 演示模式（输入 quit 退出）\n")
    while True:
        try:
            line = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line or line.lower() in ("q", "quit", "exit"):
            break
        print("Agent:", run_demo_reply(store, line))
        print()


def cmd_chat() -> None:
    if not _has_llm_key():
        print("请设置环境变量 OPENAI_API_KEY 或 ARK_API_KEY。", file=sys.stderr)
        sys.exit(1)
    store = _new_store()
    print("酒店管理 Agent — LLM 模式（输入 quit 退出）\n")
    while True:
        try:
            line = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line or line.lower() in ("q", "quit", "exit"):
            break
        try:
            reply = run_llm_turn(store, line)
        except RuntimeError as e:
            print(e, file=sys.stderr)
            sys.exit(1)
        print("Agent:", reply)
        print()


def cmd_web(host: str, port: int) -> None:
    try:
        import uvicorn
    except ImportError:
        print('请先安装 Web 依赖：pip install -e ".[web]"', file=sys.stderr)
        sys.exit(1)
    print(f"打开浏览器访问 http://{host}:{port}/")
    uvicorn.run(
        "hotel_agent.web:app",
        host=host,
        port=port,
        factory=False,
    )


def main() -> None:
    p = argparse.ArgumentParser(prog="hotel-agent", description="Hotel management agent CLI")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo", help="Interactive demo without API keys")
    sub.add_parser(
        "chat",
        help="Chat with LLM tool calling (needs OPENAI_API_KEY or ARK_API_KEY)",
    )
    wp = sub.add_parser("web", help="Web UI (FastAPI + browser)")
    wp.add_argument("--host", default="127.0.0.1", help="Bind host")
    wp.add_argument("--port", type=int, default=8000, help="Bind port")
    args = p.parse_args()
    if args.cmd == "demo":
        cmd_demo()
    elif args.cmd == "chat":
        cmd_chat()
    elif args.cmd == "web":
        cmd_web(args.host, args.port)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
