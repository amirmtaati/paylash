from db.schema import metadata
from db.connection import db_get, get_session
from repositories import (
    create_user, get_all_users,
    create_group, get_all_groups,
    add_member_to_group, get_members_of_group,
    create_expense, add_participant, get_participants_for_expense
)

def main():
    # 1. Create engine and tables
    engine = db_get()
    metadata.create_all(engine)
    print("Tables created successfully!")

    # 2. Create a session manually
    session = get_session()
    try:
        # ---- Users ----
        user1 = create_user(session, username="amir", first_name="Amir")
        user2 = create_user(session, username="ali", first_name="Ali")
        print("Users created:")
        print(get_all_users(session))

        # ---- Groups ----
        group = create_group(session, name="Trip", created_by=user1[0])
        print("Groups created:")
        print(get_all_groups(session))

        # ---- Group Members ----
        add_member_to_group(session, group_id=group[0], user_id=user1[0])
        add_member_to_group(session, group_id=group[0], user_id=user2[0])
        print("Members of group:")
        print(get_members_of_group(session, group_id=group[0]))

        # ---- Expenses ----
        expense = create_expense(
            session,
            description="Hotel",
            amount=200.00,
            paid_by=user1[0],
            group_id=group[0]
        )
        print(f"Expense created: {expense}")

        # ---- Expense Participants ----
        add_participant(session, expense_id=expense[0], user_id=user1[0], share_type="equal", amount_owed=100.00)
        add_participant(session, expense_id=expense[0], user_id=user2[0], share_type="equal", amount_owed=100.00)
        print("Participants for expense:")
        print(get_participants_for_expense(session, expense_id=expense[0]))

    finally:
        # 3. Close session
        session.close()


if __name__ == "__main__":
    main()
