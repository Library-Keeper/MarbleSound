from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, ForeignKey, JSON 
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    avatar = Column(String(2048))
    description = Column(Text)
    date_of_reg = Column(DateTime, nullable=False)

    hashed_password = relationship("UserHashedData", backref="users", uselist=False)
    audios = relationship("Audio", backref="users")
    playlists = relationship("Playlist", backref="users")

class UserHashedData(Base):
    __tablename__ = "user_hashed_data"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    hashed_password = Column(Text, nullable=False)
    hashed_session = Column(Text)

class Audio(Base):
    __tablename__ = "audios"

    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    cover = Column(Text, nullable=True)
    file = Column(Text, nullable=False)
    key = Column(String(255), default="No key")
    instrument = Column(String(255), nullable=False)
    bpm = Column(Integer)
    is_loop = Column(Boolean, nullable=False, default=False)
    playlist_id = Column(Integer, ForeignKey("playlists.id"), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    genres = relationship("Genre", secondary="audiosgenres", back_populates="audios")

    favorite = relationship("Favorite", backref="audios")

class Genre(Base):
    __tablename__ = "genres"

    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    name = Column(String(128), nullable=False)

    audios = relationship("Audio", secondary="audiosgenres", back_populates="genres")

class AudioGenre(Base):
    __tablename__ = "audiosgenres"

    id = Column(Integer, autoincrement=True, primary_key=True)
    audio_id = Column(Integer, ForeignKey("audios.id"))
    genre_id = Column(Integer, ForeignKey("genres.id"))

class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    cover = Column(String(2048))
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    audio = relationship("Audio", backref="playlists")
    favorite = relationship("Favorite", backref="playlists")

class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    audio_id = Column(Integer, ForeignKey("audios.id"))
    playlist_id = Column(Integer, ForeignKey("playlists.id"))

