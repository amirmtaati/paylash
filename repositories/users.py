from sqlalchemy.orm import Session
from sqlalchemy import select, insert, update, delete
from db.schema import users, groups, group_members, expenses, expense_participants


def normalize_custom_id(custom_id: str) -> str:
    """Normalize custom IDs so lookups are case-insensitive and consistent."""
    return custom_id.strip().lower().lstrip("@")

def create_user(session: Session, user_id: int, username: str = None, first_name: str = None):
    """Create user with explicit Telegram user_id"""
    stmt = insert(users).values(id=user_id, username=username, first_name=first_name)
    result = session.execute(stmt)
    session.commit()
    return get_user_by_id(session, user_id)

def get_user_by_id(session: Session, user_id: int):
    stmt = select(users).where(users.c.id == user_id)
    result = session.execute(stmt).first()
    return result


def get_user_by_custom_id(session: Session, custom_id: str):
    normalized_custom_id = normalize_custom_id(custom_id)
    stmt = select(users).where(users.c.custom_id == normalized_custom_id)
    result = session.execute(stmt).first()
    return result


def get_user_by_identifier(session: Session, identifier: str):
    """
    Resolve a user by either Telegram numeric ID or custom ID.
    """
    normalized_identifier = identifier.strip()

    if normalized_identifier.isdigit():
        return get_user_by_id(session, int(normalized_identifier))

    return get_user_by_custom_id(session, normalized_identifier)


def set_custom_id(session: Session, user_id: int, custom_id: str):
    normalized_custom_id = normalize_custom_id(custom_id)

    stmt = update(users).where(users.c.id == user_id).values(custom_id=normalized_custom_id)
    session.execute(stmt)
    session.commit()
    return get_user_by_id(session, user_id)

def get_all_users(session: Session):
    stmt = select(users)
    return session.execute(stmt).fetchall()

def delete_user(session: Session, user_id: int):
    stmt = delete(users).where(users.c.id == user_id)
    session.execute(stmt)
    session.commit()
