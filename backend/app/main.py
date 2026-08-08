from fastapi import FastAPI

from app.api.routes.health import router as health_router


app = FastAPI(
    title="FlowPilot",
    description="Agentic workflow automation platform",
    version="0.1.0",
)


app.include_router(
    health_router,
    prefix="/api/v1",
)


@app.get("/")
async def root():
    return {
        "message": "FlowPilot API is running"
    }