from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.employees import router as employees_router
from app.api.routes.workflows import router as workflows_router


app = FastAPI(
    title="FlowPilot",
    description="Agentic workflow automation platform",
    version="0.1.0",
)


app.include_router(
    employees_router,
    prefix="/api/v1",
)

app.include_router(
    health_router,
    prefix="/api/v1",
)

app.include_router(
    auth_router,
    prefix="/api/v1",
)

app.include_router(
    workflows_router,
    prefix="/api/v1",
)


@app.get("/")
async def root():
    return {
        "message": "FlowPilot API is running"
    }