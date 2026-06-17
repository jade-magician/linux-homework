import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Player(Base):
    __tablename__ = "players"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    unlocked_achievements = Column(JSON, nullable=True, default=list)
    games = relationship("GameState", back_populates="player", cascade="all, delete-orphan")


class GameState(Base):
    __tablename__ = "game_states"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    player_id = Column(String(36), ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    day = Column(Integer, nullable=False, default=1)
    watermelons = Column(Integer, nullable=False, default=15)
    money = Column(Integer, nullable=False, default=200)
    huaqiang_anger = Column(Integer, nullable=False, default=30)
    police_attention = Column(Integer, nullable=False, default=5)
    mentality = Column(Integer, nullable=False, default=60)
    status = Column(String(16), nullable=False, default="active")
    lose_reason = Column(String(512), nullable=True)
    current_event_id = Column(Integer, nullable=True)
    current_event_variant = Column(Integer, nullable=True)
    current_event_options = Column(JSON, nullable=True)
    seen_event_ids = Column(JSON, nullable=True, default=list)
    seen_variants = Column(JSON, nullable=True, default=dict)
    zero_wml_day = Column(Integer, nullable=True)  # 西瓜首次归零的日期(绝处逢生成就)
    # Save slot metadata
    save_slot = Column(Integer, nullable=True)
    saved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    player = relationship("Player", back_populates="games")
    events = relationship("GameEvent", back_populates="game", cascade="all, delete-orphan")


class PresetEvent(Base):
    __tablename__ = "preset_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    scene = Column(Text, nullable=False)
    dialogue = Column(Text, nullable=False)
    image = Column(String(64), nullable=False, default="bg_game.png")
    options = Column(JSON, nullable=False)
    min_day = Column(Integer, nullable=False, default=1)
    weight = Column(Integer, nullable=False, default=10)


class GameEvent(Base):
    __tablename__ = "game_events"
    id = Column(String(36), primary_key=True, default=gen_uuid)
    game_id = Column(String(36), ForeignKey("game_states.id", ondelete="CASCADE"), nullable=False)
    day = Column(Integer, nullable=False)
    event_title = Column(String(128), nullable=False)
    event_scene = Column(Text, nullable=False)
    event_dialogue = Column(Text, nullable=False)
    event_image = Column(String(64), nullable=False)
    day_hint = Column(Text, nullable=True)
    chosen_option_idx = Column(Integer, nullable=False)
    chosen_option_text = Column(String(256), nullable=False)
    result_text = Column(Text, nullable=False)
    stat_changes = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    game = relationship("GameState", back_populates="events")
