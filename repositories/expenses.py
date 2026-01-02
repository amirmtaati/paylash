from sqlalchemy.orm import Session
from sqlalchemy import select, insert, update, delete
from db.schema import users, groups, group_members, expenses, expense_participants

def create_expense(session: Session, description: str, amount: float, paid_by: int,
                   group_id: int = None, currency: str = "USD"):
    stmt = insert(expenses).values(
        description=description,
        amount=amount,
        paid_by=paid_by,
        group_id=group_id,
        currency=currency
    )
    result = session.execute(stmt)
    session.commit()
    expense_id = result.inserted_primary_key[0]
    return get_expense_by_id(session, expense_id)


def get_expense_by_id(session: Session, expense_id: int):
    stmt = select(expenses).where(expenses.c.id == expense_id)
    return session.execute(stmt).first()


def get_expenses_for_group(session: Session, group_id: int):
    stmt = select(expenses).where(expenses.c.group_id == group_id)
    return session.execute(stmt).fetchall()


def delete_expense(session: Session, expense_id: int):
    stmt = delete(expenses).where(expenses.c.id == expense_id)
    session.execute(stmt)
    session.commit()


# -----------------------
# Expense Participants
# -----------------------

def add_participant(session: Session, expense_id: int, user_id: int, share_type: str,
                    amount_owed: float, share_value: float = None):
    stmt = insert(expense_participants).values(
        expense_id=expense_id,
        user_id=user_id,
        share_type=share_type,
        amount_owed=amount_owed,
        share_value=share_value
    )
    session.execute(stmt)
    session.commit()


def get_participants_for_expense(session: Session, expense_id: int):
    stmt = select(expense_participants).where(expense_participants.c.expense_id == expense_id)
    return session.execute(stmt).fetchall()


def delete_participant(session: Session, participant_id: int):
    stmt = delete(expense_participants).where(expense_participants.c.id == participant_id)
    session.execute(stmt)
    session.commit()
