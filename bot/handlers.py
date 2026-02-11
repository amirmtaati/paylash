from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from db.connection import get_session
from repositories.users import (
    create_user, get_user_by_id, get_user_by_identifier, set_custom_id, normalize_custom_id
)
from repositories.groups import (
    create_group, add_member_to_group, get_groups_for_user, 
    get_members_of_group, get_member_count, get_group_by_id
)
from services.expense_service import create_expense_with_split
from services.balance_service import get_balance_with_names
from decimal import Decimal
import shlex

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


def is_group_creator(session, group_id, user_id):
    """Check whether the user created the group."""
    group = get_group_by_id(session, group_id)
    return bool(group and group[2] == user_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = get_session()
    
    try:
        ensure_user_exists(session, user.id, user.username, user.first_name)
        
        welcome_message = (
            f"👋 *Welcome, {user.first_name}!*\n\n"
            f"🎯 *PayLash* helps you split bills with friends effortlessly.\n\n"
            f"*Commands:*\n\n"
            f"💡 `/creategroup` - Start a new group\n"
            f"💸 `/addexpense` - Record an expense\n"
            f"📊 `/balance` - Check who owes what\n"
            f"📋 `/mygroups` - View your groups\n"
            f"🆔 `/setid <custom_id>` - Set your own shareable ID\n"
            f"👥 `/addmember <group> <id...>` - Add members quickly\n\n"
            f"_Your Telegram ID: `{user.id}`_"
        )
        
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown'
        )
    finally:
        session.close()


async def create_group_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the group creation process"""
    user = update.effective_user
    session = get_session()

    try:
        ensure_user_exists(session, user.id, user.username, user.first_name)

        if update.message and context.args:
            group_name = " ".join(context.args).strip()
            group = create_group(session, name=group_name, created_by=user.id)
            group_id = group[0]
            add_member_to_group(session, group_id=group_id, user_id=user.id)

            context.user_data['current_group_id'] = group_id
            context.user_data['group_name'] = group_name
            await update.message.reply_text(
                f"✅ Group *'{group_name}'* created!\n\n"
                "Now add members by sending each Telegram ID/custom ID one-by-one.\n"
                "When finished, send `done`.\n"
                "Send `cancel` to abort.",
                parse_mode='Markdown'
            )
            return WAITING_FOR_MEMBER_SELECTION

        await update.message.reply_text(
            "Let's create a new group! 🎉\n\n"
            "What would you like to name this group?\n"
            "(e.g., 'Pizza Night', 'Trip to Rome', 'Apartment 4B')\n\n"
            "Tip: You can also do this directly: `/creategroup <group_name>`",
            parse_mode='Markdown'
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
        group = create_group(session, name=group_name, created_by=user.id)
        group_id = group[0]
        add_member_to_group(session, group_id=group_id, user_id=user.id)
        
        # Store group_id in context for next steps
        context.user_data['current_group_id'] = group_id
        context.user_data['group_name'] = group_name
        
        await update.message.reply_text(
            f"✅ Group *'{group_name}'* created!\n\n"
            f"👥 *Current members:* 1 (you, the creator)\n\n"
            f"*How to add members:*\n"
            f"1️⃣ Forward any message from the person you want to add\n"
            f"2️⃣ Send their Telegram user ID (number) *or* custom ID (e.g. `john-doe`)\n"
            f"3️⃣ Type `done` after adding at least *one* more person (2 total members)\n\n"
            f"Type `cancel` to abort.",
            parse_mode='Markdown'
        )
        
        return WAITING_FOR_MEMBER_SELECTION

    finally:
        session.close()


async def add_group_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add members to the group - handles text messages and forwarded messages"""

    group_id = context.user_data.get('current_group_id')
    acting_user_id = update.effective_user.id

    session = get_session()
    try:
        if group_id and not is_group_creator(session, group_id, acting_user_id):
            await update.message.reply_text(
                "⚠️ Only the group creator can add members. You can still use /addexpense for this group."
            )
            return WAITING_FOR_MEMBER_SELECTION

    finally:
        session.close()
    
    if not update.message:
        return WAITING_FOR_MEMBER_SELECTION

    # Handle forwarded messages
    if update.message.forward_from:
        forwarded_user = update.message.forward_from
        member_id = forwarded_user.id
        member_name = forwarded_user.first_name or forwarded_user.username or "Unknown"
        
        group_id = context.user_data.get('current_group_id')
        session = get_session()
        
        try:
            # Check if user exists, if not create them
            if not user_exists(session, member_id):
                create_user(session, user_id=member_id, 
                           username=forwarded_user.username, 
                           first_name=forwarded_user.first_name)
            
            # Check if already in group
            members = get_members_of_group(session, group_id)
            if any(m[1] == member_id for m in members):
                await update.message.reply_text(
                    f"⚠️ {member_name} is already in this group!"
                )
                return WAITING_FOR_MEMBER_SELECTION
            
            # Add member
            add_member_to_group(session, group_id=group_id, user_id=member_id)
            member_count = get_member_count(session, group_id)
            
            await update.message.reply_text(
                f"✅ *{member_name}* added to group!\n\n"
                f"👥 Total members: {member_count}\n\n"
                f"Forward another message or type `done` when finished.",
                parse_mode='Markdown'
            )
            
            return WAITING_FOR_MEMBER_SELECTION
            
        finally:
            session.close()
    
    # Handle text input
    raw_text = update.message.text.strip()
    text = raw_text.lower()
    
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
            group_name = group[1]
            
            await update.message.reply_text(
                f"🎉 Group '{group_name}' is ready with {member_count} members!\n\n"
                f"You can now:\n"
                f"/addexpense - Add an expense to this group\n"
                f"/mygroups - View all your groups"
            )
            
            context.user_data.clear()
            return ConversationHandler.END
            
        finally:
            session.close()
    
    elif text == 'cancel':
        await update.message.reply_text("❌ Group creation cancelled.")
        context.user_data.clear()
        return ConversationHandler.END
    
    else:
        group_id = context.user_data.get('current_group_id')
        session = get_session()

        try:
            member = get_user_by_identifier(session, raw_text)
            if not member:
                await update.message.reply_text(
                    f"❌ I couldn't find `{raw_text}`.\n"
                    "Ask them to send /start first, then try their Telegram ID or custom ID.",
                    parse_mode='Markdown'
                )
                return WAITING_FOR_MEMBER_SELECTION

            member_id = member[0]

            # Check if already in group
            members = get_members_of_group(session, group_id)
            if any(m[1] == member_id for m in members):
                await update.message.reply_text("⚠️ This user is already in the group!")
                return WAITING_FOR_MEMBER_SELECTION

            # Add member
            add_member_to_group(session, group_id=group_id, user_id=member_id)
            member_count = get_member_count(session, group_id)

            custom_id = member[1]
            id_hint = f" (custom ID: {custom_id})" if custom_id else ""

            await update.message.reply_text(
                f"✅ Member added{id_hint}!\n\n"
                f"👥 Total members: {member_count}\n\n"
                "Add another or type `done`.",
                parse_mode='Markdown'
            )

            return WAITING_FOR_MEMBER_SELECTION

        finally:
            session.close()


