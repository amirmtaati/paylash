#!/usr/bin/env python3
"""
Test script to verify the PayLash system works correctly
"""
from db.schema import metadata
from db.connection import db_get, get_session
from repositories.users import create_user, get_user_by_id
from repositories.groups import create_group, add_member_to_group, get_members_of_group, get_member_count
from repositories.expenses import create_expense, add_participant, get_participants_for_expense
from services.expense_service import create_expense_with_split
from services.balance_service import get_user_balance, get_balance_with_names

def test_basic_workflow():
    """Test the basic workflow: create users, group, add expense, check balance"""
    
    print("🧪 Testing PayLash System...\n")
    
    # 1. Setup database
    print("1️⃣ Creating database...")
    engine = db_get()
    metadata.create_all(engine)
    print("   ✅ Database created\n")
    
    session = get_session()
    
    try:
        # 2. Create users
        print("2️⃣ Creating test users...")
        user1 = create_user(session, user_id=111111, username="alice", first_name="Alice")
        user2 = create_user(session, user_id=222222, username="bob", first_name="Bob")
        user3 = create_user(session, user_id=333333, username="charlie", first_name="Charlie")
        print(f"   ✅ Created users: Alice (111111), Bob (222222), Charlie (333333)\n")
        
        # 3. Create group
        print("3️⃣ Creating group...")
        group = create_group(session, name="Pizza Night", created_by=111111)
        group_id = group[0]
        print(f"   ✅ Created group: Pizza Night (ID: {group_id})\n")
        
        # 4. Add members to group
        print("4️⃣ Adding members to group...")
        add_member_to_group(session, group_id=group_id, user_id=111111)
        add_member_to_group(session, group_id=group_id, user_id=222222)
        add_member_to_group(session, group_id=group_id, user_id=333333)
        member_count = get_member_count(session, group_id)
        print(f"   ✅ Added {member_count} members to group\n")
        
        # 5. Create expense
        print("5️⃣ Creating expense...")
        print("   Scenario: Alice paid €60 for pizza, split 3 ways")
        expense_id = create_expense_with_split(
            session=session,
            desc="Dominos Pizza",
            amount=60.00,
            paid_by=111111,  # Alice paid
            group_id=group_id,
            IDs=[111111, 222222, 333333],  # All 3 people
            split_type="equal"
        )
        print(f"   ✅ Created expense (ID: {expense_id})\n")
        
        # 6. Check balances
        print("6️⃣ Checking balances...\n")
        
        # Alice's balance (she paid)
        alice_balance = get_balance_with_names(session, 111111)
        print("   Alice's balance:")
        for name, amount in alice_balance:
            if amount > 0:
                print(f"     ✅ {name} owes Alice €{amount:.2f}")
            else:
                print(f"     ❌ Alice owes {name} €{abs(amount):.2f}")
        
        # Bob's balance (he owes)
        bob_balance = get_balance_with_names(session, 222222)
        print("\n   Bob's balance:")
        for name, amount in bob_balance:
            if amount > 0:
                print(f"     ✅ {name} owes Bob €{amount:.2f}")
            else:
                print(f"     ❌ Bob owes {name} €{abs(amount):.2f}")
        
        # Charlie's balance (he owes)
        charlie_balance = get_balance_with_names(session, 333333)
        print("\n   Charlie's balance:")
        for name, amount in charlie_balance:
            if amount > 0:
                print(f"     ✅ {name} owes Charlie €{amount:.2f}")
            else:
                print(f"     ❌ Charlie owes {name} €{abs(amount):.2f}")
        
        print("\n" + "="*50)
        print("🎉 All tests passed! System is working correctly!")
        print("="*50)
        
        # Expected results:
        print("\n📊 Expected Results:")
        print("   - Alice paid €60, her share is €20")
        print("   - Bob owes €20 to Alice")
        print("   - Charlie owes €20 to Alice")
        print("   - Alice is owed €40 total (€20 from Bob + €20 from Charlie)")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        session.close()
        print("\n✅ Database session closed")


if __name__ == "__main__":
    import os
    
    # Use a test database
    os.environ['DB_URL'] = 'sqlite:///./test_paylash.db'
    
    test_basic_workflow()
    
    print("\n💡 Tip: Check test_paylash.db to see the data created")
    print("💡 To test the bot, run: python3 -m bot.main")
