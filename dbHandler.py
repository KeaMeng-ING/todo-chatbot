import os
import asyncpg
from typing import Optional
import datetime


DATABASE_URL = os.getenv('DATABASE_URL')

async def test_database():
    """Test database connection"""
    connection_string = DATABASE_URL
    try:
        pool = await asyncpg.create_pool(connection_string)
        async with pool.acquire() as conn:
            time = await conn.fetchval('SELECT NOW();')
            version = await conn.fetchval('SELECT version();')
        await pool.close()
        print('Current time:', time)
        print('PostgreSQL version:', version)
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
   


