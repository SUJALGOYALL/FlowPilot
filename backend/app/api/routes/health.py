from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.redis import redis_client


router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("")
async def health_check():
    return {
        "status": "healthy",
        "service": "FlowPilot",
    }


@router.get("/db")
async def database_health_check(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
        "test": result.scalar(),
    }


@router.get("/redis")
async def redis_health_check():
    result = await redis_client.ping()

    return {
        "status": "healthy",
        "redis": "connected",
        "ping": result,
    }