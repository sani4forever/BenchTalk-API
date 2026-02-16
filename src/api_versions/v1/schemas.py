"""
SQLAlchemy schemas for Dating App API.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Text,
    Float,
    create_engine,
    UniqueConstraint,
    Index, JSON,
)
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

from . import version_constants

__all__ = [
    'User', 'Photo', 'Swipe', 'Match', 'Message', 'Base','MeetingBench',
    'get_engine'
]

Base = declarative_base()

def get_engine() -> Engine:
    """Get the engine for the database."""
    if not version_constants.POSTGRES_NAME:
        raise ValueError('POSTGRES_NAME is not set')

    url = URL.create(
        drivername='postgresql+psycopg2',
        host=version_constants.POSTGRES_HOST,
        port=version_constants.POSTGRES_PORT,
        username=version_constants.POSTGRES_USER,
        password=version_constants.POSTGRES_PASSWORD,
        database=version_constants.POSTGRES_NAME
    )

    try:
        engine = create_engine(url, echo=False)
        Base.metadata.create_all(engine)
    except OperationalError:
        connection = psycopg2.connect(
            dbname='postgres',
            user=version_constants.POSTGRES_USER,
            password=version_constants.POSTGRES_PASSWORD,
            host=version_constants.POSTGRES_HOST,
            port=version_constants.POSTGRES_PORT,
        )
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        cursor.execute(f'CREATE DATABASE {version_constants.POSTGRES_NAME};')
        cursor.close()
        connection.close()

        engine = create_engine(url, echo=False)
        Base.metadata.create_all(engine)

    return engine


class User(Base):
    """
    Основная таблица пользователей
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(50), nullable=False)
    bio = Column(Text, nullable=True)

    latitude = Column(Float, nullable=True, index=True)
    longitude = Column(Float, nullable=True, index=True)
    last_location = Column(String(255), nullable=True)

    looking_for_gender = Column(String(50), nullable=True)
    min_age = Column(Integer, default=18)
    max_age = Column(Integer, default=99)
    max_distance_km = Column(Integer, default=50)

    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    photos = relationship("Photo", back_populates="user", cascade="all, delete-orphan", lazy="joined")
    swipes_made = relationship("Swipe", foreign_keys="Swipe.from_user_id", back_populates="from_user")
    swipes_received = relationship("Swipe", foreign_keys="Swipe.to_user_id", back_populates="to_user")
    matches_as_user_one = relationship("Match", foreign_keys="Match.user_one_id", back_populates="user_one")
    matches_as_user_two = relationship("Match", foreign_keys="Match.user_two_id", back_populates="user_two")
    messages_sent = relationship("Message", foreign_keys="Message.sender_id", back_populates="sender")
    messages_received = relationship("Message", foreign_keys="Message.receiver_id", back_populates="receiver")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"


class Photo(Base):
    """
    Фотографии пользователей
    """
    __tablename__ = 'photos'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    url = Column(String(512), nullable=False)
    order_index = Column(Integer, default=0)
    is_primary = Column(Boolean, default=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="photos")

    __table_args__ = (
        Index('idx_user_order', 'user_id', 'order_index'),
    )

    def __repr__(self) -> str:
        return f"<Photo(id={self.id}, user_id={self.user_id}, order={self.order_index})>"


class Swipe(Base):
    """
    История свайпов (лайки/дизлайки)
    """
    __tablename__ = 'swipes'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    from_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    to_user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    type = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    from_user = relationship("User", foreign_keys=[from_user_id], back_populates="swipes_made")
    to_user = relationship("User", foreign_keys=[to_user_id], back_populates="swipes_received")

    __table_args__ = (
        UniqueConstraint('from_user_id', 'to_user_id', name='unique_swipe'),
        Index('idx_swipe_lookup', 'to_user_id', 'from_user_id', 'type'),
    )

    def __repr__(self) -> str:
        return f"<Swipe(from={self.from_user_id}, to={self.to_user_id}, type={self.type})>"


class Match(Base):
    """
    Взаимные лайки (мэтчи)
    """
    __tablename__ = 'matches'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_one_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    user_two_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    user_one = relationship("User", foreign_keys=[user_one_id], back_populates="matches_as_user_one")
    user_two = relationship("User", foreign_keys=[user_two_id], back_populates="matches_as_user_two")
    messages = relationship("Message", back_populates="match", cascade="all, delete-orphan")
    meeting_benches = relationship("MeetingBench",back_populates="match",cascade="all, delete-orphan",lazy="joined")

    __table_args__ = (
        UniqueConstraint('user_one_id', 'user_two_id', name='unique_match'),
        Index('idx_match_users', 'user_one_id', 'user_two_id'),
    )

    def __repr__(self) -> str:
        return f"<Match(id={self.id}, users=[{self.user_one_id}, {self.user_two_id}])>"


class Message(Base):
    """
    Сообщения между пользователями (только после мэтча)
    """
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey('matches.id', ondelete='CASCADE'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    receiver_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    message_text = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    match = relationship("Match", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="messages_received")

    __table_args__ = (
        Index('idx_match_messages', 'match_id', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, match={self.match_id}, from={self.sender_id})>"

class MeetingBench(Base):
    __tablename__ = 'meeting_benches'

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey('matches.id', ondelete='CASCADE'), nullable=False)
    osm_id = Column(String(50), nullable=False)
    osm_type = Column(String(20))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    distance_user_a_km = Column(Float)
    distance_user_b_km = Column(Float)
    total_distance_km = Column(Float)
    fairness_diff_km = Column(Float)
    score = Column(Float)
    osm_tags = Column(JSON)
    suggested_at = Column(DateTime(timezone=True), server_default=func.now())
    is_accepted = Column(Boolean, default=False)

    match = relationship("Match", back_populates="meeting_benches")