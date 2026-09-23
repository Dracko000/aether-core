from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from aether.config import settings

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def init_db():
    # Ensure all models are imported so they are registered with their respective metadata
    from aether.storage import models
    from aether.storage.models_lifecycle import Base as LifecycleBase
    from aether.storage.models_events import Base as EventBase
    from aether.storage.models_goals import Base as GoalBase
    from aether.storage.models_relationships import Base as RelBase
    from aether.storage.models_messages import Base as MsgBase
    from aether.storage.models_experience import Base as ExpBase
    from aether.storage.models_drives import Base as DriveBase
    from aether.tools.permissions import metadata as tool_metadata

    async with engine.begin() as conn:
        # Initialize core models
        await conn.run_sync(models.Base.metadata.create_all)
        # Initialize specialized models
        await conn.run_sync(LifecycleBase.metadata.create_all)
        await conn.run_sync(EventBase.metadata.create_all)
        await conn.run_sync(GoalBase.metadata.create_all)
        await conn.run_sync(RelBase.metadata.create_all)
        await conn.run_sync(MsgBase.metadata.create_all)
        await conn.run_sync(ExpBase.metadata.create_all)
        await conn.run_sync(DriveBase.metadata.create_all)
        # Initialize tool permissions
        await conn.run_sync(tool_metadata.create_all)
