-- 华强卖瓜 v3 — PostgreSQL 表结构
-- 种子数据由 Python database.py 在启动时自动插入
-- 此文件仅作参考，实际表结构由 SQLAlchemy ORM 自动管理

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS players (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    unlocked_achievements JSONB DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS game_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    day INTEGER NOT NULL DEFAULT 1,
    watermelons INTEGER NOT NULL DEFAULT 15,
    money INTEGER NOT NULL DEFAULT 200,
    huaqiang_anger INTEGER NOT NULL DEFAULT 30,
    police_attention INTEGER NOT NULL DEFAULT 5,
    mentality INTEGER NOT NULL DEFAULT 60,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    lose_reason VARCHAR(512),
    current_event_id INTEGER,
    current_event_variant INTEGER,
    current_event_options JSONB,
    seen_event_ids JSONB DEFAULT '[]'::jsonb,
    seen_variants JSONB DEFAULT '{}'::jsonb,
    zero_wml_day INTEGER,
    save_slot INTEGER,
    saved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS preset_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(128) NOT NULL,
    scene TEXT NOT NULL,
    dialogue TEXT NOT NULL,
    image VARCHAR(64) NOT NULL DEFAULT 'bg_game.png',
    options JSONB NOT NULL,
    min_day INTEGER NOT NULL DEFAULT 1,
    weight INTEGER NOT NULL DEFAULT 10
);

CREATE TABLE IF NOT EXISTS game_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES game_states(id) ON DELETE CASCADE,
    day INTEGER NOT NULL,
    event_title VARCHAR(128) NOT NULL,
    event_scene TEXT NOT NULL,
    event_dialogue TEXT NOT NULL,
    event_image VARCHAR(64) NOT NULL,
    day_hint TEXT,
    chosen_option_idx INTEGER NOT NULL,
    chosen_option_text VARCHAR(256) NOT NULL,
    result_text TEXT NOT NULL,
    stat_changes JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_game_states_player ON game_states(player_id);
CREATE INDEX IF NOT EXISTS idx_game_states_save_slot ON game_states(save_slot);
CREATE INDEX IF NOT EXISTS idx_game_events_game ON game_events(game_id);
CREATE INDEX IF NOT EXISTS idx_lb ON game_states(day DESC, mentality DESC);
