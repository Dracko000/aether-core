import logging
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid

from aether.agent.runtime import AgentRuntime
from aether.orchestration.manager import OrchestrationManager
from aether.storage.database import AsyncSessionLocal
from aether.storage.repositories import AgentRepository, IdentityRepository
from aether.storage.repositories_goals import GoalRepository
from aether.agent.lifecycle import AgentState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aether.api")

app = FastAPI(title="Aether Core API v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
runtime = AgentRuntime()
orch_manager = OrchestrationManager(runtime)

@app.on_event("startup")
async def startup_event():
    await orch_manager.start()
    logger.info("Aether Core API started")

@app.on_event("shutdown")
async def shutdown_event():
    await orch_manager.stop()

# Schemas
class MessageRequest(BaseModel):
    sender_id: str
    content: str

class GoalRequest(BaseModel):
    description: str
    priority: int = 10

class StateResponse(BaseModel):
    agent_id: str
    state: str
    model_id: Optional[str] = None

# Endpoints
@app.post("/agent/{agent_id}/wake")
async def wake_agent(agent_id: str):
    try:
        # We need a session to persist the transition
        async with AsyncSessionLocal() as session:
            await runtime.wake(agent_id)
            # The runtime.wake method handles the DB update and transition.
            # If it's the first time waking, it moves from CREATED/IDLE -> AWAKENED.

        return {"status": "awakened", "agent_id": agent_id}
    except Exception as e:
        logger.exception(f"Wake failed for {agent_id}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/agent/{agent_id}/sleep")
async def sleep_agent(agent_id: str):
    try:
        await runtime.sleep(agent_id)
        return {"status": "sleeping", "agent_id": agent_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/agent/{agent_id}/state")
async def get_agent_state(agent_id: str):
    async with AsyncSessionLocal() as session:
        agent_repo = AgentRepository(session)
        agent = await agent_repo.get(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        return StateResponse(
            agent_id=agent_id,
            state=agent.status,
            model_id=getattr(agent, "model_id", "unknown")
        )

@app.post("/agent/{agent_id}/message")
async def send_message(agent_id: str, req: MessageRequest):
    try:
        await orch_manager.send_agent_message(req.sender_id, agent_id, req.content)
        return {"status": "sent", "receiver_id": agent_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/{agent_id}/goals")
async def add_goal(agent_id: str, req: GoalRequest):
    async with AsyncSessionLocal() as session:
        goal_repo = GoalRepository(session)
        goal_id = f"goal_{uuid.uuid4().hex[:8]}"
        await goal_repo.create_goal(goal_id, agent_id, req.description, req.priority)
        return {"status": "created", "goal_id": goal_id}

@app.get("/agent/{agent_id}/goals")
async def get_goals(agent_id: str):
    async with AsyncSessionLocal() as session:
        goal_repo = GoalRepository(session)
        goals = await goal_repo.get_active_goals(agent_id)
        return [{"goal_id": g.goal_id, "description": g.description, "priority": g.priority} for g in goals]

# Observability: WebSocket for Lifecycle streaming
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, agent_id: str, websocket: WebSocket):
        await websocket.accept()
        if agent_id not in self.active_connections:
            self.active_connections[agent_id] = []
        self.active_connections[agent_id].append(websocket)

    def disconnect(self, agent_id: str, websocket: WebSocket):
        if agent_id in self.active_connections:
            self.active_connections[agent_id].remove(websocket)

    async def broadcast(self, agent_id: str, message: dict):
        if agent_id in self.active_connections:
            for connection in self.active_connections[agent_id]:
                await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/agent/{agent_id}/lifecycle")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    await manager.connect(agent_id, websocket)
    try:
        while True:
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(agent_id, websocket)
