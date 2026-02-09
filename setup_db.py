#!/usr/bin/env python3
"""
Initialize the PayLash database
"""
from db.schema import metadata
from db.connection import db_get

def main():
    print("🔧 Initializing PayLash database...")
    
    # Create engine and tables
    engine = db_get()
    metadata.create_all(engine)
    
    print("✅ Database tables created successfully!")
    print("\nTables created:")
    print("  - users")
    print("  - groups")
    print("  - group_members")
    print("  - expenses")
    print("  - expense_participants")
    print("\n🚀 You can now run the bot with: python -m bot.main")

if __name__ == "__main__":
    main()