async def my_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all groups the user is part of with beautiful formatting"""
    user = update.effective_user
    session = get_session()
    
    try:
        ensure_user_exists(session, user.id, user.username, user.first_name)
        
        groups = get_groups_for_user(session, user.id)
        
        if not groups:
            await update.message.reply_text(
                "📋 *Your Groups*\n\n"
                "You're not part of any groups yet.\n\n"
                "Create a group to start splitting expenses!",
                parse_mode='Markdown'
            )
            return
        
        message = "📋 *Your Groups*\n\n"
        
        for i, group in enumerate(groups, 1):
            group_id = group[0]
            group_name = group[1]
            member_count = get_member_count(session, group_id)
            
            # Add emoji based on group size
            if member_count == 2:
                emoji = "👥"
            elif member_count <= 5:
                emoji = "👨‍👩‍👦"
            else:
                emoji = "👨‍👩‍👧‍👦"
            
            message += f"{i}. {emoji} *{group_name}*\n"
            message += f"   └ {member_count} members • ID: `{group_id}`\n\n"
        
        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )
        
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

        selectable_groups = []
        message = "Select a group for this expense by sending the group ID or exact name:\n\n"
        for group in groups:
            group_id = group[0]
            group_name = group[1]
            member_count = get_member_count(session, group_id)

            if member_count >= 2:
                selectable_groups.append(group)
                message += f"• `{group_id}` — *{group_name}* ({member_count} members)\n"

        if not selectable_groups:
            await update.message.reply_text(
                "❌ None of your groups have enough members (minimum 2).\n"
                "Add more members to your groups first!"
            )
            return ConversationHandler.END

        context.user_data['expense_selectable_groups'] = {g[0]: g[1] for g in selectable_groups}
        await update.message.reply_text(message, parse_mode='Markdown')
        
        return WAITING_FOR_GROUP_SELECTION
        
    finally:
        session.close()


async def receive_group_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle group selection for expense"""
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("group_"):
        await query.message.reply_text(
            "Please choose a group from the list, or use /cancel to exit this flow."
        )
        return WAITING_FOR_GROUP_SELECTION

    try:
        group_id = int(query.data.split('_', maxsplit=1)[1])
    except (ValueError, IndexError):
        await query.message.reply_text(
            "That group selection looks invalid. Please choose one of the listed group buttons."
        )
        return WAITING_FOR_GROUP_SELECTION

    context.user_data['expense_group_id'] = group_id
    context.user_data.pop('expense_selectable_groups', None)
    
    session = get_session()
    try:
        group = get_group_by_id(session, group_id)
        group_name = group[1]
        
        await update.message.reply_text(
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


async def addmember(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add one or more members to a group owned by the caller.

    Usage: /addmember <group_name> <id1> [id2 ...]
    """
    user = update.effective_user
    if not update.message or not update.message.text:
        return

    payload = update.message.text.partition(' ')[2].strip()
    if not payload:
        await update.message.reply_text(
            "Usage: /addmember <group_name> <id1> [id2 ...]\n"
            "Examples:\n"
            "• /addmember Trip alice-01 123456789\n"
            "• /addmember Trip to Rome alice-01 123456789\n"
            "• /addmember \"Trip to Rome\" alice-01 123456789"
        )
        return

    try:
        tokens = shlex.split(payload)
    except ValueError:
        tokens = payload.split()

    if len(tokens) < 2:
        await update.message.reply_text(
            "Usage: /addmember <group_name> <id1> [id2 ...]"
        )
        return

    session = get_session()
    try:
        ensure_user_exists(session, user.id, user.username, user.first_name)

        owned_groups = [g for g in get_groups_for_user(session, user.id) if g[2] == user.id]

        group = None
        member_identifiers = []
        longest_match = -1

        for candidate in owned_groups:
            name_tokens = candidate[1].strip().split()
            if not name_tokens or len(name_tokens) >= len(tokens):
                continue

            if [t.lower() for t in tokens[:len(name_tokens)]] == [t.lower() for t in name_tokens]:
                if len(name_tokens) > longest_match:
                    longest_match = len(name_tokens)
                    group = candidate
                    member_identifiers = tokens[len(name_tokens):]

        if not group:
            # Fallback: explicit quoted name support from /addmember "My Group" user1 user2
            quoted_name = tokens[0]
            direct_group = next((g for g in owned_groups if g[1].lower() == quoted_name.lower()), None)
            if direct_group:
                group = direct_group
                member_identifiers = tokens[1:]

        if group and not member_identifiers:
            await update.message.reply_text(
                "Please provide at least one member identifier after the group name."
            )
            return

        if not group:
            # Fallback: explicit quoted name support from /addmember "My Group" user1 user2
            quoted_name = tokens[0]
            direct_group = next((g for g in owned_groups if g[1].lower() == quoted_name.lower()), None)
            if direct_group:
                group = direct_group
                member_identifiers = tokens[1:]

        if group and not member_identifiers:
            await update.message.reply_text(
                "❌ Could not match a group name from your command.\n"
                "Tip: use quotes for clarity, e.g. `/addmember \"Trip to Rome\" alice-01`\n"
                "Use /mygroups to see your groups.",
                parse_mode='Markdown'
            )
            return

        group_id = group[0]
        members = get_members_of_group(session, group_id)
        member_ids = {m[1] for m in members}
        added = []
        skipped = []

        for identifier in member_identifiers:
            member = get_user_by_identifier(session, identifier)
            if not member:
                skipped.append(f"{identifier} (user not found)")
                continue

            member_id = member[0]
            if member_id in member_ids:
                skipped.append(f"{identifier} (already in group)")
                continue

            add_member_to_group(session, group_id=group_id, user_id=member_id)
            member_ids.add(member_id)
            added.append(identifier)

        member_count = len(member_ids)

        lines = [f"✅ Updated *{group[1]}*.", f"👥 Total members: {member_count}"]
        if added:
            lines.append("Added: " + ", ".join(f"`{x}`" for x in added))
        if skipped:
            lines.append("Skipped: " + ", ".join(f"`{x}`" for x in skipped))

        await update.message.reply_text("\n".join(lines), parse_mode='Markdown')
    finally:
        session.close()


async def setid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set or view the caller custom ID for easy group invites."""
    user = update.effective_user
    session = get_session()

    try:
        ensure_user_exists(session, user.id, user.username, user.first_name)

        if not context.args:
            current_user = get_user_by_id(session, user.id)
            current_custom_id = current_user[1]

            if current_custom_id:
                await update.message.reply_text(
                    f"🆔 Your current custom ID is: `{current_custom_id}`\n"
                    f"Use `/setid <new_id>` to change it.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "You have no custom ID yet.\n"
                    "Set one with: `/setid your_custom_id`",
                    parse_mode='Markdown'
                )
            return

        candidate = normalize_custom_id(context.args[0])
        allowed_chars = set("abcdefghijklmnopqrstuvwxyz0123456789_-")

        if len(candidate) < 3 or len(candidate) > 32 or any(c not in allowed_chars for c in candidate):
            await update.message.reply_text(
                "❌ Invalid custom ID. Use 3-32 chars: lowercase letters, numbers, `_`, `-`.",
                parse_mode='Markdown'
            )
            return

        existing = get_user_by_identifier(session, candidate)
        if existing and existing[0] != user.id:
            await update.message.reply_text("❌ That custom ID is already taken. Try another one.")
            return

        set_custom_id(session, user.id, candidate)
        await update.message.reply_text(
            f"✅ Custom ID saved: `{candidate}`\n"
            f"Others can now add you to groups using this ID.",
            parse_mode='Markdown'
        )
    finally:
        session.close()


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
                f"✅ *Expense Added!*\n\n"
                f"📁 Group: {group_name}\n"
                f"💰 Total: €{amount}\n"
                f"📝 Description: {description}\n"
                f"👥 Split {len(member_ids)} ways: €{split_amount:.2f} each\n\n"
                "Use /addexpense to add another, or /balance to review balances.",
                parse_mode='Markdown'
            )
            
            # Clear the stored group
            context.user_data.pop('expense_group_id', None)
            
        finally:
            session.close()
            
    except ValueError as e:
        await update.message.reply_text(f"❌ Error: Invalid amount. Please use a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all inline button callbacks"""
    query = update.callback_query
    await query.answer()

    if query.data == "check_balance":
        # Show balance
        user_id = query.from_user.id
        session = get_session()
        
        try:
            balances = get_balance_with_names(session, user_id)
            
            if not balances:
                keyboard = [[InlineKeyboardButton("➕ Add First Expense", callback_data="add_expense_quick")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(
                    "💰 *Your Balance*\n\n"
                    "No expenses yet!\n"
                    "Add your first expense to get started.",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return
            
            message = "💰 *Your Balance*\n\n"
            
            for name, amount in balances:
                if amount > 0:
                    message += f"✅ *{name}* owes you €{amount:.2f}\n"
                else:
                    message += f"❌ You owe *{name}* €{abs(amount):.2f}\n"
            
            keyboard = [[InlineKeyboardButton("➕ Add Expense", callback_data="add_expense_quick")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        finally:
            session.close()
            
    elif query.data == "view_groups":
        # Show groups
        user_id = query.from_user.id
        session = get_session()
        
        try:
            groups = get_groups_for_user(session, user_id)
            
            if not groups:
                keyboard = [[InlineKeyboardButton("➕ Create Group", callback_data="create_new_group")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(
                    "📋 *Your Groups*\n\n"
                    "You're not part of any groups yet.\n"
                    "Create one to get started!",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return
            
            message = "📋 *Your Groups*\n\n"
            
            for i, group in enumerate(groups, 1):
                group_id = group[0]
                group_name = group[1]
                member_count = get_member_count(session, group_id)
                
                if member_count == 2:
                    emoji = "👥"
                elif member_count <= 5:
                    emoji = "👨‍👩‍👦"
                else:
                    emoji = "👨‍👩‍👧‍👦"
                
                message += f"{i}. {emoji} *{group_name}*\n"
                message += f"   └ {member_count} members\n\n"
            
            keyboard = [
                [InlineKeyboardButton("➕ Create New", callback_data="create_new_group")],
                [InlineKeyboardButton("💰 Add Expense", callback_data="add_expense_quick")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        finally:
            session.close()

    else:
        await query.message.reply_text(
            "⚠️ That button action is not available right now. Please try /start again."
        )
