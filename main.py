import os
import asyncio
from datetime import datetime, timedelta
from aiHandler import parse_ai_response, get_ai_response
from dbHandler import test_database, insert_task, get_upcoming_tasks, mark_task_alerted,get_tomorrow_tasks, get_all_tasks

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Load environment variables
load_dotenv()
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = """
        Hello! I'm your To-Do assistant. Here's what I can do:

        📝 Add tasks: "Add call mom tomorrow at 2pm"
        📋 List tasks: "Show my tasks" 
        ✅ Mark done: "Mark task done"
        🗑️ Delete tasks: "Delete task"

        I'll also send you:
        🔔 2-hour alerts for upcoming tasks
        🌅 Daily reminders at 9 PM for tomorrow's tasks

        Just tell me what you need to do!
    """
    await update.message.reply_text(welcome_message)


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userId = update.message.from_user.id
    text = update.message.text

    # Check if text is None
    if text is None:
        await update.message.reply_text("I can only process text messages. Please send me a text message with your task.")
        return

    response = await get_ai_response(text)
    if response:
        action, task, duedate, duetime, note = await parse_ai_response(response)
        print(f"Action: {action}, Task: {task}, Due date: {duedate}, Due time: {duetime}, Note: {note}")
        if action == 'add':
            await insert_task(action, task, duedate, duetime, note, userId)
        elif action == 'list':
            tasks = await get_all_tasks(userId)
            await update.message.reply_text(tasks)
            return

        await update.message.reply_text(response)
    else:
        await update.message.reply_text("I am temporarily unavailable. Please try again later.")

async def check_upcoming_tasks(app):
    """Check for tasks due in the next 2 hours and send alerts every hour"""
    while True:
        try:
            print("Checking for upcoming tasks...")
            upcoming_tasks = await get_upcoming_tasks()
            
            for task in upcoming_tasks:
                task_id = task['id']
                task_name = task['task']
                note = task['note']
                user_id = task['userid']
                due_date = task['duedate']
                due_time = task['duetime']
                
                # Calculate how much time is left
                due_datetime = datetime.combine(due_date, due_time)
                time_left = due_datetime - datetime.now()
                hours_left = int(time_left.total_seconds() / 3600)
                minutes_left = int((time_left.total_seconds() % 3600) / 60)
                
                # Create alert message
                alert_message = f"🚨 Deadline Approach!\n\n"
                alert_message += f"📝 Task: {task_name}\n"
                alert_message += f"⏰ Due: {due_date} at {due_time}\n"
                alert_message += f"⏳ Time left: {hours_left}h {minutes_left}m\n"
                
                if note:
                    alert_message += f"📄 Note: {note}\n"
                
                # Send alert to user
                try:
                    await app.bot.send_message(
                        chat_id=user_id,
                        text=alert_message
                    )
                    print(f"Alert sent to user {user_id} for task: {task_name}")
                    
                    # Mark task as alerted to prevent duplicate notifications
                    await mark_task_alerted(task_id)
                    
                except Exception as send_error:
                    print(f"Failed to send alert to user {user_id}: {send_error}")
            
            if not upcoming_tasks:
                print("No upcoming tasks found.")
            
        except Exception as e:
            print(f"Error checking upcoming tasks: {e}")
        
        # Wait 1 hour (3600 seconds) before checking again
        print("Waiting 1 hour before next check...")
        await asyncio.sleep(7200)

async def send_daily_reminders(app):
    """Send daily reminders at 21:00 about tomorrow's tasks"""
    while True:
        try:
            now = datetime.now()
            
            # Calculate next 21:00
            target_time = now.replace(hour=21, minute=0, second=0, microsecond=0)
            # target_time = now + timedelta(seconds=10)

            if now >= target_time:
                # If it's already past 21:00 today, schedule for tomorrow
                target_time += timedelta(days=1)
            
            # Calculate sleep time until next 21:00
            sleep_seconds = (target_time - now).total_seconds()
            
            print(f"Daily reminder scheduled for {target_time}. Sleeping for {sleep_seconds/3600:.2f} hours...")
            await asyncio.sleep(sleep_seconds)
            
            # Send reminders
            print("Sending daily reminders for tomorrow's tasks...")
            tomorrow_tasks = await get_tomorrow_tasks()
            
            # Group tasks by user
            user_tasks = {}
            for task in tomorrow_tasks:
                user_id = task['userid']
                if user_id not in user_tasks:
                    user_tasks[user_id] = []
                user_tasks[user_id].append(task)
            
            # Send reminders to each user
            for user_id, tasks in user_tasks.items():
                tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                
                # Create reminder message
                reminder_message = f"🌅 Good Evening! Here are your tasks for tomorrow ({tomorrow_date}):\n\n"
                
                for i, task in enumerate(tasks, 1):
                    task_name = task['task']
                    note = task['note']
                    due_time = task['duetime']
                    
                    reminder_message += f"{i}. 📝 {task_name}\n"
                    if due_time:
                        reminder_message += f"   ⏰ {due_time}\n"
                    if note:
                        reminder_message += f"   📄 {note}\n"
                    reminder_message += "\n"
                
                reminder_message += "Have a great evening! 🌙"
                
                # Send reminder to user
                try:
                    await app.bot.send_message(
                        chat_id=user_id,
                        text=reminder_message
                    )
                    print(f"Daily reminder sent to user {user_id} with {len(tasks)} tasks")
                except Exception as send_error:
                    print(f"Failed to send daily reminder to user {user_id}: {send_error}")
            
            if not tomorrow_tasks:
                print("No tasks due tomorrow.")
                
        except Exception as e:
            print(f"Error in daily reminder system: {e}")
            await asyncio.sleep(3600)  # Wait 1 hour before retrying

async def main():
    # Test database connection first
    # await test_database()
    
    # Build the bot
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    print("Bot is running...")
    
    # Initialize and start the bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Start the alert checker in the background
    print("Starting background task checker...")
    alert_task = asyncio.create_task(check_upcoming_tasks(app))
    
    print("Starting daily reminder system...")
    daily_reminder_task = asyncio.create_task(send_daily_reminders(app))
    # Keep the bot running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("Bot stopped by user")
        alert_task.cancel()
        daily_reminder_task.cancel()
        await asyncio.gather(alert_task, daily_reminder_task, return_exceptions=True)
    finally:
        # Clean shutdown
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())