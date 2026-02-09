from repositories.expenses import create_expense, add_participant

def calculate_equal_split(amount, num):
    return amount / num

def validate_expense_data(amount, IDs, split_type, custom_amounts):
    pass

def create_expense_with_split(session, desc, amount, paid_by, group_id, IDs, split_type="equal", custom_amounts=None):
    expense = create_expense(
        session=session,
        description=desc,
        amount=float(amount),
        paid_by=paid_by,
        group_id=group_id
    )

    expense_id = expense[0]

    if split_type == "equal":
        split_amount = calculate_equal_split(amount, len(IDs))

        for ID in IDs:
            add_participant(
                session,
                expense_id=expense_id,
                user_id=ID,
                share_type="equal",
                amount_owed=float(split_amount)
            )

    elif split_type == "custom":
        for ID in IDs:
            custom_amount = custom_amounts[ID]
            add_participant(
               session,
               expense_id=expense_id,
               user_id=ID,
               share_type="custom",
               amount_owed=float(custom_amount),
               share_value=float(custom_amount)
            )

    return expense_id
