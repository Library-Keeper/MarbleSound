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
from pathlib import Path
class SearchBy(str, Enum):
    id = "ID"
    username = "Username"

EXTENSION_GROUPS = {
    "audio": {
        "file": {".wav", ".mp3", ".aiff"},
        "cover": {".png", ".jpg", ".jpeg", ".webp"}
    },
    "avatar": {".png", ".jpg", ".jpeg", ".webp"},
    "playlist": {".png", ".jpg", ".jpeg", ".webp"}
}

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

def save_file(path: str, file: UploadFile) -> str:
    parts = path.strip("./").split("/")
    if len(parts) < 3:
        raise HTTPException(400, "Invalid path format")

    category, subcategory = parts[1], parts[2]
    
    try:
        if category == "audio":
            base_dir = Path(f"./uploads/audio/{subcategory}")
            allowed_extensions = EXTENSION_GROUPS["audio"][subcategory]
        else:
            base_dir = Path(f"./uploads/{category}")
            if category == "playlist":
                base_dir /= "cover"
            allowed_extensions = EXTENSION_GROUPS[category]
    except KeyError:
        raise HTTPException(400, "Invalid file category")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(400, "Unsupported file type")

    base_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{uuid4().hex}{file_ext}"
    filepath = base_dir / filename

    try:
        with filepath.open("wb") as buffer:
            buffer.write(file.file.read())
    except Exception as e:
        raise HTTPException(500, f"Failed to save file: {str(e)}")

    return str(filepath.resolve())

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


def create_playlist(db: Session, user_id: int, name: str, cover: UploadFile = None):
    db_user = get_user(db, SearchBy.id, id=user_id)
    
    playlist = models.Playlist(
        name=name,
        author_id=db_user.id,
        cover=save_file("./uploads/playlist/cover", cover) if cover else None
    )
    
    db.add(playlist)
    db.commit()
    return {"id": playlist.id}

def add_audio_to_playlist(db: Session, playlist_id: int, audio_id: int, user_id: int):
    playlist = db.query(models.Playlist).filter(
        models.Playlist.id == playlist_id,
        models.Playlist.author_id == user_id
    ).first()
    
    if not playlist:
        raise HTTPException(404, "Playlist not found")
    
    audio = get_audio(db, audio_id)
    if not audio:
        raise HTTPException(404, "Audio not found")
    
    max_order = db.query(func.max(models.PlaylistAudio.order)).filter(
        models.PlaylistAudio.playlist_id == playlist_id
    ).scalar() or 0
    
    playlist_audio = models.PlaylistAudio(
        playlist_id=playlist_id,
        audio_id=audio_id,
        order=max_order + 1
    )
    
    db.add(playlist_audio)
    db.commit()
    return {"status": "added"}

def get_playlist(db: Session, playlist_id: int):
    return db.query(models.Playlist).options(
        joinedload(models.Playlist.audios)
    ).filter(models.Playlist.id == playlist_id).first()
