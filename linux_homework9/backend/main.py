"""
华强卖瓜 v3 — FastAPI
"""

import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config import settings
from database import get_db, init_db
from game_engine import (
    create_new_game, get_game, pick_random_event,
    apply_action, game_state_response, get_leaderboard,
    save_game, list_saves, load_game, quit_game,
)
from models import GameEvent, PresetEvent, GameState, Player
from game_engine import Option, EventData

app = FastAPI(title=settings.app_title)


# ─── Models ──────────────────────────────────────────────────────────────────

class NewGameReq(BaseModel): name: str = ""
class ActionReq(BaseModel): option_idx: int
class SaveReq(BaseModel): player_name: str; slot: int
class LoadReq(BaseModel): player_name: str; slot: int
class QuitReq(BaseModel): player_name: str


# ─── Game API ────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "3.0"}


@app.post("/api/game/new")
async def new_game(req: NewGameReq, db: AsyncSession = Depends(get_db)):
    game = await create_new_game(req.name, db)
    return game_state_response(game)


async def _get_player_achv(game: GameState, db: AsyncSession) -> list:
    """安全获取玩家跨游戏成就"""
    try:
        result = await db.execute(
            select(Player).where(Player.id == game.player_id)
        )
        player = result.scalars().first()
        return player.unlocked_achievements if player else []
    except Exception:
        return []


@app.get("/api/game/{game_id}")
async def get_state(game_id: str, db: AsyncSession = Depends(get_db)):
    game = await get_game(game_id, db)
    if not game: raise HTTPException(404, "游戏不存在")
    resp = game_state_response(game)
    resp["unlocked_achievements"] = await _get_player_achv(game, db)
    return resp


@app.get("/api/game/{game_id}/event")
async def get_event(game_id: str, db: AsyncSession = Depends(get_db)):
    game = await get_game(game_id, db)
    if not game: raise HTTPException(404, "游戏不存在")
    if game.status != "active": raise HTTPException(400, f"游戏已结束: {game.status}")
    event = await pick_random_event(game, db)
    return {
        "title": event.title, "scene": event.scene,
        "dialogue": event.dialogue, "day_hint": event.day_hint,
        "image": event.image, "speaker": event.speaker,
        "options": [{"index": o.index, "text": o.text} for o in event.options],
    }


@app.post("/api/game/{game_id}/action")
async def do_action(game_id: str, req: ActionReq, db: AsyncSession = Depends(get_db)):
    game = await get_game(game_id, db)
    if not game: raise HTTPException(404, "游戏不存在")
    if game.status != "active": raise HTTPException(400, "游戏已结束")
    if not game.current_event_options: raise HTTPException(400, "请先获取事件")

    preset_result = await db.execute(
        select(PresetEvent).where(PresetEvent.id == game.current_event_id)
    )
    preset = preset_result.scalar_one_or_none()
    options = [Option(o["index"], o["text"], o["effects"]) for o in game.current_event_options]
    event = EventData(
        event_id=game.current_event_id or 0,
        variant_idx=game.current_event_variant or 0,
        title=preset.title if preset else "",
        scene="", dialogue="", day_hint="", image="",
        options=options,
    )
    if req.option_idx < 0 or req.option_idx >= len(options):
        raise HTTPException(400, "无效选项")

    # 查询已解锁成就用于去重
    player_result = await db.execute(select(Player).where(Player.id == game.player_id))
    player = player_result.scalars().first()
    already = set(player.unlocked_achievements or []) if player else set()

    ge = await apply_action(game, event, req.option_idx, db, already)
    # 持久化新成就到 Player (存储的是 KEY, 如 "day_1")
    new_achv_keys = getattr(game, '_new_achv_keys', [])
    if new_achv_keys and player:
        existing = set(player.unlocked_achievements or [])
        for k in new_achv_keys:
            existing.add(k)
        player.unlocked_achievements = list(existing)
    resp = game_state_response(game)
    resp["unlocked_achievements"] = await _get_player_achv(game, db)
    return {
        "game": resp,
        "result_text": ge.result_text,
        "stat_changes": ge.stat_changes,
        "is_game_over": game.status != "active",
        "daily_msg": getattr(game, "daily_msg", None),
        "new_achievements": getattr(game, "_new_achievements", []),
    }


