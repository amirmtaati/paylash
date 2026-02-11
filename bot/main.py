from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ConversationHandler
)
from bot.handlers import (
    start, balance, my_groups,
    create_group_start, receive_group_name, add_group_member,
    add_expense_start, receive_group_selection, handle_expense_details,
    setid,
    addmember,
    cancel,
    WAITING_FOR_GROUP_NAME, WAITING_FOR_MEMBER_SELECTION, WAITING_FOR_GROUP_SELECTION
)
import os
from db.connection import db_get
from db.schema import metadata
from db.migrations import ensure_users_custom_id_column

def main():
    # Get token from environment or use hardcoded (not recommended for production!)
    token = os.getenv("TELEGRAM_BOT_TOKEN", "8529720422:AAEOTNA8dwYf0Z98qyvxUmtYKY3NESvaTSo")
    
    engine = db_get()
    metadata.create_all(engine)
    ensure_users_custom_id_column(engine)

    app = Application.builder().token(token).build()
    
    # Simple command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("mygroups", my_groups))
    app.add_handler(CommandHandler("setid", setid))
    app.add_handler(CommandHandler("addmember", addmember))
    
    # Conversation handler for creating groups
    create_group_conv = ConversationHandler(
        allow_reentry=True,
        entry_points=[
            CommandHandler("creategroup", create_group_start),
            CallbackQueryHandler(create_group_start, pattern="^create_new_group$")
        ],
        states={
            WAITING_FOR_GROUP_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group_name),
                CallbackQueryHandler(handle_button_callback, pattern="^(check_balance|view_groups)$")
            ],
            WAITING_FOR_MEMBER_SELECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_group_member),
                CallbackQueryHandler(add_group_member, pattern="^(done_adding_members|help_find_id|continue_adding)$"),
                CallbackQueryHandler(handle_button_callback, pattern="^(check_balance|view_groups)$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(create_group_conv)
    
    # Conversation handler for adding expenses
    add_expense_conv = ConversationHandler(
        allow_reentry=True,
        entry_points=[
            CommandHandler("addexpense", add_expense_start),
            CallbackQueryHandler(add_expense_start, pattern="^add_expense_quick$")
        ],
        states={
            WAITING_FOR_GROUP_SELECTION: [
                CallbackQueryHandler(receive_group_selection, pattern=r"^group_\d+$")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(add_expense_conv)
    
    # Global callback query handler for non-conversation inline buttons.
    # Keep this scoped so conversation entry-point callbacks are handled by
    # their corresponding ConversationHandler.
    app.add_handler(CallbackQueryHandler(handle_button_callback, pattern="^(check_balance|view_groups)$"))
    
    # Handler for expense details (when user has selected a group)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_expense_details
    ))
    
    print("🤖 PayLash Bot starting...")
    print("⌨️ Command-based workflow enabled (inline buttons removed).")
    print("\nCommands available:")
    print("  /start - Start the bot")
    print("  /creategroup - Create a new group")
    print("  /addexpense - Add an expense")
    print("  /balance - Check your balance")
    print("  /mygroups - View your groups")
    print("  /setid - Set your shareable custom ID")
    print("  /addmember - Add members to your group by name")
    print("\n💡 Tip: Type /start anytime to see available commands.")
    app.run_polling()

if __name__ == "__main__":
    main()
