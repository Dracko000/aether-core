import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from aether.storage.models_messages import AgentMessageModel

class MessageRepository:
    """
    Manages the persistence of agent-to-agent communication.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def send_message(self, sender_id: str, receiver_id: str, content: str):
        msg_id = f"msg_{int(time.time()*1000)}_{sender_id[:4]}"
        stmt = insert(AgentMessageModel).values(
            message_id=msg_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content
        )
        await self.session.execute(stmt)
        await self.session.commit()
        return msg_id

    async def get_unread_messages(self, agent_id: str):
        stmt = select(AgentMessageModel).where(
            AgentMessageModel.receiver_id == agent_id,
            AgentMessageModel.is_read == False
        ).order_by(AgentMessageModel.timestamp.asc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def mark_as_read(self, message_id: str):
        stmt = update(AgentMessageModel).where(
            AgentMessageModel.message_id == message_id
        ).values(is_read=True)
        await self.session.execute(stmt)
        await self.session.commit()
