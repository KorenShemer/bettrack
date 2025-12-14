from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    client: Optional[AsyncIOMotorClient] = None
    
    @classmethod
    async def connect_db(cls):
        cls.client = AsyncIOMotorClient(os.getenv("MONGODB_URL"))
        print("✅ Connected to MongoDB")
    
    @classmethod
    async def close_db(cls):
        if cls.client:
            cls.client.close()
            print("❌ Closed MongoDB connection")
    
    @classmethod
    def get_database(cls):
        return cls.client[os.getenv("DATABASE_NAME")]

# Convenience function
def get_db():
    return Database.get_database()