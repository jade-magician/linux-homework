"""
MCP 服务 — 华强卖瓜
暴露游戏数据查询和管理接口
"""

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("huaqiang-game-mcp")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="game_status",
            description="查询指定游戏状态：天数、数值、胜负",
            inputSchema={
                "type": "object",
                "properties": {"game_id": {"type": "string"}},
                "required": ["game_id"],
            },
        ),
        Tool(
            name="leaderboard",
            description="查看存活天数排行榜",
            inputSchema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "default": 20}},
                "required": [],
            },
        ),
        Tool(
            name="list_events",
            description="列出所有预设事件",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="game_history",
            description="查看游戏历史记录",
            inputSchema={
                "type": "object",
                "properties": {
                    "game_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": ["game_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    from database import async_session
    from sqlalchemy import select
    from models import GameState, PresetEvent, GameEvent, Player

    async with async_session() as db:
        if name == "game_status":
            result = await db.execute(
                select(GameState).where(GameState.id == arguments["game_id"])
            )
            g = result.scalar_one_or_none()
            if not g:
                return [TextContent(type="text", text=json.dumps({"error": "not found"}, ensure_ascii=False))]
            return [TextContent(type="text", text=json.dumps({
                "id": str(g.id), "day": g.day, "watermelons": g.watermelons,
                "money": g.money, "anger": g.huaqiang_anger,
                "police": g.police_attention, "mind": g.mentality,
                "status": g.status, "lose_reason": g.lose_reason,
            }, ensure_ascii=False))]

        elif name == "leaderboard":
            from game_engine import get_leaderboard
            data = await get_leaderboard(db, arguments.get("limit", 20))
            return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False))]

        elif name == "list_events":
            result = await db.execute(select(PresetEvent).order_by(PresetEvent.id))
            data = [{"id": e.id, "title": e.title, "scene": e.scene, "image": e.image,
                      "min_day": e.min_day, "weight": e.weight} for e in result.scalars().all()]
            return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False))]

        elif name == "game_history":
            result = await db.execute(
                select(GameEvent).where(GameEvent.game_id == arguments["game_id"])
                .order_by(GameEvent.day.asc()).limit(arguments.get("limit", 20))
            )
            data = [{"day": e.day, "title": e.event_title, "chosen": e.chosen_option_text,
                      "result": e.result_text} for e in result.scalars().all()]
            return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False))]

    return [TextContent(type="text", text=json.dumps({"error": "unknown tool"}))]


async def run_mcp():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_mcp())
