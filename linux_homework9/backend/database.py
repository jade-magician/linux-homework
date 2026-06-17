from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed events if empty
    from sqlalchemy import select
    from models import PresetEvent

    async with async_session() as session:
        result = await session.execute(select(PresetEvent).limit(1))
        if result.scalar_one_or_none() is None:
            await _seed_events(session)
            await session.commit()


async def _seed_events(session):
    from models import PresetEvent
    from events_data import PRESET_EVENTS

    for e in PRESET_EVENTS:
        # In v3, events have variants — use first variant for the PresetEvent table
        v = e["variants"][0]
        # Flatten all 3 variant options into one merged option set for the DB record
        merged_options = []
        seen = set()
        for variant in e["variants"]:
            for opt in variant["options"]:
                if opt["text"] not in seen:
                    seen.add(opt["text"])
                    merged_options.append(opt)
        session.add(PresetEvent(
            id=e["id"],
            title=e["title"],
            scene=v["scene"],
            dialogue=v["dialogue"],
            image=e["image"],
            options=merged_options,
            min_day=e["min_day"],
            weight=e["weight"],
        ))
