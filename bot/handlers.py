from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from db.connection import get_session
from repositories.users import create_user, get_user_by_id
from repositories.groups import (
    create_group, add_member_to_group, get_groups_for_user, 
    get_members_of_group, get_member_count, get_group_by_id
)
from services.expense_service import create_expense_with_split
from services.balance_service import get_balance_with_names
from decimal import Decimal

# Conversation states
WAITING_FOR_GROUP_NAME, WAITING_FOR_MEMBER_SELECTION, WAITING_FOR_GROUP_SELECTION = range(3)

def user_exists(session, user_id):
    """Check if user exists in database"""
    user = get_user_by_id(session, user_id)
    return user is not None

def ensure_user_exists(session, user_id, username, first_name):
    """Create user if they don't exist"""
    if not user_exists(session, user_id):
        create_user(session, user_id=user_id, username=username, first_name=first_name)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = get_session()
    
    try:
        ensure_user_exists(session, user.id, user.username, user.first_name)
        
        await update.message.reply_text(
            f"Hello {user.first_name}! 👋\n\n"
            "Welcome to PayLash - Split bills with friends!\n\n"
            "Commands:\n"
            "/creategroup - Create a new group\n"
            "/addexpense - Add expense to a group\n"
            "/balance - Check your balance\n"
            "/mygroups - View your groups"
        )
    finally:
        session.close()


async def create_group_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the group creation process"""
    user = update.effective_user
    session = get_session()
    
    try:
        ensure_user_exists(session, user.id, user.username, user.first_name)
        
        await update.message.reply_text(
            "Let's create a new group! 🎉\n\n"
            "What would you like to name this group?\n"
            "(e.g., 'Pizza Night', 'Trip to Rome', 'Apartment 4B')"
        )
        
        return WAITING_FOR_GROUP_NAME
        
    finally:
        session.close()


async def receive_group_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive group name and create the group"""
    group_name = update.message.text.strip()
    user = update.effective_user
    session = get_session()
    
    try:
        # Create the group
        group = create_group(session, name=group_name, created_by=user.id)
        group_id = group[0]
        
        # Add creator as first member
        add_member_to_group(session, group_id=group_id, user_id=user.id)
        
        # Store group_id in context for next steps
        context.user_data['current_group_id'] = group_id
        
        await update.message.reply_text(
            f"✅ Group '{group_name}' created!\n\n"
            f"Now, let's add members to this group.\n"
            f"Forward me a message from someone or have them send /start to this bot first.\n\n"
            f"Then send their Telegram user ID (number), or type 'done' when finished.\n"
            f"(Remember: groups need at least 2 members to create expenses!)"
        )
        
        return WAITING_FOR_MEMBER_SELECTION
        
    finally:
        session.close()


async def add_group_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add members to the group"""
    text = update.message.text.strip().lower()
    
    if text == 'done':
        group_id = context.user_data.get('current_group_id')
        session = get_session()
        
        try:
            member_count = get_member_count(session, group_id)
            
            if member_count < 2:
                await update.message.reply_text(
                    f"⚠️ Your group only has {member_count} member(s).\n"
                    f"You need at least 2 members to create expenses.\n\n"
                    f"Please add more members or type 'cancel' to abort."
                )
                return WAITING_FOR_MEMBER_SELECTION
            
            group = get_group_by_id(session, group_id)
            group_name = group[1]  # name is second column
            
            await update.message.reply_text(
                f"🎉 Group '{group_name}' is ready with {member_count} members!\n\n"
                f"You can now:\n"
                f"/addexpense - Add an expense to this group\n"
                f"/mygroups - View all your groups"
            )
            
            # Clear context
            context.user_data.clear()
            return ConversationHandler.END
            
        finally:
            session.close()
    
    elif text == 'cancel':
        await update.message.reply_text("Group creation cancelled.")
        context.user_data.clear()
        return ConversationHandler.END
    
    else:
        # Try to parse as user ID
        try:
            member_id = int(text)
            group_id = context.user_data.get('current_group_id')
            session = get_session()
            
            try:
                # Check if user exists
                if not user_exists(session, member_id):
                    await update.message.reply_text(
                        f"❌ User {member_id} hasn't started the bot yet.\n"
                        f"They need to send /start to @your_bot_name first!\n\n"
                        f"Add another member or type 'done' to finish."
                    )
                    return WAITING_FOR_MEMBER_SELECTION
                
                # Add member
                add_member_to_group(session, group_id=group_id, user_id=member_id)
                member_count = get_member_count(session, group_id)
                
                await update.message.reply_text(
                    f"✅ Member added! Total members: {member_count}\n\n"
                    f"Add another member ID or type 'done' to finish."
                )
                
                return WAITING_FOR_MEMBER_SELECTION
                
            finally:
                session.close()
                
        except ValueError:
            await update.message.reply_text(
                "Please send a valid user ID (number) or 'done' to finish."
            )
            return WAITING_FOR_MEMBER_SELECTION


async def my_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all groups the user is part of"""
    user = update.effective_user
    session = get_session()
    
    try:
        ensure_user_exists(session, user.id, user.username, user.first_name)
        
        groups = get_groups_for_user(session, user.id)
        
        if not groups:
            await update.message.reply_text(
                "You're not part of any groups yet.\n"
                "Use /creategroup to create one!"
            )
            return
        
        message = "📋 Your Groups:\n\n"
        for group in groups:
            group_id = group[0]
            group_name = group[1]
            member_count = get_member_count(session, group_id)
            message += f"• {group_name} ({member_count} members) - ID: {group_id}\n"
        
        await update.message.reply_text(message)
        
    finally:
        session.close()


