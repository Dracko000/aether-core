from fastapi import FastAPI
from aether.api.routes import health

app = FastAPI(title="Aether Core API")
app.include_router(health.router)
