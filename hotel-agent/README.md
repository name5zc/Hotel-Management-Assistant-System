# Hotel Agent

酒店管理 Agent：房间、预订、入住/退房、客房任务；工具调用 + 内存存储。演示模式无需 API Key。

## 安装

```bash
cd hotel-agent
pip install -e .
# 可选：OpenAI 兼容 API
pip install -e ".[llm]"
# 可选：浏览器 Web 界面
pip install -e ".[web]"
```

## 使用

```bash
# 交互演示（内置规则回复，不调用外网）
hotel-agent demo

# 使用环境变量 OPENAI_API_KEY 或 ARK_API_KEY（需已安装 openai）
hotel-agent chat

# Web：浏览器访问 http://127.0.0.1:8000/（需 .[web]）
hotel-agent web
hotel-agent web --host 0.0.0.0 --port 8000
```

有 API Key 时，页面里模式选「自动」或「LLM」即可用工具调用；无 Key 时用「演示」看房态。

## JSON 持久化

默认会把数据保存到启动目录下的 `hotel_data/` 目录，拆分为多个 JSON 文件：

- `hotel_data/rooms.json`
- `hotel_data/guests.json`
- `hotel_data/bookings.json`
- `hotel_data/tasks.json`

- 自定义目录：设置环境变量 `HOTEL_DATA_DIR`
- 兼容单文件：也支持 `HOTEL_DATA_FILE=xxx.json`
- 首次无文件时会写入演示种子数据
- 后续房态、预订、任务变更会自动写回 JSON

## RAG 知识库（政策检索）

项目已内置最小 RAG 工具 `search_policy`，用于检索酒店政策/SOP 文档并给出证据片段。

- 默认知识库目录：`knowledge/`
- 自定义目录：设置环境变量 `HOTEL_KB_DIR`
- 支持文件：`*.md`

示例问题（LLM 模式）：
- “退房时间和延时收费规则是什么？”
- “会员折扣有哪些？”
- “儿童早餐政策是什么？”

## 接入豆包（Ark）

豆包使用 OpenAI 兼容协议，可直接复用本项目。

```bash
pip install -e ".[llm,web]"

# PowerShell
$env:ARK_API_KEY="你的豆包Key"
$env:ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
$env:ARK_MODEL="你的endpoint或模型ID"

# 也可继续用 OPENAI_BASE_URL / HOTEL_AGENT_MODEL 命名
hotel-agent chat
# 或
hotel-agent web
```

说明：
- `ARK_API_KEY` 与 `OPENAI_API_KEY` 二选一即可。
- `ARK_BASE_URL` 推荐填豆包兼容地址；若不填，则走 SDK 默认地址。
- 已内置默认豆包 endpoint：`ep-20260428103409-pcrnx`（设置 `ARK_API_KEY` 后，不配模型也可直接用）。
- 模型优先级：`HOTEL_AGENT_MODEL` > `ARK_MODEL` > 默认值。

## 项目结构

- `src/hotel_agent/models.py` — 领域模型
- `src/hotel_agent/store.py` — 内存仓储
- `src/hotel_agent/tools.py` — Agent 可调用的工具实现与 JSON Schema
- `src/hotel_agent/agent.py` — 工具循环 / 可选 LLM 驱动
- `src/hotel_agent/web.py` — FastAPI 应用与 `/api/chat`、`/api/rooms`
- `src/hotel_agent/static/index.html` — Web 前端
- `src/hotel_agent/cli.py` — 命令行入口（含 `web`）