async def add_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding an expense - first select group"""
    user = update.effective_user
    session = get_session()
    
    try:
        ensure_user_exists(session, user.id, user.username, user.first_name)
        
        groups = get_groups_for_user(session, user.id)
        
        if not groups:
            await update.message.reply_text(
                "❌ You need to create a group first!\n"
                "Use /creategroup to get started."
            )
            return ConversationHandler.END
        
        # Build keyboard with groups
        keyboard = []
        for group in groups:
            group_id = group[0]
            group_name = group[1]
            member_count = get_member_count(session, group_id)
            
            # Only show groups with 2+ members
            if member_count >= 2:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{group_name} ({member_count} members)",
                        callback_data=f"group_{group_id}"
                    )
                ])
        
        if not keyboard:
            await update.message.reply_text(
                "❌ None of your groups have enough members (minimum 2).\n"
                "Add more members to your groups first!"
            )
            return ConversationHandler.END
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Which group is this expense for?",
            reply_markup=reply_markup
        )
        
        return WAITING_FOR_GROUP_SELECTION
        
    finally:
        session.close()


async def receive_group_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle group selection for expense"""
    query = update.callback_query
    await query.answer()
    
    group_id = int(query.data.split('_')[1])
    context.user_data['expense_group_id'] = group_id
    
    session = get_session()
    try:
        group = get_group_by_id(session, group_id)
        group_name = group[1]
        
        await query.edit_message_text(
            f"Adding expense to: {group_name}\n\n"
            f"Please send the expense details in this format:\n"
            f"`<amount> <description>`\n\n"
            f"Example: `50 Pizza dinner`",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END  # We'll handle the next message in add_expense_details
        
    finally:
        session.close()


async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addexpense command - wrapper to start conversation"""
    return await add_expense_start(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current conversation"""
    await update.message.reply_text("Operation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's balance - who owes them and who they owe"""
    session = get_session()
    user_id = update.effective_user.id
    
    try:
        ensure_user_exists(session, user_id, update.effective_user.username, update.effective_user.first_name)
        
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


# This would be called from a message handler after group selection
async def handle_expense_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense amount and description after group is selected"""
    
    # Check if we have a group selected
    if 'expense_group_id' not in context.user_data:
        await update.message.reply_text(
            "Please use /addexpense to start adding an expense."
        )
        return
    
    try:
        # Parse message: "50 Pizza dinner"
        parts = update.message.text.strip().split(maxsplit=1)
        
        if len(parts) < 2:
            await update.message.reply_text(
                "Please use format: `<amount> <description>`\n"
                "Example: `50 Pizza dinner`",
                parse_mode='Markdown'
            )
            return
        
        amount = Decimal(parts[0])
        description = parts[1]
        user_id = update.effective_user.id
        group_id = context.user_data['expense_group_id']
        
        session = get_session()
        try:
            # Get all members of the group
            members = get_members_of_group(session, group_id)
            member_ids = [member[1] for member in members]  # user_id is second column
            
            # Create expense split equally among all members
            expense_id = create_expense_with_split(
                session=session,
                desc=description,
                amount=amount,
                paid_by=user_id,
                group_id=group_id,
                IDs=member_ids,
                split_type="equal"
            )
            
            group = get_group_by_id(session, group_id)
            group_name = group[1]
            split_amount = amount / len(member_ids)
            
            await update.message.reply_text(
                f"✅ Expense added to '{group_name}'!\n\n"
                f"💰 Total: €{amount}\n"
                f"📝 Description: {description}\n"
                f"👥 Split {len(member_ids)} ways: €{split_amount:.2f} each\n\n"
                f"Use /balance to see who owes what."
            )
            
            # Clear the stored group
            context.user_data.pop('expense_group_id', None)
            
        finally:
            session.close()
            
    except ValueError as e:
        await update.message.reply_text(f"❌ Error: Invalid amount. Please use a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
