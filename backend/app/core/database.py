from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create all tables and seed demo data."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        import app.models  # noqa: registers all models with Base.metadata
        await conn.run_sync(Base.metadata.create_all)

        # Idempotent column additions for Phase 6 AI classification fields.
        # create_all won't ALTER an existing table, so we do it explicitly.
        _ai_cols = [
            "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS ai_incident_type VARCHAR",
            "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS ai_severity      FLOAT",
            "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS ai_confidence    FLOAT",
            "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS ai_keywords      VARCHAR",
            "ALTER TABLE incidents ADD COLUMN IF NOT EXISTS ai_reasoning     VARCHAR",
        ]
        for sql in _ai_cols:
            try:
                await conn.execute(text(sql))
            except Exception:
                pass  # column already present — safe to ignore

    # Seed demo data (no-ops if already seeded)
    async with AsyncSessionLocal() as session:
        from app.services.seed_data import seed
        await seed(session)
