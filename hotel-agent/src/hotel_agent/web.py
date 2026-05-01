from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .agent import run_demo_reply, run_llm_turn
from .store import HotelStore
from .tools import run_tool


STATIC_DIR = Path(__file__).resolve().parent / "static"
DEFAULT_DATA_DIR = "hotel_data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    data_path = os.environ.get("HOTEL_DATA_DIR") or os.environ.get("HOTEL_DATA_FILE") or DEFAULT_DATA_DIR
    store = HotelStore(data_path=data_path)
    store.load_or_seed_demo()
    app.state.store = store
    yield


class ChatBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    mode: str = Field("auto", description="auto | demo | llm")

    @field_validator("mode")
    @classmethod
    def normalize_mode(cls, v: str) -> str:
        allowed = {"auto", "demo", "llm"}
        if v not in allowed:
            return "auto"
        return v


class RoomCreateBody(BaseModel):
    number: str = Field(..., min_length=1, max_length=20)
    floor: int = Field(..., ge=0, le=200)
    room_type: str = Field(..., min_length=1, max_length=50)
    status: str = Field("vacant")

    @field_validator("status")
    @classmethod
    def normalize_status(cls, v: str) -> str:
        allowed = {"vacant", "occupied", "dirty", "maintenance"}
        if v not in allowed:
            raise ValueError("status must be one of vacant/occupied/dirty/maintenance")
        return v


def _resolve_mode(body: ChatBody) -> str:
    if body.mode == "demo":
        return "demo"
    if body.mode == "llm":
        return "llm"
    if os.environ.get("OPENAI_API_KEY") or os.environ.get("ARK_API_KEY"):
        return "llm"
    return "demo"


def _fallback_demo_reply(store: HotelStore, user_message: str, reason: str) -> str:
    demo = run_demo_reply(store, user_message)
    reason_text = "LLM 服务暂时不可用，请稍后重试。"
    if "InvalidEndpoint.ClosedEndpoint" in reason:
        reason_text = "当前模型端点已关闭或不可用。"
    elif "Missing API key" in reason:
        reason_text = "未检测到可用的 API Key。"
    return f"LLM 当前不可用，已自动切换到演示模式。\n原因：{reason_text}\n\n{demo}"


def create_app() -> FastAPI:
    app = FastAPI(title="Hotel Agent", lifespan=lifespan)

    if STATIC_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": "服务内部异常，请稍后重试。"},
        )

    @app.get("/")
    async def index():
        index_path = STATIC_DIR / "index.html"
        if not index_path.is_file():
            return JSONResponse(
                {"detail": "Web UI missing. Reinstall package with static files."},
                status_code=500,
            )
        return FileResponse(index_path, media_type="text/html; charset=utf-8")

    @app.get("/api/rooms")
    async def api_rooms(request: Request):
        store: HotelStore = request.app.state.store
        out = run_tool(store, "list_rooms", "{}")
        return json.loads(out)

    @app.post("/api/rooms")
    async def api_create_room(request: Request, body: RoomCreateBody):
        store: HotelStore = request.app.state.store
        try:
            room = store.create_room(
                number=body.number,
                floor=body.floor,
                room_type=body.room_type,
                status=body.status,
            )
            return {
                "id": room.id,
                "number": room.number,
                "floor": room.floor,
                "room_type": room.room_type,
                "status": room.status.value,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @app.post("/api/chat")
    async def api_chat(request: Request, body: ChatBody):
        store: HotelStore = request.app.state.store
        mode = _resolve_mode(body)
        requested_mode = body.mode
        if mode == "llm":
            if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("ARK_API_KEY")):
                raise HTTPException(
                    status_code=400,
                    detail="LLM 模式需要设置 OPENAI_API_KEY 或 ARK_API_KEY，或改用 mode=demo。",
                )
            try:
                reply = run_llm_turn(store, body.message)
            except RuntimeError as e:
                if requested_mode == "auto":
                    return {
                        "reply": _fallback_demo_reply(store, body.message, str(e)),
                        "mode": "demo",
                    }
                raise HTTPException(status_code=503, detail=str(e)) from e
            except Exception as e:
                if requested_mode == "auto":
                    return {
                        "reply": _fallback_demo_reply(store, body.message, str(e)),
                        "mode": "demo",
                    }
                # Normalize unexpected upstream/provider errors into JSON.
                raise HTTPException(status_code=502, detail=f"LLM 调用失败：{e}") from e
        else:
            reply = run_demo_reply(store, body.message)
        return {"reply": reply, "mode": mode}

    return app


app = create_app()
