"""
华强卖瓜 — 核心引擎 v3
- 22主题 x 5变体 = 110个独立文案
- 存档/读档/退出
- 排行榜
"""

import random
from dataclasses import dataclass
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from models import GameState, PresetEvent, GameEvent, Player


@dataclass
class Option:
    index: int
    text: str
    effects: dict


@dataclass
class EventData:
    event_id: int
    variant_idx: int
    title: str
    scene: str
    dialogue: str
    day_hint: str
    image: str
    options: list[Option]
    speaker: str = "刘华强"


async def create_new_game(player_name: str, db: AsyncSession) -> GameState:
    player = Player(name=player_name or "无名瓜摊")
    db.add(player)
    await db.flush()
    game = GameState(player_id=player.id)
    db.add(game)
    await db.flush()
    return game


async def get_game(game_id: str, db: AsyncSession) -> GameState | None:
    result = await db.execute(select(GameState).where(GameState.id == game_id))
    return result.scalar_one_or_none()


async def pick_random_event(game: GameState, db: AsyncSession) -> EventData:
    """从事件池按权重选一个主题，优先选未出现过的，随机选变体"""
    from events_data import PRESET_EVENTS

    # Filter by min_day
    available = [e for e in PRESET_EVENTS if e["min_day"] <= game.day]
    if not available:
        return _fallback_event()

    # Anti-repeat: prefer unseen topics (use DB-persisted list)
    seen_ids = set(game.seen_event_ids or [])
    unseen = [e for e in available if e["id"] not in seen_ids]

    # If we have unseen topics, use them. If all seen, recycle the least recently seen ones.
    if unseen:
        pool = unseen
    else:
        # All seen: keep only the most recent few in seen to allow recycling
        seen_ids = set(list(seen_ids)[-5:])
        game.seen_event_ids = list(seen_ids)
        unseen = [e for e in available if e["id"] not in seen_ids]
        pool = unseen if unseen else available

    # Weighted selection
    weights = [e["weight"] for e in pool]
    topic = random.choices(pool, weights=weights, k=1)[0]

    # Track seen (keep last 18 to ensure variety)
    seen_ids = set(game.seen_event_ids or [])
    seen_ids.add(topic["id"])
    if len(seen_ids) > 18:
        seen_ids = set(list(seen_ids)[-14:])
    game.seen_event_ids = list(seen_ids)

    # Pick variant: prefer unseen variants for this topic
    var_key = str(topic["id"])
    seen_vars = game.seen_variants or {}
    used_idxs = set(seen_vars.get(var_key, []))
    variants = topic["variants"]
    unused_idxs = [i for i in range(len(variants)) if i not in used_idxs]
    if unused_idxs:
        variant_idx = random.choice(unused_idxs)
    else:
        variant_idx = random.randrange(len(variants))
        used_idxs.clear()  # Reset when all variants seen

    used_idxs.add(variant_idx)
    seen_vars[var_key] = list(used_idxs)
    game.seen_variants = seen_vars

    variant = variants[variant_idx]

    options = [Option(i, o["text"], o["effects"]) for i, o in enumerate(variant["options"])]

    # Cache on game state
    game.current_event_id = topic["id"]
    game.current_event_variant = variant_idx
    game.current_event_options = [
        {"index": o.index, "text": o.text, "effects": o.effects} for o in options
    ]

    return EventData(
        event_id=topic["id"],
        variant_idx=variants.index(variant),
        title=topic["title"],
        scene=variant["scene"],
        dialogue=variant["dialogue"],
        day_hint=variant.get("day_hint", "").replace("{day}", str(game.day)),
        image=topic["image"],
        speaker=topic.get("speaker", variant.get("speaker", "刘华强")),
        options=options,
    )


def _fallback_event():
    return EventData(
        event_id=0, variant_idx=0, title="平静的一天",
        scene="今天华强没来。阳光洒在瓜摊上，温暖而安静。",
        dialogue='"今天的瓜……保熟。"你对着空无一人的街道自言自语。',
        day_hint="难得的平静。但明天他一定会来——你知道的。",
        image="event_normal.png",
        options=[
            Option(0, "好好整理瓜摊，为明天做准备", {"money": 10, "mind": 5}),
            Option(1, "泡杯茶，坐在摊前享受久违的清静", {"mind": 10}),
            Option(2, "主动去派出所问问最近的治安情况", {"police": 5, "mind": -3}),
        ],
    )


