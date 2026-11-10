import asyncio
import os
from mediapatner.database.db import Database
from mediapatner.database.repository import Repository

async def main():
    db_path = "data/test_quick.db"
    db = Database(db_path=db_path)
    print("Initializing DB...")
    await db.init()
    print("DB initialized!")
    repo = Repository(db)
    print("Upserting user...")
    await repo.upsert_user(999, "adm", "Admin User")
    print("User upserted!")
    u = await repo.get_user(999)
    print("Fetched user:", u)
    active_devs = await repo.get_active_devices()
    print("Active devices:", active_devs)
    report_chat = await repo.get_report_chat_id()
    print("Report chat ID:", report_chat)
    op_cfg = await repo.get_operational_config()
    print("Op config:", op_cfg)

if __name__ == "__main__":
    asyncio.run(main())
