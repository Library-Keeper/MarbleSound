from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func, exists
from datetime import datetime
from hashing import Hasher
from uuid import uuid4
import models
from enum import Enum
from fastapi import UploadFile, HTTPException
from fastapi.responses import FileResponse
from typing import List, Union
from pathlib import Path
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

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

# =====================
# Function
# =====================

def save_file(path: str, file: UploadFile) -> str:
    parts = path.strip("./").split("/")
    if len(parts) < 3:
        raise HTTPException(400, "Invalid path format")

    category, subcategory = parts[1], parts[2]
    
    try:
        if category == "audio":
            base_dir = Path(f"uploads/audio/{subcategory}")
            allowed_extensions = EXTENSION_GROUPS["audio"][subcategory]
        else:
            base_dir = Path(f"uploads/{category}")
            if category == "playlist":
                base_dir /= "cover"
            allowed_extensions = EXTENSION_GROUPS[category]
    except KeyError:
        raise HTTPException(400, "Invalid file category")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(400, f"Unsupported file type {file_ext} - {file.filename}")

    base_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{uuid4().hex}{file_ext}"
    filepath = base_dir / filename

    try:
        with filepath.open("wb") as buffer:
            buffer.write(file.file.read())
    except Exception as e:
        raise HTTPException(500, f"Failed to save file: {str(e)}")

    return str(filepath).replace("\\", "/")

def get_file(filepath: str) -> FileResponse:
    absolute_path = Path.cwd() / filepath
    if not absolute_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=absolute_path,
        filename=absolute_path.name,
        media_type='multipart/form-data'
    )
# =====================
# User control
# =====================

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
    return {"id": user.id, "session": session}

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

def update_user_avatar(db: Session, id: int, avatar: UploadFile):
    user = get_user(db, id=id)
    file = save_file("./uploads/avatar", avatar)
    user.avatar = file
    db.commit()
    db.refresh(user)
    return get_user(db, id=id)

def get_user_avatar(db: Session, id: int) -> FileResponse:
    return get_file(get_user(db, id=id).avatar)

def delete_user(db: Session, id: int, session: str):
    if not check_user_session(db, id, session):
        raise HTTPException(401)
    db_user = get_user(db, SearchBy.id, id=id)
    db_user_data = get_user_hash(db, session=session, id=id)
    db.delete(db_user_data)
    db.delete(db_user)
    db.commit()
    return 

def get_user_favorites(db: Session, user_id: int):
    return db.query(models.Favorite).filter(
        models.Favorite.user_id == user_id
    ).options(
        joinedload(models.Favorite.audios),
        joinedload(models.Favorite.playlists)
    ).all()

def remove_from_favorites(
    db: Session,
    user_id: int,
    audio_id: int = None,
    playlist_id: int = None
):
    filters = [models.Favorite.user_id == user_id]
    if audio_id:
        filters.append(models.Favorite.audio_id == audio_id)
    if playlist_id:
        filters.append(models.Favorite.playlist_id == playlist_id)
    
    favorite = db.query(models.Favorite).filter(and_(*filters)).first()
    if not favorite:
        raise HTTPException(404, "Favorite not found")
    
    db.delete(favorite)
    db.commit()
    return {"status": "removed from favorites"}

def get_user_audios(db: Session, user_id: int):
    return db.query(models.Audio).filter(
        models.Audio.author_id == user_id
    ).options(
        joinedload(models.Audio.genres),
        joinedload(models.Audio.instrument)
    ).all()

def get_user_playlists(db: Session, user_id: int):
    return db.query(models.Playlist).filter(
        models.Playlist.author_id == user_id
    ).options(
        joinedload(models.Playlist.audios)
    ).all()

# =====================
# Audio control
# =====================

def get_genre(db: Session, id: int = None, name: str = None):
    db_genre = db.query(models.Genre).all()
    if id is not None:
        db_genre = db.query(models.Genre).filter(models.Genre.id == id).first()
    if name is not None:
        db_genre = db.query(models.Genre).filter(models.Genre.name.ilike(f"%{name}%")).first()
    return db_genre

