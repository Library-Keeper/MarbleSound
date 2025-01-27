from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import datetime
from hashing import Hasher
from uuid import uuid4
import models
from enum import Enum
from fastapi import UploadFile
from fastapi.responses import FileResponse
class SearchBy(str, Enum):
    id = "ID"
    username = "Username"

class Error(dict, Enum):
    SearchBy = {"error": "search by or attribute"}
    NotExist = {"error": "not exists"}
    WrongData = {"error": "wrong data"}

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
    return {"id": db_user.id, "session": str(session)}

def get_user(db: Session, search_by: SearchBy = SearchBy.id, username: str = None, id: int = None):
    if search_by == SearchBy.id and id is not None:
        return db.query(models.User).filter(models.User.id == id).first()
    elif search_by == SearchBy.username and username is not None:
        return db.query(models.User).filter(models.User.username == username).first()
    else:
        return Error.SearchBy

def get_users(db: Session, username: str):
    return db.query(models.User).filter(models.User.username.regexp_match(f"(?i).*{username}.*", flags='i')).limit(30).all()

def check_user_session(db: Session, id:int, session: str):
    user_data = get_user_hash(db, session, get_user(db, SearchBy.id, id=id))
    return Hasher.verify_hash(session, user_data.hashed_session) if user_data.hashed_session is not None else False

def user_logout(db: Session, id:str, session:str):
    user_data = get_user_hash(db, session, get_user(db, id=id))
    
    user_data.hashed_session = None
    db.commit()
    db.refresh(user_data)
    return "logout"

def user_login(db: Session, username:str, password: str):
    user = get_user(db, SearchBy.username, username)
    if not user:
        return Error.NotExist
    user_data = db.query(models.UserHashedData).filter(models.UserHashedData.user_id == user.id).first()
    if not Hasher.verify_hash(password, user_data.hashed_password):
        return Error.WrongData
    
    session = str(uuid4())
    user_data.hashed_session = str(Hasher.get_hash(session))
    db.commit()
    db.refresh(user_data)
    return {"session": session}

def get_user_hash(db: Session, session: str, user: models.User):
    user_data = db.query(models.UserHashedData).filter(models.UserHashedData.user_id == user.id).first()
    if not Hasher.verify_hash(session, user_data.hashed_session):
        return Error.WrongData
    return user_data

def update_user_data(db: Session, id: int, username: str = None, description: str = None):
    user = get_user(db, id=id)
    if not user:
        return Error.NotExist
    if username is not None:
        user.username = username
    if description is not None:
        user.description = description
    
    db.commit()
    db.refresh(user)
    return get_user(db, SearchBy.id, id=id)

def save_file(path: str, file: UploadFile):
    path = path.strip("./").split("/")
    print(path)
    filepath = f"./uploads/temp/{uuid4()}+{uuid4()}"
    match path[1]:
        case "audio":
            match path[2]:
                case "file":
                    filepath = f"./uploads/audio/file/{uuid4()}+{file.filename}"
                case "cover":
                    filepath = f"./uploads/audio/cover/{uuid4()}+{file.filename}"
        case "avatar":
            filepath = f"./uploads/avatar/{uuid4()}+{file.filename}"
        case "playlist":
            filepath = f"./uploads/playlist/cover/{uuid4()}+{file.filename}"

    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return filepath

def get_file(filepath: str) -> FileResponse:
    return FileResponse(path = filepath, filename=filepath.split("/")[-1],media_type='multipart/form-data')

def update_user_avatar(db: Session, id: int, avatar: UploadFile):
    user = get_user(db, id=id)
    user.avatar = save_file("./uploads/avatar", avatar)
    db.commit()
    db.refresh(user)
    return get_user(db, id=id)

def get_user_avatar(db: Session, id: int) -> FileResponse:
    return get_file(get_user(db, id=id).avatar)

