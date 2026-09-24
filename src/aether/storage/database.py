from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from aether.config import settings

# SQLite raises "database is locked" immediately by default when another
# connection holds a write lock. In async/pooled contexts (tests included)
# transient lock contention is normal, so we wait for the lock instead.
#
# NullPool: connections are created and closed within a single session scope,
# so a connection opened inside one event loop (e.g. a TestClient portal loop)
# can never leak into the pooled state of another loop.
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={"timeout": 30},
    poolclass=NullPool,
)

if settings.DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_connection, connection_record):
        """Enable WAL + busy timeout on every SQLite connection.

        WAL decouples readers from writers: a long-lived reader (e.g. a
        session left open across a test boundary) can no longer block a
        writer's COMMIT, which is the classic cause of "database is locked"
        on the commit in multi-connection async apps.
        """
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()
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
