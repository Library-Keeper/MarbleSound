    from fastapi import FastAPI, HTTPException, Depends, File, UploadFile
    from typing import Annotated, List
    import models
    from database import engine, SessionLocal
    from sqlalchemy.orm import Session
    import crud


    tags_metadata = [
        {
            "name": "User control",
            "description": "Operations with users. The **login** logic is also here."
        },
        {
            "name": "Audio control",
            "description": "Operations with audios."
        },
        {
            "name": "Playlist control",
            "description": "Operations with playlists."
        },
    ]



    app = FastAPI(openapi_tags=tags_metadata)
    models.Base.metadata.create_all(bind=engine)

    def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    db = Annotated[Session, Depends(get_db)]

    # =====================
    # User control
    # =====================

    @app.post("/user/create/", status_code=201, tags=["User control"])
    def create_user(
        db: db, 
        username: str, 
        password: str
        ):
        user = crud.get_user(db, crud.SearchBy.username, username=username)
        
        if user:
            raise HTTPException(404)
        return crud.create_user(username=username, password=password, db=db)

    @app.post("/user/logout/", status_code=200, tags=["User control"])
    def user_logout(
        db: db, 
        id: int, 
        session: str
        ):
        if not crud.check_user_session(db, id, session):
            raise HTTPException(403)
        return crud.user_logout(db=db, id=id, session=session)

    @app.post("/user/login/", status_code=201, tags=["User control"])
    def user_login(
        db: db, 
        username: str, 
        password: str
        ):
        return crud.user_login(db=db, username=username, password=password)

    @app.get("/user/", status_code=200, tags=["User control"])
    def get_user(
        db: db, 
        search_by: crud.SearchBy, 
        username: str = None, 
        id: int = None
        ):
        return crud.get_user(db=db, search_by=search_by, username=username, id=id)

    @app.get("/users/", status_code=200, tags=["User control"])
    def get_users(
        db: db, 
        username: str = None
        ):
        return crud.get_users(db=db, username=username)

    @app.put("/user/update/", status_code=202, tags=["User control"])
    def update_user_data(
        db: db, 
        id: int, 
        session: str, 
        username: str = None, 
        description: str = None
        ):
        if not crud.check_user_session(db, id, session):
            raise HTTPException(403)
        return crud.update_user_data(db, id, username, description)

    @app.put("/user/update/avatar/", status_code=202, tags=["User control"])
    def update_user_avatar(
        db: db, 
        id: int, 
        session: str, 
        avatar: UploadFile
        ):
        if not crud.check_user_session(db, id, session):
            raise HTTPException(403)
        return crud.update_user_avatar(db, id, avatar)

    @app.get("/user/avatar/", status_code=200, tags=["User control"])
    def get_user_avatar(
        db: db, 
        id: int
        ):
        return crud.get_user_avatar(db, id)

    @app.delete("/user/delete/", status_code=200, tags=["User control"])
    def delete_user(
        db: db,
        id: int,
        session
        ):
        return crud.delete_user(db, id, session)

    @app.get("/user/{user_id}/favorites", status_code=200, tags=["User control"])
    def get_user_favorites(db: db, user_id: int):
        return crud.get_user_favorites(db, user_id)

    # =====================
    # Audio control
    # =====================

    @app.post("/audio/create/", status_code=201, tags=["Audio control"])
    def create_audio(
        db: db, 
        id: int, 
        session: str, 
        file: UploadFile, 
        title: str, 
        instrument: str, 
        is_loop: bool, 
        key: str= None, 
        bpm: int = None, 
        genre: List[str] = None, 
        cover: UploadFile = None
        ):
        if not crud.check_user_session(db, id, session):
            raise HTTPException(403)
        return crud.create_audio(db, id, file, cover, title, is_loop, key, bpm, genre, instrument)

    @app.get("/audio/{audio_id}", status_code=200, tags=["Audio control"])
    def get_audio(
        db: db, 
        audio_id: int = None
        ):
        return crud.get_audio(db, audio_id)

    @app.post("/audios/", status_code=200, tags=["Audio control"])
    def search_audio(
        db: db, 
        title: str = None, 
        bpm: int = None, 
        genre: List[str] = None, 
        instrument: str = None, 
        loop: bool = None
        ):
        return crud.search_audio(db, title, bpm, genre, instrument, loop)

    @app.get("/genres/", status_code=200, tags=["Audio control"])
    def get_genres(db: db):
        return crud.get_genre(db)

    @app.get("/keys/", status_code=200, tags=["Audio control"])
    def get_all_keys(db: db):
        return crud.get_all_keys(db)

    @app.get("/instruments/", status_code=200, tags=["Audio control"])
    def get_all_instruments(db: db):
        return crud.get_all_instruments(db)

    @app.delete("/audio/delete/{audio_id}", status_code=200, tags=["Audio control"])
    def delete_audio(
        db: db,
        audio_id: int,
        id: int,
        session: str
    ):
        if not crud.check_user_session(db, id, session):
            raise HTTPException(403)
        return crud.delete_audio(db, audio_id, id)

    @app.post("/favorite/audio/{audio_id}", status_code=201, tags=["Audio control"])
    def add_audio_to_favorites(
        db: db,
        audio_id: int,
        user_id: int,
        session: str
    ):
        if not crud.check_user_session(db, user_id, session):
            raise HTTPException(403)
        return crud.add_to_favorites(db, user_id=user_id, audio_id=audio_id)

    @app.get("/audios/popular", status_code=200, tags=["Audio control"])
    def get_popular_audios(db: db, limit: int = 10):
        return crud.get_popular_audios(db, limit)

    # =====================
    # Playlist control
    # =====================

    @app.post("/playlist/create/", status_code=201, tags=["Playlist control"])
    def create_playlist(
        db: db, 
        id: int, 
        session: str, 
        name: str,
        cover: UploadFile = File(None)
        ):
        if not crud.check_user_session(db, id, session):
            raise HTTPException(403)
        return crud.create_playlist(db, id, name, cover)

    @app.post("/playlist/{playlist_id}/add/", status_code=200, tags=["Playlist control"])
    def add_to_playlist(
        db: db,
        playlist_id: int,
        audio_id: int,
        id: int,
        session: str
        ):
        if not crud.check_user_session(db, id, session):
            raise HTTPException(403)
        return crud.add_audio_to_playlist(db, playlist_id, audio_id, id)

    @app.get("/playlist/{playlist_id}/", status_code=200, tags=["Playlist control"])
    def get_playlist(
        db: db, 
        playlist_id: int
        ):
        return crud.get_playlist(db, playlist_id)

    @app.delete("/playlist/delete/{playlist_id}", status_code=200, tags=["Playlist control"])
    def delete_playlist(
        db: db,
        playlist_id: int,
        id: int,
        session: str
    ):
        if not crud.check_user_session(db, id, session):
            raise HTTPException(403)
        return crud.delete_playlist(db, playlist_id, id)

    @app.get("/playlists/popular", status_code=200, tags=["Playlist control"])
    def get_popular_playlists(db: db, limit: int = 10):
        return crud.get_popular_playlists(db, limit)
