from fastapi import FastAPI, HTTPException, Depends, status
from typing import Annotated
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

@app.post("/user/create/", status_code=status.HTTP_201_CREATED)
def create_user(db: db, username: str, password: str):
    user = crud.get_user(db=db, search_by=crud.SearchBy.username, username=username)
    if user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already registered")
    return crud.create_user(username=username, password=password, db=db)

@app.post("/user/logout", status_code=status.HTTP_200_OK)
def user_logout(db: db, id: str, session: str):
    return crud.user_logout(db=db, id=id, session=session)

@app.post("/user/login", status_code=status.HTTP_202_ACCEPTED)
def user_login(db: db, username: str, password: str):
    return crud.user_login(db=db, username=username, password=password)

@app.get("/user/", status_code=status.HTTP_202_ACCEPTED)
def get_user(db: db, search_by: crud.SearchBy, username: str = None, id: int = None):
    """
    Get one user by id or username
    """
    return crud.get_user(db=db, search_by=search_by, username=username, id=id)

@app.get("/users/", status_code=status.HTTP_202_ACCEPTED)
def get_users(db: db, username: str = None):
    """
    Get multiple users with similar username
    """
    return crud.get_users(db=db, username=username)

@app.put("/user/update/", status_code=status.HTTP_202_ACCEPTED)
def update_user_data(db: db, id: int, session: str, username: str = None, description: str = None):
    return crud.update_user_data(db, id, session, username, description)