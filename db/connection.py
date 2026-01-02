from sqlalchemy import create_engine, Engine
from utils import get_logger
from sqlalchemy.orm import sessionmaker

import os

logger = get_logger("db.connection")

db = None

def db_get():
    global db

    if db is None:
        return db_connect()

    return db


def db_connect():
    global db

    if db is None:
        db_url = db_get_url()
        db = create_engine(db_url, echo=True)
        logger.info("database created: %s", db_url)

    return db


def db_disconnect():
    global db

    if db is not None:
        db.dispose()
        db = None

def db_get_url():
    return os.getenv('DB_URL', 'sqlite:///./paylash.db')


def get_session():
    engine = db_get()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return SessionLocal()
