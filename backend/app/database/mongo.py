import motor.motor_asyncio
from app.config.settings import settings
import logging

logger = logging.getLogger("rag_pipeline")

class Database:
    client: motor.motor_asyncio.AsyncIOMotorClient = None
    db = None

db = Database()

def get_db():
    """Returns the MongoDB database instance."""
    return db.db

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    db.client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
    db.db = db.client[settings.DATABASE_NAME]
    logger.info("Connected to MongoDB!")

    # Ensure indexes (e.g., unique email and username)
    await db.db["users"].create_index("email", unique=True)
    await db.db["users"].create_index("username", unique=True)
    await db.db["documents"].create_index("filename")
    await db.db["evaluations"].create_index("document_id")

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db.client:
        db.client.close()
    logger.info("MongoDB connection closed!")
