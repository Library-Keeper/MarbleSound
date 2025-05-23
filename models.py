from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, ForeignKey, Float 
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
    key_id = Column(Integer, ForeignKey("keys.id"), nullable=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    bpm = Column(Integer)
    is_loop = Column(Boolean, nullable=False, default=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    duration = Column(Float)

    instrument = relationship("Instrument", back_populates="audios")
    genres = relationship("Genre", secondary="audiosgenres", back_populates="audios")
    playlists = relationship("Playlist", secondary="playlistaudio", back_populates="audios")
    favorite = relationship("Favorite", backref="audios")
    key = relationship("Key", back_populates="audios")
    author = relationship("User", back_populates="audios")

    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "cover": self.cover,
            "file": self.file,
            "duration": self.duration,
            "key": self.key.name if self.key else None,
            "instrument": self.instrument.name if self.instrument else None,
            "bpm": self.bpm,
            "is_loop": self.is_loop,
            "author_id": self.author_id,
            "genres": [genre.name for genre in self.genres],
            "author": {
                "id": self.author.id,
                "username": self.author.username,
                "avatar": self.author.avatar
            } if self.author else None
        }


class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)

    audios = relationship("Audio", back_populates="instrument")

class Key(Base):
    __tablename__ = "keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)

    audios = relationship("Audio", back_populates="key")


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
    audios = relationship("Audio", secondary="playlistaudio", back_populates="playlists")
    favorite = relationship("Favorite", backref="playlists")

class PlaylistAudio(Base):
    __tablename__ = "playlistaudio"
    
    id = Column(Integer, autoincrement=True, primary_key=True)
    playlist_id = Column(Integer, ForeignKey("playlists.id"))
    audio_id = Column(Integer, ForeignKey("audios.id"))
    order = Column(Integer, default=0)


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, autoincrement=True, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    audio_id = Column(Integer, ForeignKey("audios.id"))
    playlist_id = Column(Integer, ForeignKey("playlists.id"))

