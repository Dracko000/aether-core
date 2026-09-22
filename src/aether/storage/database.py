from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from aether.config import settings

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        from aether.storage.models import Base
        await conn.run_sync(Base.metadata.create_all)
