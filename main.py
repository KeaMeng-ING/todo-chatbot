import os
import asyncio
from datetime import datetime, timedelta
from aiHandler import parse_ai_response, get_ai_response
from dbHandler import test_database, insert_task, get_upcoming_tasks, mark_task_alerted

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
    await update.message.reply_text("Hello! I'm your To-Do assistant. Send me tasks to manage!")

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
        if action:
            if duetime:
                print("duetime: " + duetime)
            await insert_task(action, task, duedate, duetime, note, userId)

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
                alert_message = f"🔔 Task Reminder!\n\n"
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
    
    # Keep the bot running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("Bot stopped by user")
        alert_task.cancel()
    finally:
        # Clean shutdown
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())