def get_all_keys(db: Session):
    return db.query(models.Key).all()

def get_all_instruments(db: Session):
    return db.query(models.Instrument).all()

def create_audio(db: Session, user_id: int, file: UploadFile, cover: UploadFile, title: str, 
                 is_loop: bool, key: str, bpm: int, genres: List[str], instrument: str):
    db_user = get_user(db, SearchBy.id, id=user_id)
    audio_file = save_file("./uploads/audio/file", file)
    audio_cover = save_file("./uploads/audio/cover", cover) if cover is not None else None  

    db_instrument = db.query(models.Instrument).filter(
        func.lower(models.Instrument.name) == func.lower(instrument)
    ).first()
    if not db_instrument:
        raise HTTPException(404)

    if key:
        db_key = db.query(models.Key).filter(
            func.lower(models.Key.name) == func.lower(key)
        ).first()
        
        if not db_key:
            db_key = models.Key(name=key.strip().upper())
            db.add(db_key)
            db.flush()

    try:
        audio = AudioSegment.from_file(audio_file)
        duration = len(audio) / 1000 
        
    except CouldntDecodeError:
        duration = None
    except Exception as e:
        duration = None


    db_audio = models.Audio(
        title=title,
        file=audio_file,
        cover=audio_cover,
        key_id=db_key.id if db_key else None,
        instrument_id=db_instrument.id, 
        bpm=bpm,
        is_loop=is_loop,
        author_id=db_user.id,
        duration=duration
    )




    db.add(db_audio)
    db.flush()
    if genres:
        for genre_name in genres:
            db_genre = get_genre(db, name=genre_name)
            if not db_genre:
                raise HTTPException(404, detail=genres) 
            db.add(models.AudioGenre(audio_id=db_audio.id, genre_id=db_genre.id))

    db.commit()
    return {"id": db_audio.id}

def update_audio(
    db: Session,
    audio_id: int,
    user_id: int,
    title: str = None,
    key: str = None,
    bpm: int = None,
    genres: List[str] = None,
    instrument: str = None,
    is_loop: bool = None
):
    db_audio = db.query(models.Audio).filter(
        models.Audio.id == audio_id,
        models.Audio.author_id == user_id
    ).first()
    
    if not db_audio:
        raise HTTPException(404, "Audio not found or access denied")
    
    if title: db_audio.title = title
    if bpm: db_audio.bpm = bpm
    if is_loop is not None: db_audio.is_loop = is_loop
    
    if key:
        db_key = db.query(models.Key).filter(
            func.lower(models.Key.name) == func.lower(key.strip())
        ).first()
        if not db_key:
            db_key = models.Key(name=key.strip().upper())
            db.add(db_key)
            db.flush()
        db_audio.key_id = db_key.id
    
    if instrument:
        db_instrument = db.query(models.Instrument).filter(
            func.lower(models.Instrument.name) == func.lower(instrument)
        ).first()
        if not db_instrument:
            raise HTTPException(404, "Instrument not found")
        db_audio.instrument_id = db_instrument.id
    
    if genres is not None:
        db.query(models.AudioGenre).filter(
            models.AudioGenre.audio_id == audio_id
        ).delete()
        for genre_name in genres:
            db_genre = db.query(models.Genre).filter(
                func.lower(models.Genre.name) == func.lower(genre_name.strip())
            ).first()
            if not db_genre:
                raise HTTPException(404, f"Genre '{genre_name}' not found")
            db.add(models.AudioGenre(
                audio_id=audio_id,
                genre_id=db_genre.id
            ))
    
    db.commit()
    return db_audio

def get_audio(db: Session, id: int = None):
    audio = db.query(models.Audio).options(joinedload(models.Audio.genres),joinedload(models.Audio.instrument)).filter(models.Audio.id == id).first()
    if not audio:
        raise HTTPException(status_code=404, detail="Audio not found")
    return audio

def get_audio_file(db: Session, audio_id: int):
    audio = db.query(models.Audio).filter(models.Audio.id == audio_id).first()
    if not audio or not audio.file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    return get_file(audio.file)

