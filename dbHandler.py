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
    duetime: Optional[str],
    note: Optional[str],
    userId: int
):  
    connection_string = DATABASE_URL

    try:
        pool = await asyncpg.create_pool(connection_string)
        async with pool.acquire() as conn:
            # Convert the duedate string (YYYY-MM-DD) to datetime.date
            parsed_date = None
            if duedate:
                parsed_date = datetime.datetime.strptime(duedate, "%Y-%m-%d").date()

            # Convert the duetime string (HH:MM) to datetime.time
            parsed_time = None
            if duetime:
                try:
                    parsed_time = datetime.datetime.strptime(duetime, "%H:%M").time()
                except ValueError:
                    print(f"Invalid time format: {duetime}, expected HH:MM")
                    parsed_time = None

        
            await conn.execute(
                '''
                INSERT INTO tasks (action, task, duedate, duetime, note, userId)
                VALUES ($1, $2, $3, $4, $5, $6)
                ''',
                action,
                task,
                parsed_date,
                parsed_time,
                note,
                userId
            )
        await pool.close()
        print("Task inserted successfully.")
    except Exception as e:
        print(f"Insert failed: {e}")

async def get_upcoming_tasks():
    """Get tasks that are due within the next 2 hours and haven't been alerted yet"""
    connection_string = DATABASE_URL
    try:
        pool = await asyncpg.create_pool(connection_string)
        async with pool.acquire() as conn:
            # Get current time and 2 hours from now
            now = datetime.datetime.now()
            two_hours_later = now + datetime.timedelta(hours=2)
            
            # Query for tasks due within the next 2 hours that haven't been alerted
            tasks = await conn.fetch(
                '''
                SELECT id, task, note, userid, duedate, duetime 
                FROM tasks 
                WHERE action = 'add' 
                AND duedate IS NOT NULL 
                AND duetime IS NOT NULL
                AND (duedate::timestamp + duetime::time) BETWEEN $1 AND $2
                AND (alerted IS NULL OR alerted = false)
                ''',
                now,
                two_hours_later
            )

            


        await pool.close()
        return tasks
    except Exception as e:
        print(f"Failed to get upcoming tasks: {e}")
        return []

async def mark_task_alerted(task_id: int):
    """Mark a task as alerted to avoid duplicate notifications"""
    connection_string = DATABASE_URL
    try:
        pool = await asyncpg.create_pool(connection_string)
        async with pool.acquire() as conn:
            await conn.execute(
                'UPDATE tasks SET alerted = true WHERE id = $1',
                task_id
            )
        await pool.close()
    except Exception as e:
        print(f"Failed to mark task as alerted: {e}")

async def get_tomorrow_tasks():
    """Get tasks that are due tomorrow"""
    connection_string = DATABASE_URL
    try:
        pool = await asyncpg.create_pool(connection_string)
        async with pool.acquire() as conn:
            # Get tomorrow's date
            tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).date()
            print(f"Fetching tasks due tomorrow: {tomorrow}")
            # Query for tasks due tomorrow
            tasks = await conn.fetch(
                '''
                SELECT task, note, userid, duedate, duetime 
                FROM tasks 
                WHERE action = 'add' 
                AND duedate = $1
                ORDER BY duetime ASC
                ''',
                tomorrow
            )


        await pool.close()
        return tasks
    except Exception as e:
        print(f"Failed to get tomorrow's tasks: {e}")
        return []
    
async def get_all_tasks(userId):
    """Get all upcoming tasks for a user"""
    connection_string = DATABASE_URL
    try:
        pool = await asyncpg.create_pool(connection_string)
        async with pool.acquire() as conn:

            tasks = await conn.fetch(
                '''
                SELECT id, task, note, userid, duedate, duetime, alerted, completed
                FROM tasks 
                WHERE action = 'add' 
                AND userid = $1
                AND (completed IS NULL OR completed = false)
                ORDER BY 
                    CASE WHEN duedate IS NULL THEN 1 ELSE 0 END,
                    duedate ASC, 
                    CASE WHEN duetime IS NULL THEN 1 ELSE 0 END,
                    duetime ASC
                ''',
                userId
            )

        await pool.close()
        return tasks
    except Exception as e:
        print(f"Failed to get all tasks for user {userId}: {e}")
        return []


async def update_task_completion(task_id: int, completed: bool = True):
    """Mark a task as completed or incomplete"""
    connection_string = DATABASE_URL
    try:
        pool = await asyncpg.create_pool(connection_string)
        async with pool.acquire() as conn:
            await conn.execute(
                'UPDATE tasks SET completed = $1 WHERE id = $2',
                completed,
                task_id
            )
        await pool.close()
        print(f"Task {task_id} marked as {'completed' if completed else 'incomplete'}")
        return True
    except Exception as e:
        print(f"Failed to update task completion: {e}")
        return False

async def get_user_tasks_for_selection(userId):
    """Get incomplete tasks for a user to allow selection"""
    connection_string = DATABASE_URL
    try:
        pool = await asyncpg.create_pool(connection_string)
        async with pool.acquire() as conn:
            tasks = await conn.fetch(
                '''
                SELECT id, task, duedate, duetime
                FROM tasks 
                WHERE action = 'add' 
                AND userid = $1
                AND (completed IS NULL OR completed = false)
                ORDER BY 
                    CASE WHEN duedate IS NULL THEN 1 ELSE 0 END,
                    duedate ASC, 
                    CASE WHEN duetime IS NULL THEN 1 ELSE 0 END,
                    duetime ASC
                ''',
                userId
            )
        await pool.close()
        return tasks
    except Exception as e:
        print(f"Failed to get tasks for selection: {e}")
        return []
    
async def delete_task(task_id: int):
    """Delete a task"""
    connection_string = DATABASE_URL
    try:
        pool = await asyncpg.create_pool(connection_string)
        async with pool.acquire() as conn:
            await conn.execute(
                'DELETE FROM tasks WHERE id = $1',
                task_id
            )
        await pool.close()
        print(f"Task {task_id} deleted successfully")
        return True
    except Exception as e:
        print(f"Failed to delete task: {e}")
        return False