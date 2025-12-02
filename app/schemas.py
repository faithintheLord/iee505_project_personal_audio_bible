from datetime import datetime, timedelta
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator, ConfigDict


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
    model_config = ConfigDict(from_attributes=True)


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

    @field_validator("verse_index_start")
    @classmethod
    def start_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("VerseIndexStart must be >= 1")
        return v

    @model_validator(mode="after")
    def validate_range(self):
        if self.verse_index_end < self.verse_index_start:
            raise ValueError("VerseIndexEnd must be >= start")
        return self


class RecordingUpdate(BaseModel):
    verse_index_start: Optional[int] = None
    verse_index_end: Optional[int] = None
    transcription_text: Optional[str] = None

    @field_validator("verse_index_start")
    @classmethod
    def start_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("VerseIndexStart must be >= 1")
        return v

    @model_validator(mode="after")
    def validate_range(self):
        if (
            self.verse_index_start is not None
            and self.verse_index_end is not None
            and self.verse_index_end < self.verse_index_start
        ):
            raise ValueError("VerseIndexEnd must be >= start")
        return self


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
