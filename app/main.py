from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.error_handlers import register_error_handlers
from app.core.logging_config import configure_logging
from app.middlewares.request_logger import request_logging_middleware
from app.core.responses import success_response
from app.db.mongo import (
    close_mongo_connection,
    connect_to_mongo,
    get_database,
)
from app.api.weather import router as weather_router
from app.api.analysis import router as analysis_router


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title=settings.APP_NAME,
    description="Analyze historical weather and climate hazard trends.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
)

app.middleware("http")(request_logging_middleware)
register_error_handlers(app)


@app.get("/")
async def root():
    return success_response(
        "Climate Hazard API is running",
        {"status": "healthy"},
    )


@app.get("/health")
async def health_check():
    database = await get_database()
    await database.command("ping")

    return success_response(
        "Database connection is healthy",
        {"database": "connected"},
    )


app.include_router(weather_router)
app.include_router(analysis_router)
