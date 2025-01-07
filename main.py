from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Annotated, Optional
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from datetime import datetime
from uuid import uuid4
from hashing import Hasher
app = FastAPI()
models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db = Annotated[Session, Depends(get_db)]

class UserBase(BaseModel):
    username: str
    password: str

@app.post("/users/create/", status_code=status.HTTP_201_CREATED)
def create_user(user: UserBase, db: db):
    db_user = models.User(
        username=user.username,
        date_of_reg=datetime.now()
    )

    db.add(db_user)
    db.commit()
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    session = str(uuid4())
    db_user_password = models.UserHashedData(
        user_id=db_user.id,
        hashed_password=Hasher.get_hash(user.password),
        hashed_session=Hasher.get_hash(session)
    )
    db.add(db_user_password)
    db.commit()
    return {"id": str(db_user.id), "session": str(session)}
