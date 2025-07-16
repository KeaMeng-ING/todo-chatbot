import os
import asyncpg
from typing import Optional
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
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
   
async def insert_task(
    action: str,
    task: Optional[str],
    duedate: Optional[str],
    note: Optional[str],
    userId: int,
):  
    connection_string = DATABASE_URL
    try:
        pool = await asyncpg.create_pool(connection_string)
        async with pool.acquire() as conn:
            # Convert the duedate string (YYYY-MM-DD) to datetime.date
            parsed_date = None
            if duedate:
                parsed_date = datetime.datetime.strptime(duedate, "%Y-%m-%d").date()

            await conn.execute(
                '''
                INSERT INTO tasks (action, task, duedate, note,userId)
                VALUES ($1, $2, $3, $4, $5)
                ''',
                action,
                task,
                parsed_date,
                note,
                userId
            )
        await pool.close()
        print("Task inserted successfully.")
    except Exception as e:
        print(f"Insert failed: {e}")


