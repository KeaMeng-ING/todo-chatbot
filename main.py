import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from dotenv import load_dotenv
# import datetime

load_dotenv()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)
# Replace with your BotFather token
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Respond to /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me a message and I’ll echo it back.")

# Respond to any text message
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # now = datetime.datetime.now()
    # current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    
    completion = client.chat.completions.create(
        messages=[
            {
            "role": "system",
            "content": "You are a To-Do app assistant. Your job is to help the user manage their tasks. Understand natural language instructions and convert them into clear actions: add a task, list tasks, mark tasks as done, delete tasks, or update tasks. Keep your replies short and direct. Always confirm the action clearly. If the request is unclear, ask questions to clarify. This To-Do app has columns: [action, task, duedate, note]. You must always return a JSON object like this:\n\n{\n  \"action\": \"add\",  // can be add, list, done, delete, update\n  \"task\": \"Call mom\",\n  \"duedate\": \"2025-07-16\",  // use ISO format YYYY-MM-DD or null if none\n  \"note\": \"Ask about her trip\"\n}\n\nIf there is no specific task, duedate, or note, set them to null."
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
    
    # Get the response from the completion
    response = completion.choices[0].message.content
    await update.message.reply_text(response)

    # await update.message.reply_text(f"Echo: {text}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
