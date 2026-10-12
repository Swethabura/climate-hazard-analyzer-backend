from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase

from app.core.config import settings

client: AsyncMongoClient | None = None
database: AsyncDatabase | None = None


async def connect_to_mongo() -> None:
    global client, database

    mongo_client = AsyncMongoClient(settings.MONGODB_URL)

    try:
        await mongo_client.admin.command("ping")

        mongo_database = mongo_client[settings.MONGODB_DATABASE]

        await mongo_database["daily_weather"].create_index(
            [
                ("latitude", 1),
                ("longitude", 1),
                ("date", 1),
                ("source", 1),
                ("model", 1),
            ],
            unique=True,
            name="unique_daily_weather_record",
        )

        client = mongo_client
        database = mongo_database

    except Exception:
        await mongo_client.close()
        raise


async def close_mongo_connection() -> None:
    global client, database

    if client is not None:
        await client.close()

    client = None
    database = None


async def get_database() -> AsyncDatabase:
    if database is None:
        raise RuntimeError("MongoDB has not been initialized")

    return database