async def apply_action(game: GameState, event: EventData, option_idx: int, db: AsyncSession, already_unlocked: set = None) -> GameEvent:
    chosen = event.options[option_idx]
    effects = dict(chosen.effects)  # copy

    # 提取成就触发器(不计入属性修改)
    achv_trigger = effects.pop("achv", None)

    # 统一 wml/watermelons 键名
    wml_effect = effects.pop("wml", 0)
    if "watermelons" not in effects:
        effects["watermelons"] = wml_effect
    else:
        effects["watermelons"] = effects["watermelons"] + wml_effect

    # 西瓜为0时,所有选项收益变为负面 (没瓜卖,什么都做不了)
    if game.watermelons <= 0:
        effects = {k: (-abs(v) if v != 0 else 0) for k, v in effects.items()}
        if "money" not in effects or effects["money"] == 0:
            effects["money"] = -5
        if "mind" not in effects or effects["mind"] == 0:
            effects["mind"] = -3

    # 选项效果上限控制
    anger_effect = effects.get("anger", 0)
    if anger_effect < -10: anger_effect = -10
    if anger_effect > 20: anger_effect = 20
    mind_effect = effects.get("mind", 0)
    if mind_effect > 20: mind_effect = 20
    if mind_effect < -20: mind_effect = -20
    police_effect = effects.get("police", 0)
    if police_effect > 20: police_effect = 20
    if police_effect < -10: police_effect = -10
    money_effect = effects.get("money", 0)
    if money_effect > 50: money_effect = 50
    if money_effect < -100: money_effect = -100

    # 应用属性(使用上限控制后的值)
    game.watermelons = _clamp(game.watermelons + effects.get("watermelons", effects.get("wml", 0)), 0, 999)
    game.money = _clamp(game.money + money_effect, -999, 9999)
    game.huaqiang_anger = _clamp(game.huaqiang_anger + anger_effect, 0, 100)
    game.police_attention = _clamp(game.police_attention + police_effect, 0, 100)
    game.mentality = _clamp(game.mentality + mind_effect, 0, 100)

    # 软修正: 推动游戏向结局发展 (怒气/警方有自然上升趋势, 心态过高会自然回落)
    if game.huaqiang_anger < 35:
        game.huaqiang_anger = _clamp(game.huaqiang_anger + 3, 0, 100)
    if game.police_attention < 25:
        game.police_attention = _clamp(game.police_attention + 3, 0, 100)
    if game.mentality > 75:
        game.mentality = _clamp(game.mentality - 3, 0, 100)

    result_text = _result_text(event.title, chosen.text, effects)

    ge = GameEvent(
        game_id=game.id, day=game.day,
        event_title=event.title, event_scene=event.scene,
        event_dialogue=event.dialogue, event_image=event.image,
        day_hint=event.day_hint,
        chosen_option_idx=option_idx, chosen_option_text=chosen.text,
        result_text=result_text, stat_changes=effects,
    )
    db.add(ge)

    game.current_event_id = None
    game.current_event_variant = None
    game.current_event_options = None
    # 每天固定消耗1个西瓜 (摆摊切瓜给客人试吃)
    game.watermelons = _clamp(game.watermelons - 1, 0, 999)
    game.day += 1
    # 每天有概率随机获得或失去西瓜 (重点: 西瓜耗尽后靠此恢复)
    daily_msg = ""
    if random.random() < 0.35:
        r = random.random()
        if r < 0.25:
            gain = random.randint(2, 8)
            game.watermelons = _clamp(game.watermelons + gain, 0, 999)
            daily_msg = f"今早供货商多送了{gain}个西瓜,库存增加。"
        elif r < 0.50:
            loss = random.randint(1, 5)
            game.watermelons = _clamp(game.watermelons - loss, 0, 999)
            daily_msg = f"昨晚有{loss}个瓜被野猫啃坏了,心疼。"
        elif r < 0.70:
            sold = random.randint(2, 6)
            game.watermelons = _clamp(game.watermelons - sold, 0, 999)
            game.money = _clamp(game.money + sold * 3, -999, 9999)
            daily_msg = f"早上来了个饭店采购,一口气买了{sold}个瓜,进账{sold*3}块。"
        else:
            gain = random.randint(3, 10)
            game.watermelons = _clamp(game.watermelons + gain, 0, 999)
            daily_msg = f"隔壁老王的瓜烂了,他把库存的{gain}个好瓜转让给了你。"
    game.daily_msg = daily_msg if daily_msg else None
    # 追踪西瓜归零日期(持久化, 用于绝处逢生成就)
    if game.watermelons <= 0:
        if not game.zero_wml_day:
            game.zero_wml_day = game.day
    else:
        game.zero_wml_day = None
    _check_game_over(game)

    # 检测成就 (传入已解锁列表防止重复触发)
    from achievements import check_achievements
    new_achv_keys, new_achvs = check_achievements(game, achv_trigger, already_unlocked)
    # KEYS 用于持久化到 Player 表, dicts 用于 API 响应
    game._new_achv_keys = new_achv_keys
    game._new_achievements = new_achvs

    await db.flush()
    return ge


