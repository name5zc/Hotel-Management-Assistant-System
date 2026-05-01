from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .store import HotelStore
from .tools import TOOL_SPECS, run_tool

DEFAULT_ARK_MODEL = ""


def _openai_tools() -> List[Dict[str, Any]]:
    return TOOL_SPECS


def _resolve_api_key() -> Optional[str]:
    # Compatible with OpenAI and Volcengine Ark(Doubao) env naming.
    return os.environ.get("OPENAI_API_KEY") or os.environ.get("ARK_API_KEY")


def _resolve_base_url() -> Optional[str]:
    # Ark endpoint can be configured with OPENAI_BASE_URL or ARK_BASE_URL.
    return os.environ.get("OPENAI_BASE_URL") or os.environ.get("ARK_BASE_URL")


def _resolve_model(explicit_model: Optional[str]) -> str:
    model = explicit_model or os.environ.get("HOTEL_AGENT_MODEL") or os.environ.get("ARK_MODEL")
    if model:
        return model
    if os.environ.get("ARK_API_KEY"):
        return DEFAULT_ARK_MODEL
    return "gpt-4o-mini"


def run_llm_turn(
    store: HotelStore,
    user_message: str,
    *,
    model: Optional[str] = None,
    max_rounds: int = 8,
) -> str:
    """Run one user message through OpenAI chat with tool calls until assistant text reply."""
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError('Install LLM support: pip install -e ".[llm]"') from e

    api_key = _resolve_api_key()
    if not api_key:
        raise RuntimeError("Missing API key: set OPENAI_API_KEY or ARK_API_KEY.")

    base_url = _resolve_base_url()
    client = OpenAI(api_key=api_key, base_url=base_url)
    model_name = _resolve_model(model)
    messages: List[Dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a hotel operations assistant. Use tools to read/update the hotel "
                "PMS. For policy/SOP/pricing questions, call search_policy first and answer "
                "with concise evidence. Be concise. After tools succeed, summarize for the user."
            ),
        },
        {"role": "user", "content": user_message},
    ]
    tools = _openai_tools()

    for _ in range(max_rounds):
        resp = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        choice = resp.choices[0]
        msg = choice.message
        if msg.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments or "{}",
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )
            for tc in msg.tool_calls:
                name = tc.function.name
                out = run_tool(store, name, tc.function.arguments or "{}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": out,
                    }
                )
            continue
        text = (msg.content or "").strip()
        if text:
            return text
        return "(empty assistant reply)"

    return "(max tool rounds exceeded)"


def run_demo_reply(store: HotelStore, user_message: str) -> str:
    """Rule-based demo when no API key: call a simple tool chain and narrate."""
    text = user_message.strip().lower()
    if any(k in text for k in ("空", "房态", "房间", "room")) or "list" in text:
        out = run_tool(store, "list_rooms", "{}")
        data = json.loads(out)
        lines = ["当前房态："]
        for r in data.get("rooms", []):
            lines.append(f"  {r['number']} ({r['room_type']}) — {r['status']}")
        return "\n".join(lines) if len(lines) > 1 else out

    if "帮助" in user_message or "help" in text:
        return (
            "演示模式：你可以问「有哪些房间」「房态」查看列表；"
            "配置 OPENAI_API_KEY 或 ARK_API_KEY 后可用 `hotel-agent chat` 或 `hotel-agent web` 做全流程操作。"
        )

    return (
        "演示模式仅支持简单房态查询。"
        "如需完整能力，请切换到可用的 LLM 模式。"
    )