@app.get("/api/game/{game_id}/history")
async def get_history(game_id: str, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GameEvent).where(GameEvent.game_id == game_id)
        .order_by(GameEvent.day.asc()).limit(limit)
    )
    return [{
        "day": e.day, "event_title": e.event_title,
        "event_scene": e.event_scene, "event_dialogue": e.event_dialogue,
        "chosen_option_text": e.chosen_option_text,
        "result_text": e.result_text, "stat_changes": e.stat_changes,
    } for e in result.scalars().all()]


# ─── Save / Load / Quit ──────────────────────────────────────────────────────

@app.post("/api/save")
async def api_save(req: SaveReq, db: AsyncSession = Depends(get_db)):
    """保存当前活跃游戏到指定槽位"""
    result = await db.execute(
        select(GameState).join(GameState.player).where(
            GameState.player.has(name=req.player_name),
            GameState.status == "active",
            GameState.save_slot.is_(None)
        ).order_by(GameState.updated_at.desc()).limit(1)
    )
    game = result.scalar_one_or_none()
    if not game: raise HTTPException(404, "没有找到未存档的活跃游戏")
    await save_game(str(game.id), req.slot, db)
    return {"saved": True, "slot": req.slot, "game_id": str(game.id), "day": game.day}


@app.post("/api/load")
async def api_load(req: LoadReq, db: AsyncSession = Depends(get_db)):
    """从指定槽位读档"""
    game = await load_game(req.slot, req.player_name, db)
    if not game: raise HTTPException(404, f"槽位 {req.slot} 没有存档")
    # Clear save slot flag (game is now in-play)
    game.save_slot = None
    game.saved_at = None
    await db.flush()
    return game_state_response(game)


@app.get("/api/saves/{player_name}")
async def api_list_saves(player_name: str, db: AsyncSession = Depends(get_db)):
    return await list_saves(player_name, db)


@app.post("/api/quit")
async def api_quit(req: QuitReq, db: AsyncSession = Depends(get_db)):
    """终止当前活跃游戏"""
    result = await db.execute(
        select(GameState).join(GameState.player).where(
            GameState.player.has(name=req.player_name),
            GameState.status == "active"
        ).order_by(GameState.updated_at.desc()).limit(1)
    )
    game = result.scalar_one_or_none()
    if not game: raise HTTPException(404, "没有活跃游戏")
    await quit_game(str(game.id), db)
    # 检测退出成就
    from achievements import check_achievements
    new_keys, new_achvs = check_achievements(game)
    if new_keys:
        p_result = await db.execute(select(Player).where(Player.id == game.player_id))
        player = p_result.scalars().first()
        if player:
            existing = set(player.unlocked_achievements or [])
            for k in new_keys:
                existing.add(k)
            player.unlocked_achievements = list(existing)
    return {"quit": True, "game_id": str(game.id)}


# ─── Leaderboard ─────────────────────────────────────────────────────────────

@app.get("/api/leaderboard")
async def leaderboard(limit: int = 20, db: AsyncSession = Depends(get_db)):
    return await get_leaderboard(db, limit)


@app.get("/api/achievements/{player_name}")
async def get_achievements(player_name: str, db: AsyncSession = Depends(get_db)):
    """获取某玩家的成就 (跨游戏持久化)"""
    from models import Player
    result = await db.execute(select(Player).where(Player.name == player_name))
    player = result.scalar_one_or_none()
    if not player:
        return {"unlocked_achievements": []}
    return {"unlocked_achievements": player.unlocked_achievements or []}


# ─── Static ──────────────────────────────────────────────────────────────────

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "static")


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup():
    await init_db()
    print(f"[Huaqiang v3] Started. DB: {settings.database_url[:50]}...")
