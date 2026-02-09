from telegram import Update
from telegram.ext import ContextTypes
from db.connection import get_session
from repositories.users import create_user, get_user_by_id
from services.expense_service import create_expense_with_split, get_user_balance
from services.balance_service import get_balance_with_names
from decimal import Decimal

async def user_exists(session, userID):
    user = get_user_by_id(session, userID)
    return (user) ? True : False

async def ensure_user_exists(session, userID, user_name, first_name):
    if !user_exists(session, userID):
        create_user(session, username=user_name, first_name=first_name)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = get_session()
    
    ensure_user_exists(session, user.id, user.user_name, user.first_name)
    
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
                desc=description,
                amount=amount,
                paid_by=user_id,
                group_id=None,  # Personal expense for now
                IDs=[user_id],
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


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's balance - who owes them and who they owe"""
    session = get_session()
    user_id = update.effective_user.id
    
    try:
        await ensure_user_exists(session, update.effective_user)
        
        # Get balances
        balances = get_balance_with_names(session, user_id)
        
        if not balances:
            await update.message.reply_text("💰 You have no expenses yet!")
            return
        
        message = "💰 Your Balance:\n\n"
        
        for name, amount in balances:
            if amount > 0:
                message += f"✅ {name} owes you €{amount:.2f}\n"
            else:
                message += f"❌ You owe {name} €{abs(amount):.2f}\n"
        
        await update.message.reply_text(message)
        
    finally:
        session.close()
