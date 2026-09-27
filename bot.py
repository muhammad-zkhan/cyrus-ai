from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = "8825175243:AAEtZzF44CDTQZr0prQmZPvpumkT_EkrWok"

MODEL = "qwen3:4b"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Main Ultron hoon 🤖\nMessage bhejo."
    )

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    try:
        response = await asyncio.to_thread(
            ollama.chat,
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are Ultron, a helpful personal AI assistant. Reply naturally and briefly. You can understand English and Roman Urdu."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            think=False
        )

        answer = response.message.content
        await update.message.reply_text(answer)

    except Exception as e:
        await update.message.reply_text("AI se connection mein problem aa rahi hai.")

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

print("Ultron AI bot chal raha hai...")
app.run_polling()