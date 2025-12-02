from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, EmailStr, validator


class UserCreate(BaseModel):
    username: str
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username_or_email: str
    password: str


class UserRead(BaseModel):
    user_id: int
    username: str
    name: str
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class RecordingCreate(BaseModel):
    bible_id: int
    chapter_id: int
    verse_index_start: int
    verse_index_end: int
    duration_seconds: Optional[float] = None
    transcription_text: Optional[str] = None

    @validator("verse_index_start")
    def start_positive(cls, v):
        if v < 1:
            raise ValueError("VerseIndexStart must be >= 1")
        return v

    @validator("verse_index_end")
    def end_positive(cls, v, values):
        start = values.get("verse_index_start")
        if start is not None and v < start:
            raise ValueError("VerseIndexEnd must be >= start")
        return v


class RecordingUpdate(BaseModel):
    verse_index_start: Optional[int] = None
    verse_index_end: Optional[int] = None
    transcription_text: Optional[str] = None

    @validator("verse_index_start")
    def start_positive(cls, v):
        if v is not None and v < 1:
            raise ValueError("VerseIndexStart must be >= 1")
        return v

    @validator("verse_index_end")
    def end_positive(cls, v, values):
        start = values.get("verse_index_start")
        if v is not None and start is not None and v < start:
            raise ValueError("VerseIndexEnd must be >= start")
        return v


class RecordingRead(BaseModel):
    recording_id: int
    book_name: str
    chapter_number: int
    verse_start: int
    verse_end: int
    date_recorded: str
    accessed_count: int
    duration_seconds: Optional[float]
    transcription_text: Optional[str]
    computed_wpm: Optional[float]
