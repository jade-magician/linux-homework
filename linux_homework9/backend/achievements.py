# -*- coding: utf-8 -*-
"""华强卖瓜 — 成就系统 (25个)"""

ACHIEVEMENTS = {
    # ─── 存活类 ───
    "day_1":    {"id": 1,  "name": "初来乍到",   "desc": "活过第1天",          "icon": "🌅", "group": "存活"},
    "day_7":    {"id": 2,  "name": "一周瓜农",   "desc": "存活7天",            "icon": "📅", "group": "存活"},
    "day_15":   {"id": 3,  "name": "半月坚持",   "desc": "存活15天",           "icon": "📆", "group": "存活"},
    "day_30":   {"id": 4,  "name": "一月传奇",   "desc": "存活30天",           "icon": "🏆", "group": "存活"},
    "quit":     {"id": 5,  "name": "急流勇退",   "desc": "主动收摊退出",        "icon": "🚪", "group": "存活"},

    # ─── 结局类 ───
    "win":      {"id": 6,  "name": "正义必胜",   "desc": "警方抓捕华强(胜利)",   "icon": "🚔", "group": "结局"},
    "anger":    {"id": 7,  "name": "怒火焚身",   "desc": "死于华强刀下",        "icon": "🔪", "group": "结局"},
    "mind":     {"id": 8,  "name": "心力交瘁",   "desc": "心态崩溃",            "icon": "💔", "group": "结局"},
    "bankrupt": {"id": 9,  "name": "破产清算",   "desc": "金钱破产",            "icon": "💸", "group": "结局"},
    "no_wml":   {"id": 10, "name": "弹尽粮绝",   "desc": "瓜光钱光",            "icon": "🫗", "group": "结局"},

    # ─── 西瓜类 ───
    "wml_50":   {"id": 11, "name": "瓜满为患",   "desc": "库存达到50个西瓜",     "icon": "🍉", "group": "西瓜"},
    "zero_live": {"id": 12, "name": "绝处逢生",  "desc": "西瓜归零后活过3天",    "icon": "🌱", "group": "西瓜"},

    # ─── 剧情节点 ───
    "plaque":      {"id": 13, "name": "童叟无欺",   "desc": "华强为你题写匾额",          "icon": "🖌️", "group": "剧情"},
    "reconcile":   {"id": 14, "name": "和解协议",   "desc": "与华强签署和解书",           "icon": "🤝", "group": "剧情"},
    "muse":        {"id": 15, "name": "缪斯",      "desc": "参加华强艺术回顾展",          "icon": "🎨", "group": "剧情"},
    "opera":       {"id": 16, "name": "瓜摊恩仇录", "desc": "华强原创黄梅戏:瓜摊恩仇录",   "icon": "🎭", "group": "剧情"},
    "academic":    {"id": 17, "name": "学术尽头",   "desc": "学术的尽头,是瓜摊",           "icon": "📚", "group": "剧情"},
    "no_more":     {"id": 18, "name": "不再找茬",   "desc": "华强收起秒表,不再计时",       "icon": "⏱️", "group": "剧情"},
    "shinkai":     {"id": 19, "name": "新海诚式告别","desc": "不说再见,只说路上吃",        "icon": "🌈", "group": "剧情"},
    "qiongyao":    {"id": 20, "name": "琼瑶对唱",   "desc": "完成琼瑶式山歌对唱",          "icon": "🎤", "group": "剧情"},
    "real_one":    {"id": 21, "name": "真实的瓜",   "desc": "无实物表演之后,一人一半真瓜",  "icon": "🍈", "group": "剧情"},
    "disband":     {"id": 22, "name": "卧底解散",   "desc": "黑衣组织因天热解散",           "icon": "🕶️", "group": "剧情"},

    # ─── 收集类 ───
    "seen_all":   {"id": 23, "name": "见多识广",   "desc": "触发过全部22种事件",            "icon": "👁️", "group": "收集"},
    "all_variant": {"id": 24, "name": "千面华强",  "desc": "某一事件5个变体全部见过",        "icon": "🎭", "group": "收集"},
    "seen_10":    {"id": 25, "name": "十全十美",   "desc": "触发过10种不同事件",             "icon": "✨", "group": "收集"},
}


def check_achievements(game, triggered_achv=None, already_unlocked=None):
    """
    检查并返回新解锁的成就列表。
    already_unlocked: set of achievement keys already unlocked (prevents repeats)
    返回: (list_of_keys, list_of_achievement_dicts)
    """
    already = set(already_unlocked or [])
    new_keys = []

    def unlock(key):
        """只有尚未解锁的成就才加入"""
        if key not in already:
            new_keys.append(key)
            already.add(key)

    d = game.day
    w = game.watermelons
    m = game.money
    a = game.huaqiang_anger
    p = game.police_attention
    mt = game.mentality
    seen = set(game.seen_event_ids or [])

    # 存活类
    if d >= 2: unlock("day_1")
    if d >= 8: unlock("day_7")
    if d >= 16: unlock("day_15")
    if d >= 31: unlock("day_30")

    # 西瓜类
    if w >= 50: unlock("wml_50")
    if game.zero_wml_day and d - game.zero_wml_day >= 3:
        unlock("zero_live")

    # 收集类
    if len(seen) >= 10: unlock("seen_10")
    if len(seen) >= 22: unlock("seen_all")

    # 变体收集
    if game.seen_variants:
        for topic_id, variants in game.seen_variants.items():
            if len(variants) >= 5:
                unlock("all_variant")
                break

    # 剧情触发 (由选项中的 achv 键触发)
    if triggered_achv:
        unlock(triggered_achv)

    # 结局类 (游戏结束时触发)
    if game.status == "won":
        unlock("win")
    elif game.status == "lost":
        reason = game.lose_reason or ""
        if "华强怒" in reason or "不保熟" in reason:
            unlock("anger")
        elif "破产" in reason or "债主" in reason:
            unlock("bankrupt")
        elif "崩溃" in reason or "游荡" in reason:
            unlock("mind")
        elif "瓜也没了" in reason or "绝望" in reason:
            unlock("no_wml")
        elif "主动收摊" in reason:
            unlock("quit")

    return new_keys, [ACHIEVEMENTS[k] for k in new_keys]