def get_audio_file_v2(db: Session, audio_id: int):
    audio = db.query(models.Audio).filter(models.Audio.id == audio_id).first()
    if not audio or not audio.file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    file_path = Path(audio.file)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on server")
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type='application/octet-stream',
        headers={
            'Content-Disposition': f'attachment; filename="{file_path.name}"',
            'Access-Control-Expose-Headers': 'Content-Disposition'
        }
    )

def get_audio_cover(db: Session, audio_id: int):
    audio = db.query(models.Audio).filter(models.Audio.id == audio_id).first()
    if not audio or not audio.cover:
        raise HTTPException(status_code=404, detail="Cover not found")
    return get_file(audio.cover)

def search_audio(
    db: Session,
    title: str = None,
    min_bpm: int = None,
    max_bpm: int = None,
    genres: str = None,
    instruments: str = None,
    keys: str = None,
    loop: bool = None
    ):
    query = db.query(models.Audio).join(models.Audio.instrument)
    filters = []

    if title:
        filters.append(models.Audio.title.ilike(f"%{title}%"))

    bpm_filters = []
    if min_bpm is not None:
        bpm_filters.append(models.Audio.bpm >= min_bpm)
    if max_bpm is not None:
        bpm_filters.append(models.Audio.bpm <= max_bpm)
    if bpm_filters:
        filters.append(and_(*bpm_filters))

    if instruments:
        instrument_list = [i.strip().lower() for i in instruments.split(',')]
        filters.append(func.lower(models.Instrument.name).in_(instrument_list))

    if genres:
        genre_list = [g.strip().lower() for g in genres.split(',')]
        subquery = exists().where(
            and_(
                models.AudioGenre.audio_id == models.Audio.id,
                models.Genre.id == models.AudioGenre.genre_id,
                func.lower(models.Genre.name).in_(genre_list)
            ))
        filters.append(subquery)

    if keys:
        key_list = [k.strip().lower() for k in keys.split(',')]
        query = query.join(models.Audio.key)
        filters.append(func.lower(models.Key.name).in_(key_list))

    if loop is not None:
        filters.append(models.Audio.is_loop == loop)

    if filters:
        query = query.filter(and_(*filters))

    query = query.options(
        joinedload(models.Audio.genres),
        joinedload(models.Audio.instrument),
        joinedload(models.Audio.key)
    )

    audios = query.all()

    if not audios:
        return []

    audio_ids = [audio.id for audio in audios]

    favorites_counts = db.query(
        models.Favorite.audio_id,
        func.count(models.Favorite.id).label('favorites_count')
    ).filter(
        models.Favorite.audio_id.in_(audio_ids)
    ).group_by(models.Favorite.audio_id).all()

    counts_dict = {fc.audio_id: fc.favorites_count for fc in favorites_counts}

    results = []
    for audio in audios:
        audio_dict = audio.to_dict()
        favorites_count = counts_dict.get(audio.id, 0)
        results.append({
            "audio": audio_dict,
            "favorites_count": favorites_count
        })

    return results

def delete_audio(db: Session, audio_id: int, user_id: int):
    db_audio = db.query(models.Audio).filter(
        models.Audio.id == audio_id,
        models.Audio.author_id == user_id
    ).first()
    
    if not db_audio:
        raise HTTPException(404, "Audio not found or access denied")
    
    db.query(models.AudioGenre).filter(models.AudioGenre.audio_id == audio_id).delete()
    db.query(models.PlaylistAudio).filter(models.PlaylistAudio.audio_id == audio_id).delete()
    db.query(models.Favorite).filter(models.Favorite.audio_id == audio_id).delete()
    
    for file_path in [db_audio.file, db_audio.cover]:
        if file_path:
            path = Path(file_path)
            if path.exists():
                path.unlink()
    
    db.delete(db_audio)
    db.commit()
    return {"status": "Audio deleted"}

