import os

import datetime
import asyncio
from typing import Optional
from prompt import system_prompt
from aiHandler import parse_ai_response
from dbHandler import test_database

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from groq import Groq
import google.generativeai as genai
import asyncpg

# Load environment variables
load_dotenv()
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATABASE_URL = os.getenv('DATABASE_URL')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your To-Do assistant. Send me tasks to manage!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userId = update.message.from_user.id
    text = update.message.text
    
    try:
        client = Groq(
            api_key=GROQ_API_KEY,
        )
        completion = client.chat.completions.create(
            messages=[
                {
                "role": "system",
                "content": system_prompt
                },
                {
                    "role": "user",
                    "content": text  
                }
            ], 
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_completion_tokens=1024,
            top_p=1,
            stream=False,  
            stop=None,
        )
        response = completion.choices[0].message.content


        action, task, duedate, note = await parse_ai_response(response)
        if action:
            print(f"Action: {action}")
            print(f"Task: {task}")
            print(f"Due date: {duedate}")
            print(f"Note: {note}")

            await insert_task(action, task, duedate, note,userId)
        
        await update.message.reply_text(response)
        
    except Exception as e:
        print(f"Groq API failed: {e}")
        print("Trying Gemini as fallback...")
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.5-flash')
        try:
            full_prompt = f"{system_prompt}\n\nUser: {text}"
            gemini_response = gemini_model.generate_content(full_prompt)
            await update.message.reply_text(gemini_response.text)
            
        except Exception as gemini_error:
            print(f"Gemini API also failed: {gemini_error}")
            await update.message.reply_text("Sorry, both AI services are temporarily unavailable. Please try again later.")

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


async def main():
    # Test database connection first
    await test_database()
    
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