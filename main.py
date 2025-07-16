import os

import asyncio
from aiHandler import parse_ai_response, get_ai_response
from dbHandler import test_database, insert_task

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

    response = await get_ai_response(text)
    if response:
        action, task, duedate, duetime, note = await parse_ai_response(response)
        if action:
            print("duetime" + duetime)
            await insert_task(action, task, duedate, duetime, note, userId)

        await update.message.reply_text(response)
    else:
        await update.message.reply_text("I am temporarily unavailable. Please try again later.")

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
    
    # Keep the bot running
    try:
        # This will run indefinitely until interrupted
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    finally:
        # Clean shutdown
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())