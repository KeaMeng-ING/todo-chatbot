import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from dotenv import load_dotenv
import google.generativeai as genai
import asyncio
import asyncpg

load_dotenv()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-2.5-flash')

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

system_prompt = "You are a To-Do app assistant. Your job is to help the user manage their tasks. Understand natural language instructions and convert them into clear actions: add a task, list tasks, mark tasks as done, delete tasks, or update tasks. Keep your replies short and direct. Always confirm the action clearly. If the request is unclear, ask questions to clarify. This To-Do app has columns: [action, task, duedate, note]. You must always return a JSON object like this:\n\n{\n  \"action\": \"add\",  // can be add, list, done, delete, update\n  \"task\": \"Call mom\",\n  \"duedate\": \"2025-07-16\",  // use ISO format YYYY-MM-DD or null if none\n  \"note\": \"Ask about her trip\"\n}\n\nIf there is no specific task, duedate, or note, set them to null. You should only return this JSON object when user give the task, otherwise, interact with the user in natural language. If the user asks for help, provide a brief guide on how to use the To-Do app. "

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your To-Do assistant. Send me tasks to manage!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    try:
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
        await update.message.reply_text(response)
        
    except Exception as e:
        print(f"Groq API failed: {e}")
        print("Trying Gemini as fallback...")
        
        try:
            full_prompt = f"{system_prompt}\n\nUser: {text}"
            gemini_response = gemini_model.generate_content(full_prompt)
            await update.message.reply_text(gemini_response.text)
            
        except Exception as gemini_error:
            print(f"Gemini API also failed: {gemini_error}")
            await update.message.reply_text("Sorry, both AI services are temporarily unavailable. Please try again later.")

async def test_database():
    """Test database connection"""
    connection_string = os.getenv('DATABASE_URL')
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