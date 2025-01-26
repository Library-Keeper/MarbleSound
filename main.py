from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
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
def create_user(username: str, password: str, db: db):
    return crud.create_user(username=username, password=password, db=db)

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