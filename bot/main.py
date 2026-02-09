from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ConversationHandler, CallbackQueryHandler
)
from bot.handlers import (
    start, balance, my_groups,
    create_group_start, receive_group_name, add_group_member,
    add_expense_start, receive_group_selection, handle_expense_details,
    cancel,
    WAITING_FOR_GROUP_NAME, WAITING_FOR_MEMBER_SELECTION, WAITING_FOR_GROUP_SELECTION
)
import os

def main():
    # Get token from environment or use hardcoded (not recommended for production!)
    token = os.getenv("TELEGRAM_BOT_TOKEN", "8529720422:AAEOTNA8dwYf0Z98qyvxUmtYKY3NESvaTSo")
    
    app = Application.builder().token(token).build()
    
    # Simple command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("mygroups", my_groups))
    
    # Conversation handler for creating groups
    create_group_conv = ConversationHandler(
        entry_points=[CommandHandler("creategroup", create_group_start)],
        states={
            WAITING_FOR_GROUP_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group_name)
            ],
            WAITING_FOR_MEMBER_SELECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_group_member)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(create_group_conv)
    
    # Conversation handler for adding expenses
    add_expense_conv = ConversationHandler(
        entry_points=[CommandHandler("addexpense", add_expense_start)],
        states={
            WAITING_FOR_GROUP_SELECTION: [
                CallbackQueryHandler(receive_group_selection)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(add_expense_conv)
    
    # Handler for expense details (when user has selected a group)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_expense_details
    ))
    
    print("🤖 PayLash Bot starting...")
    print("Commands available:")
    print("  /start - Start the bot")
    print("  /creategroup - Create a new group")
    print("  /addexpense - Add an expense")
    print("  /balance - Check your balance")
    print("  /mygroups - View your groups")
    app.run_polling()

if __name__ == "__main__":
    main()
