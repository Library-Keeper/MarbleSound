from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from datetime import datetime
from hashing import Hasher
from uuid import uuid4
import models
from enum import Enum
from fastapi import UploadFile, HTTPException
from fastapi.responses import FileResponse
from typing import List, Union
class SearchBy(str, Enum):
    id = "ID"
    username = "Username"

def create_user(username: str, password: str, db: Session):
    db_user = models.User(
        username=username,
        date_of_reg=datetime.now()
    )

    db.add(db_user)
    db.flush()
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
        raise HTTPException(404)

def get_users(db: Session, username: str):
    return db.query(models.User).filter(models.User.username.ilike(f"%{username}%"))

def check_user_session(db: Session, id:int, session: str):
    user_data = get_user_hash(db, session, id)
    return Hasher.verify_hash(session, user_data.hashed_session) if user_data.hashed_session is not None else False

def user_logout(db: Session, id:str, session:str):
    user_data = get_user_hash(db, session, id)
    
    user_data.hashed_session = None
    db.commit()
    db.refresh(user_data)
    return "logout"

def user_login(db: Session, username:str, password: str):
    user = get_user(db, SearchBy.username, username)
    if not user:
        raise HTTPException(404)
    user_data = db.query(models.UserHashedData).filter(models.UserHashedData.user_id == user.id).first()
    if not Hasher.verify_hash(password, user_data.hashed_password):
        raise HTTPException(403)
    
    session = str(uuid4())
    user_data.hashed_session = str(Hasher.get_hash(session))
    db.commit()
    db.refresh(user_data)
    return {"session": session}

def get_user_hash(db: Session, session: str, id: int):
    user_data = db.query(models.UserHashedData).filter(models.UserHashedData.user_id == id).first()
    if not user_data or not Hasher.verify_hash(session, user_data.hashed_session):
        raise HTTPException(403)
    return user_data

def update_user_data(db: Session, id: int, username: str = None, description: str = None):
    user = get_user(db, id=id)
    if not user:
        raise HTTPException(404)
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
    filepath = f"./uploads/temp/{uuid4()}.tmp"
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
    
    if path[1] != "audio" and not filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.wav', '.mp3', '.aiff')):
        raise HTTPException(404)

    with open(filepath, "wb") as f:
        f.write(file.file.read())
    return filepath

def get_file(filepath: str) -> FileResponse:
    return FileResponse(path = filepath, filename=filepath.split("/")[-1],media_type='multipart/form-data')

def update_user_avatar(db: Session, id: int, avatar: UploadFile):
    user = get_user(db, id=id)
    file = save_file("./uploads/avatar", avatar)
    user.avatar = file
    db.commit()
    db.refresh(user)
    return get_user(db, id=id)

def get_user_avatar(db: Session, id: int) -> FileResponse:
    return get_file(get_user(db, id=id).avatar)

def get_genre(db: Session, id: int = None, name: str = None):
    db_genre = db.query(models.Genre).all()
    if id is not None:
        db_genre = db.query(models.Genre).filter(models.Genre.id == id).first()
    if name is not None:
        db_genre = db.query(models.Genre).filter(models.Genre.name.ilike(f"%{name}%")).first()
    return db_genre

def create_audio(db: Session, user_id: int, file: UploadFile, cover: UploadFile, title: str, 
                 is_loop: bool, key: str, bpm: int, genres: List[str], instrument: str):
    db_user = get_user(db, SearchBy.id, id=user_id)
    audio_file = save_file("./uploads/audio/file", file)
    audio_cover = save_file("./uploads/audio/cover", cover) if cover is not None else None  

    db_audio = models.Audio(
        title=title, file=audio_file, cover=audio_cover, key=key,
        instrument=instrument, bpm=bpm,
        is_loop=is_loop, author_id=db_user.id
    )
    db.add(db_audio)
    db.flush()
    genres = genres[0].split(",")
    if genres:
        for genre_name in genres:
            db_genre = get_genre(db, name=genre_name)
            if not db_genre:
                raise HTTPException(404, detail=genres) 
            db.add(models.AudioGenre(audio_id=db_audio.id, genre_id=db_genre.id))

    db.commit()
    return {"id": db_audio.id}

def get_audio(db: Session, id: int = None):
    audio = db.query(models.Audio).options(joinedload(models.Audio.genres)).filter(models.Audio.id == id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    return audio

def search_audio(db: Session, title: str = None, bpm: int = None, 
                 genre: List[str] = None, instrument: str = None, loop: bool = None):
    if all(param is None for param in [title, bpm, genre, instrument, loop]):
        raise HTTPException(400)

    filters = []
    if title is not None:
        filters.append(models.Audio.title.ilike(f"%{title}%"))
    if bpm is not None:
        filters.append(models.Audio.bpm == bpm)

    if genre:
        genre_conditions = []
        for g in genre:
            g_clean = g.strip().lower()
            genre_conditions.append(
                func.find_in_set(g_clean, models.Audio.genre) > 0
            )
        filters.append(or_(*genre_conditions))

    if instrument is not None:
        filters.append(models.Audio.instrument == instrument)
    if loop is not None:
        filters.append(models.Audio.loop.is_(loop))

    query = db.query(models.Audio).filter(or_(*filters))
    results = query.all()
    return results
