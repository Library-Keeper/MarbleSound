from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime
from hashing import Hasher
from uuid import uuid4
import models
from enum import Enum

class SearchBy(str, Enum):
    id = "ID"
    username = "Username"

class Error(dict, Enum):
    LostAttribute = {"error": "lost attribute"}

def create_user(username: str, password: str, db: Session):
    db_user = models.User(
        username=username,
        date_of_reg=datetime.now()
    )

    db.add(db_user)
    db.commit()
    db_user = db.query(models.User).filter(models.User.username == username).first()
    session = str(uuid4())
    db_user_password = models.UserHashedData(
        user_id=db_user.id,
        hashed_password=Hasher.get_hash(password),
        hashed_session=Hasher.get_hash(session)
    )
    db.add(db_user_password)
    db.commit()
    return {"id": str(db_user.id), "session": str(session)}

def get_user(db: Session, search_by: SearchBy, username: str = None, id: int = None):
    if search_by == SearchBy.id and id is not None:
        user = db.query(models.User).filter(models.User.id == id).first()
    elif search_by == SearchBy.username and username is not None:
        user = db.query(models.User).filter(models.User.username == username).first()
    else:
        user = Error.LostAttribute
    return user

def get_users(db: Session, username: str):
    return db.query(models.User).filter(models.User.username.regexp_match(f"(?i).*{username}.*", flags='i')).limit(30).all()


