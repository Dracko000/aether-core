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
    # Import EVERY model module so all tables register on the shared Base
    # metadata. Otherwise create_all silently skips tables whose modules were
    # not imported yet on this path (e.g. models_collective -> shared_knowledge,
    # models_beliefs -> beliefs, models_evolution -> agent_migrations), which
    # surfaces as "no such table" at query time depending on import order.
    from aether.storage import models
    from aether.storage import (  # noqa: F401  (side-effect: register tables)
        models_beliefs,
        models_collective,
        models_drives,
        models_events,
        models_evolution,
        models_experience,
        models_goals,
        models_lifecycle,
        models_messages,
        models_relationships,
    )
    from aether.tools.permissions import metadata as tool_metadata

    async with engine.begin() as conn:
        # All domain tables live on the shared Base metadata.
        await conn.run_sync(models.Base.metadata.create_all)
        # Tool permission tables use their own metadata.
        await conn.run_sync(tool_metadata.create_all)
