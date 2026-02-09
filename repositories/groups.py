from sqlalchemy.orm import Session
from sqlalchemy import select, insert, update, delete
from db.schema import users, groups, group_members, expenses, expense_participants

def create_group(session: Session, name: str, created_by: int):
    stmt = insert(groups).values(name=name, created_by=created_by)
    result = session.execute(stmt)
    session.commit()
    group_id = result.inserted_primary_key[0]
    return get_group_by_id(session, group_id)

def get_group_by_id(session: Session, group_id: int):
    stmt = select(groups).where(groups.c.id == group_id)
    return session.execute(stmt).first()

def get_all_groups(session: Session):
    stmt = select(groups)
    return session.execute(stmt).fetchall()

def delete_group(session: Session, group_id: int):
    stmt = delete(groups).where(groups.c.id == group_id)
    session.execute(stmt)
    session.commit()

def add_member_to_group(session: Session, group_id: int, user_id: int):
    stmt = insert(group_members).values(group_id=group_id, user_id=user_id)
    session.execute(stmt)
    session.commit()

def remove_member_from_group(session: Session, group_id: int, user_id: int):
    stmt = delete(group_members).where(
        (group_members.c.group_id == group_id) &
        (group_members.c.user_id == user_id)
    )
    session.execute(stmt)
    session.commit()

def get_members_of_group(session: Session, group_id: int):
    stmt = select(group_members).where(group_members.c.group_id == group_id)
    return session.execute(stmt).fetchall()
