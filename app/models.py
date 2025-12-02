from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel
from sqlalchemy import PrimaryKeyConstraint, ForeignKeyConstraint, LargeBinary


class Users(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    name: str
    email: str = Field(unique=True)
    password: str


class Auths(SQLModel, table=True):
    auth_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id")


class ListenAuths(SQLModel, table=True):
    auth_id: int = Field(foreign_key="auths.auth_id")
    bible_id: int = Field(foreign_key="bibles.bible_id")

    __table_args__ = (PrimaryKeyConstraint("auth_id", "bible_id"),)


class ManageAuths(SQLModel, table=True):
    auth_id: int = Field(foreign_key="auths.auth_id")
    bible_id: int = Field(foreign_key="bibles.bible_id")

    __table_args__ = (PrimaryKeyConstraint("auth_id", "bible_id"),)


class Bibles(SQLModel, table=True):
    bible_id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    language: str
    version: str


class CanonBooks(SQLModel, table=True):
    canon_book_name: str = Field(primary_key=True)
    canonical_order: int
    testament: str


class CanonChapters(SQLModel, table=True):
    canon_book_name: str = Field(foreign_key="canonbooks.canon_book_name", primary_key=True)
    canon_book_chapter: int = Field(primary_key=True)
    verse_count: int


class Books(SQLModel, table=True):
    book_id: Optional[int] = Field(default=None, primary_key=True)
    bible_id: int = Field(foreign_key="bibles.bible_id")
    canon_book_name: str = Field(foreign_key="canonbooks.canon_book_name")


class Chapters(SQLModel, table=True):
    chapter_id: Optional[int] = Field(default=None, primary_key=True)
    book_id: int = Field(foreign_key="books.book_id")
    canon_book_name: str
    canon_book_chapter: int

    __table_args__ = (
        ForeignKeyConstraint(
            ["canon_book_name", "canon_book_chapter"],
            ["canonchapters.canon_book_name", "canonchapters.canon_book_chapter"],
        ),
    )


class Recordings(SQLModel, table=True):
    recording_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.user_id")
    chapter_id: int = Field(foreign_key="chapters.chapter_id")
    date_recorded: str
    date_last_accessed: Optional[str] = None
    verse_index_start: int
    verse_index_end: int
    accessed_count: int = Field(default=0)
    file: bytes = Field(sa_type=LargeBinary)
    file_mime: Optional[str] = None
    duration_seconds: Optional[float] = None
    transcription_text: Optional[str] = None
    word_count: Optional[int] = None
    wpm: Optional[float] = None


# Utility helpers

def utc_now_iso() -> str:
    return datetime.utcnow().isoformat()
