from telegram import Update
from telegram.ext import ContextTypes
from db.connection import get_session
from repositories.users import create_user, get_user_by_id
from services.expense_service import create_expense_with_split, get_user_balance
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


async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addexpense 50 Dinner"""
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addexpense <amount> <description>")
        return
    
    try:
        amount = Decimal(context.args[0])
        description = " ".join(context.args[1:])
        user_id = update.effective_user.id
        
        session = get_session()
        try:
            # For now: create expense without group, just for this user
            expense_id = create_expense_with_split(
                session=session,
                description=description,
                amount=amount,
                paid_by=user_id,
                group_id=None,  # Personal expense for now
                participant_ids=[user_id],
                split_type="equal"
            )
            
            await update.message.reply_text(
                f"✅ Expense added!\n"
                f"Amount: €{amount}\n"
                f"Description: {description}"
            )
        finally:
            session.close()
            
    except ValueError as e:
        await update.message.reply_text(f"Error: {e}")
