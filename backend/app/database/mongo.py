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

import certifi

async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    try:
        db.client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000,
            tlsAllowInvalidCertificates=True
        )
        # Attempt a ping to verify connection
        await db.client.admin.command('ping')
        db.db = db.client[settings.DATABASE_NAME]
        logger.info("Connected to MongoDB!")

        # Ensure indexes (e.g., unique email and username)
        await db.db["users"].create_index("email", unique=True)
        await db.db["users"].create_index("username", unique=True)
        await db.db["documents"].create_index("filename")
        await db.db["evaluations"].create_index("document_id")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        logger.error("Backend will start, but database operations will fail.")
        db.client = None
        db.db = None

async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db.client:
        db.client.close()
    logger.info("MongoDB connection closed!")