def _check_game_over(game: GameState):
    if game.huaqiang_anger >= 100:
        game.status = "lost"
        game.lose_reason = "华强怒不可遏。你听到的最后一句话是：「这瓜不保熟啊，老板。」"
    elif game.police_attention >= 90:
        game.status = "won"
        game.lose_reason = "警笛长鸣，正义降临。华强终于落网。你的瓜摊成为了这条街的传奇——那个让刘华强伏法的瓜摊。"
    elif game.money <= -300:
        game.status = "lost"
        game.lose_reason = "你破产了。连遮阳伞都被债主搬走。你离开了这条街，没有人知道你的名字。"
    elif game.mentality <= 0:
        game.status = "lost"
        game.lose_reason = "你的精神彻底崩溃。现在你每天在街上游荡，嘴里反复念着：「保熟吗……保熟吗……」你变成了你最害怕的那个人。"
    elif game.watermelons <= 0 and game.money <= 50:
        game.status = "lost"
        game.lose_reason = "瓜也没了，钱也不够进货。这不是生存，这是绝望。"


def _clamp(v, lo, hi): return max(lo, min(hi, v))


def _result_text(title, choice, effects):
    parts = [f"「{choice}」"]
    a = effects.get("anger", 0)
    if a > 5: parts.append("华强的怒火明显上升。")
    elif a > 0: parts.append("华强略有不满。")
    elif a < -3: parts.append("华强明显消气了。")
    elif a < 0: parts.append("华强态度缓和了一些。")
    p = effects.get("police", 0)
    if p > 5: parts.append("警方开始关注这里。")
    elif p > 0: parts.append("引起了周围人的注意。")
    m = effects.get("mind", 0)
    if m > 5: parts.append("你心情好了不少。")
    elif m < -5: parts.append("你感到一阵心力交瘁。")
    mo = effects.get("money", 0)
    if mo > 15: parts.append("今天收获颇丰。")
    elif mo < -15: parts.append("钱包大出血。")
    return "".join(parts)


def game_state_response(game: GameState) -> dict:
    return {
        "id": str(game.id), "day": game.day,
        "watermelons": game.watermelons, "money": game.money,
        "huaqiang_anger": game.huaqiang_anger,
        "police_attention": game.police_attention,
        "mentality": game.mentality,
        "status": game.status, "lose_reason": game.lose_reason,
        "save_slot": game.save_slot,
        "daily_msg": getattr(game, "daily_msg", None),
    }


# ─── Save / Load ─────────────────────────────────────────────────────────────

async def save_game(game_id: str, slot: int, db: AsyncSession) -> GameState:
    """保存游戏到指定槽位 (1-5)"""
    game = await get_game(game_id, db)
    if not game:
        raise ValueError("游戏不存在")

    # Clear old save in this slot by the same player
    existing = await db.execute(
        select(GameState).where(
            and_(GameState.player_id == game.player_id, GameState.save_slot == slot, GameState.status == "active")
        )
    )
    for old in existing.scalars().all():
        old.save_slot = None
        old.saved_at = None

    game.save_slot = slot
    game.saved_at = datetime.utcnow()
    await db.flush()
    return game


async def list_saves(player_name: str, db: AsyncSession) -> list[dict]:
    """列出某玩家的所有存档"""
    result = await db.execute(
        select(GameState, Player.name)
        .join(Player, GameState.player_id == Player.id)
        .where(and_(Player.name == player_name, GameState.save_slot.isnot(None), GameState.status == "active"))
        .order_by(GameState.save_slot)
    )
    saves = []
    for game, name in result.scalars().all():
        if game.save_slot is not None:
            saves.append({
                "slot": game.save_slot,
                "game_id": str(game.id),
                "day": game.day,
                "player": name,
                "saved_at": game.saved_at.isoformat() if game.saved_at else None,
            })
    return saves


async def load_game(slot: int, player_name: str, db: AsyncSession) -> GameState | None:
    """从槽位读取存档（仅限同一玩家）"""
    result = await db.execute(
        select(GameState)
        .join(Player, GameState.player_id == Player.id)
        .where(and_(Player.name == player_name, GameState.save_slot == slot, GameState.status == "active"))
    )
    return result.scalar_one_or_none()


async def quit_game(game_id: str, db: AsyncSession):
    """终止游戏（标记为主动退出）"""
    game = await get_game(game_id, db)
    if game and game.status == "active":
        game.status = "lost"
        game.lose_reason = "你主动收摊了。这条街的故事还很长，但你选择了离开。华强以后会去谁的瓜摊呢——只有他自己知道了。"


# ─── Leaderboard ─────────────────────────────────────────────────────────────

async def get_leaderboard(db: AsyncSession, limit: int = 20) -> list[dict]:
    result = await db.execute(
        select(GameState, Player.name)
        .join(Player, GameState.player_id == Player.id)
        .where(GameState.day > 1)
        .order_by(desc(GameState.day), desc(GameState.mentality + GameState.money))
        .limit(limit)
    )
    rows = result.all()
    return [
        {"rank": i + 1, "player": name, "days": game.day - 1,
         "status": game.status, "anger": game.huaqiang_anger, "police": game.police_attention}
        for i, (game, name) in enumerate(rows)
    ]
