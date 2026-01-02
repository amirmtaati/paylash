from sqlalchemy.orm import Session
from sqlalchemy import select, insert, update, delete
from db.schema import users, groups, group_members, expenses, expense_participants

def create_user(session: Session, username: str = None, first_name: str = None):
    stmt = insert(users).values(username=username, first_name=first_name)
    result = session.execute(stmt)
    session.commit()
    user_id = result.inserted_primary_key[0]
    return get_user_by_id(session, user_id)

def get_user_by_id(session: Session, user_id: int):
    stmt = select(users).where(users.c.id == user_id)
    result = session.execute(stmt).first()
    return result

def get_all_users(session: Session):
    stmt = select(users)
    return session.execute(stmt).fetchall()

def delete_user(session: Session, user_id: int):
    stmt = delete(users).where(users.c.id == user_id)
    session.execute(stmt)
    session.commit()
