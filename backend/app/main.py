# Main FastAPI Application for AI-Powered Tuxemon
# Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
import time
import uvicorn

from app.config import get_settings
from app.database import (
    create_db_and_tables,
    close_db_connections,
    init_qdrant_collections,
    check_postgres_health,
    check_redis_health,
    check_qdrant_health,
    verify_critical_indexes,
)
from app.tasks.background_tasks import background_tasks

# Import API routes
from app.api.routes import auth, game, npcs, combat, admin, inventory, shop, gossip

# Import AI manager for initialization
from app.ai.ai_manager import ai_manager

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("🚀 Starting AI-Powered Tuxemon Backend...")

    try:
        # Initialize databases
        await create_db_and_tables()
        init_qdrant_collections()
        logger.info("✅ Database connections initialized")

        # Health checks
        postgres_healthy = await check_postgres_health()
        redis_healthy = await check_redis_health()
        qdrant_healthy = check_qdrant_health()

        logger.info(f"📊 Health Status - Postgres: {postgres_healthy}, Redis: {redis_healthy}, Qdrant: {qdrant_healthy}")

        if not all([postgres_healthy, redis_healthy, qdrant_healthy]):
            logger.warning("⚠️ Some database connections are unhealthy")

        # Verify critical database indexes for performance
        indexes_healthy = await verify_critical_indexes()
        if not indexes_healthy:
            logger.warning("⚠️ Database performance may be degraded due to missing indexes")

        # Initialize AI manager
        await ai_manager.initialize()
        logger.info("✅ AI manager initialized")

        # Start background tasks
        await background_tasks.start()
        logger.info("✅ Background tasks started")

    except Exception as e:
        logger.error(f"❌ Failed to initialize databases: {e}")
        raise

    yield

    # Shutdown
    logger.info("🛑 Shutting down AI-Powered Tuxemon Backend...")

    # Stop background tasks
    await background_tasks.stop()
    logger.info("✅ Background tasks stopped")

    await close_db_connections()
    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AI-Powered Tuxemon Backend",
    description="Mobile-first Pokemon-style game with AI NPCs",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://192.168.7.188:5173",  # Local IP for mobile testing
        "https://*.netlify.app",  # Netlify deployment
        "https://*.vercel.app",   # Vercel deployment
        "https://*.onrender.com", # Render deployment (production)
        "https://tuxemon-frontend.onrender.com",  # Production frontend URL
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": str(request.url)}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    postgres_healthy = await check_postgres_health()
    redis_healthy = await check_redis_health()
    qdrant_healthy = check_qdrant_health()

    status = "healthy" if all([postgres_healthy, redis_healthy, qdrant_healthy]) else "degraded"

    return {
        "status": status,
        "timestamp": time.time(),
        "services": {
            "postgres": "healthy" if postgres_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
            "qdrant": "healthy" if qdrant_healthy else "unhealthy",
        },
        "version": settings.app_version,
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "message": "AI-Powered Tuxemon Backend",
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "disabled",
        "health": "/health",
    }


# Include API routers with /api/v1 prefix
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(game.router, prefix="/api/v1/game", tags=["Game"])
app.include_router(npcs.router, prefix="/api/v1/npcs", tags=["NPCs"])
app.include_router(combat.router, prefix="/api/v1/combat", tags=["Combat"])
app.include_router(inventory.router, prefix="/api/v1/inventory", tags=["Inventory"])
app.include_router(shop.router, prefix="/api/v1/shop", tags=["Shop"])
app.include_router(gossip.router, prefix="/api/v1/gossip", tags=["Gossip"])

if settings.debug:
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )