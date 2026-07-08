import asyncio
import motor.motor_asyncio
import sys

async def main():
    try:
        url = "mongodb+srv://madipellirithvik898_db_user:%40gurudev12@cluster0.fns97bk.mongodb.net/?appName=Cluster0"
        print("Connecting...", flush=True)
        client = motor.motor_asyncio.AsyncIOMotorClient(
            url, 
            tls=True,
            tlsAllowInvalidCertificates=True
        )
        db = client["ragdb"]
        print("Pinging db...", flush=True)
        await db.command("ping")
        print("Success!", flush=True)
        client.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
