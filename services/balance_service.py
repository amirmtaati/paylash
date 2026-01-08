from sqlalchemy import select, and_
from db.schema import expenses, expense_participants, users
from decimal import Decimal

def get_user_balance(session, user_id, group_id=None):
    """
    Calculate what user owes or is owed based on expense_participants.
    Returns dict: {other_user_id: amount}
        - Positive amount = they owe you
        - Negative amount = you owe them
    """
    balances = {}
    
    # Query to get all expenses where this user is a participant
    query = select(
        expenses.c.id.label('expense_id'),
        expenses.c.paid_by,
        expenses.c.amount.label('total_amount'),
        expense_participants.c.amount_owed
    ).select_from(
        expense_participants
    ).join(
        expenses, expense_participants.c.expense_id == expenses.c.id
    ).where(
        expense_participants.c.user_id == user_id
    )
    
    # Optional: filter by group
    if group_id is not None:
        query = query.where(expenses.c.group_id == group_id)
    
    my_expenses = session.execute(query).fetchall()
    
    # Process each expense
    for expense in my_expenses:
        expense_id = expense.expense_id
        paid_by = expense.paid_by
        my_share = Decimal(str(expense.amount_owed))
        
        if paid_by == user_id:
            # I paid this expense - find who else participated
            other_participants_query = select(
                expense_participants.c.user_id,
                expense_participants.c.amount_owed
            ).where(
                and_(
                    expense_participants.c.expense_id == expense_id,
                    expense_participants.c.user_id != user_id
                )
            )
            
            other_participants = session.execute(other_participants_query).fetchall()
            
            # Each other participant owes me their share
            for participant in other_participants:
                other_id = participant.user_id
                their_share = Decimal(str(participant.amount_owed))
                
                if other_id not in balances:
                    balances[other_id] = Decimal('0')
                
                balances[other_id] += their_share  # They owe me
        
        else:
            # Someone else paid - I owe them my share
            if paid_by not in balances:
                balances[paid_by] = Decimal('0')
            
            balances[paid_by] -= my_share  # I owe them
    
    # Remove zero balances
    balances = {k: v for k, v in balances.items() if v != 0}
    
    return balances


def get_balance_with_names(session, user_id, group_id=None):
    """
    Same as get_user_balance but returns dict with user names instead of IDs.
    Returns: [(name, amount), ...]
    """
    balances = get_user_balance(session, user_id, group_id)
    
    result = []
    for other_user_id, amount in balances.items():
        # Get other user's name
        user_query = select(users).where(users.c.id == other_user_id)
        user_result = session.execute(user_query).first()
        
        if user_result:
            name = user_result.first_name or user_result.username or f"User {other_user_id}"
        else:
            name = f"User {other_user_id}"
        
        result.append((name, amount))
    
    return result
