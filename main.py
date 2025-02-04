from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
from typing import Annotated, List
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
import crud

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db = Annotated[Session, Depends(get_db)]

@app.post("/user/create/", status_code=201)
def create_user(db: db, username: str, password: str):
    user = crud.get_user(db=db, search_by=crud.SearchBy.username, username=username)
    if user:
        raise HTTPException(400, detail="User already registered")
    return crud.create_user(username=username, password=password, db=db)

@app.post("/user/logout/", status_code=200)
def user_logout(db: db, id: int, session: str):
    if not crud.check_user_session(db, id, session):
        raise HTTPException(403)
    return crud.user_logout(db=db, id=id, session=session)

@app.post("/user/login/", status_code=201)
def user_login(db: db, username: str, password: str):
    return crud.user_login(db=db, username=username, password=password)

@app.get("/user/", status_code=200)
def get_user(db: db, search_by: crud.SearchBy, username: str = None, id: int = None):
    """
    Get one user by id or username
    """
    return crud.get_user(db=db, search_by=search_by, username=username, id=id)

@app.get("/users/", status_code=200)
def get_users(db: db, username: str = None):
    """
    Get multiple users with similar username
    """
    return crud.get_users(db=db, username=username)

@app.put("/user/update/", status_code=202)
def update_user_data(db: db, id: int, session: str, username: str = None, description: str = None):
    if not crud.check_user_session(db, id, session):
        raise HTTPException(403)
    return crud.update_user_data(db, id, username, description)

@app.put("/user/update/avatar/", status_code=202)
def update_user_avatar(db: db, id: int, session: str, avatar: UploadFile):
    if not crud.check_user_session(db, id, session):
        raise HTTPException(403)
    return crud.update_user_avatar(db, id, avatar)

@app.get("/user/avatar/", status_code=200)
def get_user_avatar(db: db, id: int):
    return crud.get_user_avatar(db, id)

@app.post("/audio/create/", status_code=201)
def create_audio(db: db, id: int, session: str, file: UploadFile, title: str, instrument: str, 
                 is_loop: bool, key: str= None, bpm: int = None, genre: List[str] = None, cover: UploadFile = None):
    if not crud.check_user_session(db, id, session):
        raise HTTPException(403)
    return crud.create_audio(db, id, file, cover, title, is_loop, key, bpm, genre, instrument)

@app.get("/audio/", status_code=200)
def get_audio(db: db, id: int = None):
    return crud.get_audio(db, id)

@app.post("/audios/", status_code=200)
def search_audio(db: db, title: str = None, bpm: int = None, 
                 genre: List[str] = None, instrument: str = None, loop: bool = None):
    return crud.search_audio(db, title, bpm, genre, instrument, loop)