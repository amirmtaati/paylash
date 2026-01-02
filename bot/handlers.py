from telegram import Update
from telegram.ext import ContextTypes
from db.connection import get_session
from repositories.user_repository import create_user, get_user_by_id
from services import create_expense_with_split, get_user_balance
from decimal import Decimal

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = get_session()
    
    try:
        await update.message.reply_text(
            f"Hello {user.first_name}!\n\n"
            "Commands:\n"
            "/addexpense - Add new expense\n"
            "/balance - Check your balance\n"
            "/creategroup - Create a group"
        )
    finally:
        session.close()