def add_to_favorites(db: Session, user_id: int, audio_id: int = None, playlist_id: int = None):
    if not any([audio_id, playlist_id]):
        raise HTTPException(400, "Must provide either audio or playlist ID")
    
    favorite = models.Favorite(
        user_id=user_id,
        audio_id=audio_id,
        playlist_id=playlist_id
    )
    
    db.add(favorite)
    db.commit()
    return {"status": "added to favorites"}

def get_popular_audios(db: Session, limit: int):
    audio_counts = db.query(
        models.Audio.id,
        func.count(models.Favorite.id).label('favorites_count')
    ).outerjoin(
        models.Favorite,
        models.Audio.id == models.Favorite.audio_id
    ).group_by(models.Audio.id).order_by(
        func.count(models.Favorite.id).desc()
    ).limit(limit).all()

    if not audio_counts:
        return []

    audio_ids = [ac[0] for ac in audio_counts]
    counts_dict = {ac[0]: ac[1] for ac in audio_counts}

    audios = db.query(models.Audio).options(
        joinedload(models.Audio.genres),
        joinedload(models.Audio.instrument),
        joinedload(models.Audio.key),
        joinedload(models.Audio.author)
    ).filter(models.Audio.id.in_(audio_ids)).all()

    order_dict = {audio_id: idx for idx, audio_id in enumerate(audio_ids)}
    audios_sorted = sorted(audios, key=lambda a: order_dict[a.id])

    results = []
    for audio in audios_sorted:
        results.append({
            "audio": audio.to_dict(),
            "favorites_count": counts_dict[audio.id]
        })

    return results

# =====================
# Playlist control
# =====================

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

def delete_playlist(db: Session, playlist_id: int, user_id: int):
    db_playlist = db.query(models.Playlist).filter(
        models.Playlist.id == playlist_id,
        models.Playlist.author_id == user_id
    ).first()
    
    if not db_playlist:
        raise HTTPException(404, "Playlist not found or access denied")
    
    db.query(models.PlaylistAudio).filter(models.PlaylistAudio.playlist_id == playlist_id).delete()
    db.query(models.Favorite).filter(models.Favorite.playlist_id == playlist_id).delete()
    
    if db_playlist.cover:
        path = Path(db_playlist.cover)
        if path.exists():
            path.unlink()
    
    db.delete(db_playlist)
    db.commit()
    return {"status": "Playlist deleted"}

def get_popular_playlists(db: Session, limit: int):
    return db.query(models.Playlist).annotate(
        favorites_count=func.count(models.Favorite.id)
    ).outerjoin(models.Favorite).group_by(models.Playlist.id).order_by(
        favorites_count.desc()
    ).limit(limit).all()

def update_playlist(
    db: Session,
    playlist_id: int,
    user_id: int,
    name: str = None,
    cover: UploadFile = None
):
    playlist = db.query(models.Playlist).filter(
        models.Playlist.id == playlist_id,
        models.Playlist.author_id == user_id
    ).first()
    
    if not playlist:
        raise HTTPException(404, "Playlist not found")
    
    if name: playlist.name = name
    if cover: 
        playlist.cover = save_file("./uploads/playlist/cover", cover)
    
    db.commit()
    return playlist

def remove_audio_from_playlist(
    db: Session,
    playlist_id: int,
    audio_id: int,
    user_id: int
):
    # Проверка прав доступа
    playlist = db.query(models.Playlist).filter(
        models.Playlist.id == playlist_id,
        models.Playlist.author_id == user_id
    ).first()
    if not playlist:
        raise HTTPException(404, "Playlist not found")
    
    # Удаление связи
    db.query(models.PlaylistAudio).filter(
        models.PlaylistAudio.playlist_id == playlist_id,
        models.PlaylistAudio.audio_id == audio_id
    ).delete()
    
    # Обновление порядка треков
    tracks = db.query(models.PlaylistAudio).filter(
        models.PlaylistAudio.playlist_id == playlist_id
    ).order_by(models.PlaylistAudio.order).all()
    
    for idx, track in enumerate(tracks):
        track.order = idx + 1
    
    db.commit()
    return {"status": "audio removed"}
