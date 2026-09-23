from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Table, Column, String, Boolean, MetaData, select, insert

metadata = MetaData()

permissions_table = Table(
    "tool_permissions",
    metadata,
    Column("agent_id", String, primary_key=True),
    Column("tool_name", String, primary_key=True),
    Column("allowed", Boolean, default=False),
)

class PermissionManager:
    """
    Enforces tool access control outside the model.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_permission(self, agent_id: str, tool_name: str) -> bool:
        stmt = select(permissions_table.c.allowed).where(
            permissions_table.c.agent_id == agent_id,
            permissions_table.c.tool_name == tool_name
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return row if row is not None else False

    async def grant_permission(self, agent_id: str, tool_name: str):
        stmt = insert(permissions_table).values(
            agent_id=agent_id,
            tool_name=tool_name,
            allowed=True
        )
        await self.session.execute(stmt)
        await self.session.commit()
