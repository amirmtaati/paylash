from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot.handlers import start, add_expense
import os

def main():
    token = "8529720422:AAEOTNA8dwYf0Z98qyvxUmtYKY3NESvaTSo"
    
    app = Application.builder().token(token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addexpense", add_expense))
    
    print("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
