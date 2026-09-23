from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from aether.config import settings

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def init_db():
    # Use engine.begin() to ensure the transaction is committed
    async with engine.begin() as conn:
        from aether.storage.models import Base
        from aether.storage.models_lifecycle import Base as LifecycleBase
        from aether.storage.models_events import Base as EventBase
        from aether.storage.models_goals import Base as GoalBase
        from aether.storage.models_relationships import Base as RelBase
        from aether.storage.models_messages import Base as MsgBase
        from aether.storage.models_experience import Base as ExpBase
        from aether.tools.permissions import metadata as tool_metadata

        # Initialize core models (Agent, Identity, EpisodicMemory, etc.)
        await conn.run_sync(Base.metadata.create_all)
        # Initialize lifecycle models
        await conn.run_sync(LifecycleBase.metadata.create_all)
        # Initialize event models
        await conn.run_sync(EventBase.metadata.create_all)
        # Initialize goal models
        await conn.run_sync(GoalBase.metadata.create_all)
        # Initialize relationship models
        await conn.run_sync(RelBase.metadata.create_all)
        # Initialize message models
        await conn.run_sync(MsgBase.metadata.create_all)
        # Initialize experience graph models
        await conn.run_sync(ExpBase.metadata.create_all)
        # Initialize tool permissions table
        await conn.run_sync(tool_metadata.create_all)
