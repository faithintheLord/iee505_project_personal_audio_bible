import io
import zipfile
from datetime import timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select

from . import auth as auth_utils
from . import crud, models, schemas
from .db import get_session, init_db
from .models import utc_now_iso
from .seed import seed
from . import scripture

app = FastAPI(title="Personal Audio Bible")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")


def _compute_metrics(text: Optional[str], duration: Optional[float]) -> tuple[Optional[int], Optional[float]]:
    if not text:
        return None, None
    wc = crud.word_count(text)
    if duration and duration > 0:
        return wc, (wc / duration) * 60
    return wc, None


@app.on_event("startup")
def on_startup():
    init_db()
    seed()


# Auth endpoints
@app.post("/api/register", response_model=schemas.Token)
def register(payload: schemas.UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(
        select(models.Users).where(
            (models.Users.username == payload.username) | (models.Users.email == payload.email)
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    hashed = auth_utils.get_password_hash(payload.password)
    user = models.Users(
        username=payload.username, name=payload.name, email=payload.email, password=hashed
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    auth = models.Auths(user_id=user.user_id)
    session.add(auth)
    session.commit()
    session.refresh(auth)

    # Grant default access to bible 1
    for cls in (models.ManageAuths, models.ListenAuths):
        grant = session.exec(
            select(cls).where(cls.auth_id == auth.auth_id, cls.bible_id == 1)
        ).first()
        if not grant:
            session.add(cls(auth_id=auth.auth_id, bible_id=1))
    session.commit()

    token = auth_utils.create_access_token({"sub": str(user.user_id)})
    user_read = schemas.UserRead.model_validate(user)
    return schemas.Token(access_token=token, user=user_read)


@app.post("/api/login", response_model=schemas.Token)
def login(payload: schemas.UserLogin, session: Session = Depends(get_session)):
    user = session.exec(
        select(models.Users).where(
            (models.Users.username == payload.username_or_email)
            | (models.Users.email == payload.username_or_email)
        )
    ).first()
    if not user or not auth_utils.verify_password(payload.password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect credentials")
    token = auth_utils.create_access_token({"sub": str(user.user_id)}, timedelta(minutes=1440))
    user_read = schemas.UserRead.model_validate(user)
    return schemas.Token(access_token=token, user=user_read)


# Bible navigation
@app.get("/api/bibles")
def get_bibles(
    session: Session = Depends(get_session), current_user: models.Users = Depends(auth_utils.get_current_user)
):
    auth = session.exec(select(models.Auths).where(models.Auths.user_id == current_user.user_id)).first()
    if not auth:
        return []
    bible_ids = {
        *[row.bible_id for row in session.exec(select(models.ListenAuths).where(models.ListenAuths.auth_id == auth.auth_id))],
        *[row.bible_id for row in session.exec(select(models.ManageAuths).where(models.ManageAuths.auth_id == auth.auth_id))],
    }
    return session.exec(select(models.Bibles).where(models.Bibles.bible_id.in_(bible_ids))).all() if bible_ids else []


@app.get("/api/bibles/{bible_id}/books")
def get_books(
    bible_id: int,
    session: Session = Depends(get_session),
    current_user: models.Users = Depends(auth_utils.get_current_user),
):
    crud.ensure_listen(session, current_user, bible_id)
    results = session.exec(
        select(models.Books, models.CanonBooks)
        .where(models.Books.bible_id == bible_id)
        .join(models.CanonBooks, models.CanonBooks.canon_book_name == models.Books.canon_book_name)
        .order_by(models.CanonBooks.canonical_order)
    ).all()
    # Return JSON-friendly objects in the same shape the frontend expects
    return [
        {"Books": book.model_dump(), "CanonBooks": canon.model_dump()}
        for book, canon in results
    ]


@app.get("/api/books/{book_id}/chapters")
def get_chapters(
    book_id: int,
    session: Session = Depends(get_session),
    current_user: models.Users = Depends(auth_utils.get_current_user),
):
    book = session.get(models.Books, book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    crud.ensure_listen(session, current_user, book.bible_id)
    results = session.exec(
        select(models.Chapters, models.CanonChapters)
        .where(models.Chapters.book_id == book_id)
        .join(
            models.CanonChapters,
            (models.CanonChapters.canon_book_name == models.Chapters.canon_book_name)
            & (models.CanonChapters.canon_book_chapter == models.Chapters.canon_book_chapter),
        )
        .order_by(models.CanonChapters.canon_book_chapter)
    ).all()
    return [
        {"Chapters": chapter.model_dump(), "CanonChapters": canon.model_dump()}
        for chapter, canon in results
    ]


@app.get("/api/versions")
def get_versions(
    current_user: models.Users = Depends(auth_utils.get_current_user),
):
    versions = scripture.get_versions()
    return versions or ["KJV"]


@app.get("/api/verses")
def get_verses(
    book: str,
    chapter: int,
    start: int,
    end: int,
    version: str = "KJV",
    current_user: models.Users = Depends(auth_utils.get_current_user),
):
    if start < 1 or end < start:
        raise HTTPException(status_code=400, detail="Invalid verse range")
    chapter_max = scripture.get_chapter_count(book, chapter)
    if chapter_max and end > chapter_max:
        raise HTTPException(status_code=400, detail="Verse end exceeds chapter")
    text = scripture.get_passage_text(book, chapter, start, end, version)
    if not text:
        raise HTTPException(status_code=404, detail="Passage not found")
    return {"text": text}


def _aggregate(values: list[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def _percentile(sorted_vals: list[float], p: float) -> Optional[float]:
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def _stddev(values: list[float], mean: float) -> Optional[float]:
    if not values or mean is None:
        return None
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return var**0.5


def _histogram(values: list[float], bins: int = 10) -> list[dict]:
    if not values:
        return []
    vmin, vmax = min(values), max(values)
    if vmin == vmax:
        return [{"bin_start": vmin, "bin_end": vmax, "count": len(values)}]
    width = (vmax - vmin) / bins
    edges = [vmin + i * width for i in range(bins + 1)]
    counts = [0] * bins
    for v in values:
        idx = min(int((v - vmin) / width), bins - 1)
        counts[idx] += 1
    hist = []
    for i, count in enumerate(counts):
        hist.append({"bin_start": edges[i], "bin_end": edges[i + 1], "count": count})
    return hist


@app.get("/api/bibles/{bible_id}/analytics")
def bible_analytics(
    bible_id: int,
    session: Session = Depends(get_session),
    current_user: models.Users = Depends(auth_utils.get_current_user),
):
    crud.ensure_listen(session, current_user, bible_id)
    rows = session.exec(
        select(models.Recordings, models.Chapters, models.Books)
        .join(models.Chapters, models.Chapters.chapter_id == models.Recordings.chapter_id)
        .join(models.Books, models.Books.book_id == models.Chapters.book_id)
        .where(models.Books.bible_id == bible_id)
    ).all()
    total_words = 0
    total_duration = 0.0
    total_plays = 0
    wpm_values: list[float] = []
    word_values: list[int] = []
    by_book: dict[str, dict] = {}

    for rec, chap, _book in rows:
        wc = rec.word_count
        if wc is None and rec.transcription_text:
            wc = crud.word_count(rec.transcription_text)
        if wc is not None:
            total_words += wc
            word_values.append(wc)
        if rec.duration_seconds:
            total_duration += rec.duration_seconds
        total_plays += rec.accessed_count
        wpm = rec.wpm
        if wpm is None and wc and rec.duration_seconds and rec.duration_seconds > 0:
            wpm = (wc / rec.duration_seconds) * 60
        if wpm is not None:
            wpm_values.append(wpm)

    wpm_values_sorted = sorted(wpm_values)
    mean_wpm = _aggregate(wpm_values)
    stats = {
        "count": len(wpm_values),
        "min": min(wpm_values) if wpm_values else None,
        "max": max(wpm_values) if wpm_values else None,
        "mean": mean_wpm,
        "median": _percentile(wpm_values_sorted, 0.5),
        "std": _stddev(wpm_values, mean_wpm) if mean_wpm is not None else None,
        "q1": _percentile(wpm_values_sorted, 0.25),
        "q3": _percentile(wpm_values_sorted, 0.75),
        "histogram": _histogram(wpm_values),
    }

    return {
        "total_recordings": len(rows),
        "total_words": total_words,
        "avg_word_count": _aggregate(word_values),
        "avg_wpm": mean_wpm,
        "avg_duration_seconds": (total_duration / len(rows)) if rows else None,
        "total_plays": total_plays,
        "wpm_stats": stats,
    }


# Recordings CRUD
@app.get("/api/bibles/{bible_id}/recordings", response_model=List[schemas.RecordingRead])
def list_recordings(
    bible_id: int,
    session: Session = Depends(get_session),
    current_user: models.Users = Depends(auth_utils.get_current_user),
):
    crud.ensure_listen(session, current_user, bible_id)
    results = session.exec(
        select(models.Recordings, models.Chapters, models.Books)
        .join(models.Chapters, models.Chapters.chapter_id == models.Recordings.chapter_id)
        .join(models.Books, models.Books.book_id == models.Chapters.book_id)
        .where(models.Books.bible_id == bible_id)
    ).all()
    output = []
    for rec, chap, book in results:
        canon = session.exec(
            select(models.CanonChapters).where(
                models.CanonChapters.canon_book_name == chap.canon_book_name,
                models.CanonChapters.canon_book_chapter == chap.canon_book_chapter,
            )
        ).first()
        stored_wpm = rec.wpm
        stored_wc = rec.word_count
        if stored_wpm is None and rec.duration_seconds and rec.duration_seconds > 0 and rec.transcription_text:
            stored_wc = crud.word_count(rec.transcription_text)
            stored_wpm = (stored_wc / rec.duration_seconds) * 60
        output.append(
            schemas.RecordingRead(
                recording_id=rec.recording_id,
                book_name=chap.canon_book_name,
                chapter_number=chap.canon_book_chapter,
                verse_start=rec.verse_index_start,
                verse_end=rec.verse_index_end,
                date_recorded=rec.date_recorded,
                accessed_count=rec.accessed_count,
                duration_seconds=rec.duration_seconds,
                transcription_text=rec.transcription_text,
                computed_wpm=stored_wpm,
            )
        )
    return output


@app.post("/api/recordings")
def create_recording(
    bible_id: int = Form(...),
    chapter_id: int = Form(...),
    verse_index_start: int = Form(...),
    verse_index_end: int = Form(...),
    duration_seconds: Optional[float] = Form(None),
    transcription_text: Optional[str] = Form(None),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: models.Users = Depends(auth_utils.get_current_user),
):
    book = session.exec(
        select(models.Books)
        .join(models.Chapters, models.Chapters.book_id == models.Books.book_id)
        .where(models.Chapters.chapter_id == chapter_id)
    ).first()
    if not book:
        raise HTTPException(status_code=400, detail="Invalid chapter")
    crud.ensure_manage(session, current_user, book.bible_id)
    canon_chapter = session.exec(
        select(models.CanonChapters).where(
            models.CanonChapters.canon_book_name == book.canon_book_name,
            models.CanonChapters.canon_book_chapter == session.get(models.Chapters, chapter_id).canon_book_chapter,
        )
    ).first()
    if not canon_chapter:
        raise HTTPException(status_code=400, detail="Missing canon data")
    if verse_index_start < 1 or verse_index_end < verse_index_start:
        raise HTTPException(status_code=400, detail="Invalid verse range")
    if verse_index_end > canon_chapter.verse_count:
        raise HTTPException(status_code=400, detail="Verse end exceeds chapter")

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    word_count, wpm = _compute_metrics(transcription_text, duration_seconds)
    recording = models.Recordings(
        user_id=current_user.user_id,
        chapter_id=chapter_id,
        date_recorded=utc_now_iso(),
        verse_index_start=verse_index_start,
        verse_index_end=verse_index_end,
        file=content,
        file_mime=file.content_type,
        duration_seconds=duration_seconds,
        transcription_text=transcription_text,
        word_count=word_count,
        wpm=wpm,
    )
    session.add(recording)
    session.commit()
    session.refresh(recording)
    return {"recording_id": recording.recording_id}


@app.get("/api/recordings/{recording_id}/audio")
def stream_audio(
    recording_id: int,
    session: Session = Depends(get_session),
    current_user: models.Users = Depends(auth_utils.get_current_user),
):
    recording = session.get(models.Recordings, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Not found")
    chapter = session.get(models.Chapters, recording.chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter missing")
    book = session.get(models.Books, chapter.book_id)
    crud.ensure_listen(session, current_user, book.bible_id)

    recording.accessed_count += 1
    recording.date_last_accessed = utc_now_iso()
    session.add(recording)
    session.commit()

    return StreamingResponse(io.BytesIO(recording.file), media_type=recording.file_mime or "application/octet-stream")


@app.delete("/api/recordings/{recording_id}")
def delete_recording(
    recording_id: int,
    session: Session = Depends(get_session),
    current_user: models.Users = Depends(auth_utils.get_current_user),
):
    recording = session.get(models.Recordings, recording_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Not found")
    chapter = session.get(models.Chapters, recording.chapter_id)
    book = session.get(models.Books, chapter.book_id) if chapter else None
    if not book:
        raise HTTPException(status_code=404, detail="Book missing")
    crud.ensure_manage(session, current_user, book.bible_id)
    session.delete(recording)
    session.commit()
    return {"ok": True}


@app.get("/api/bibles/{bible_id}/download")
def download_zip(
    bible_id: int,
    session: Session = Depends(get_session),
    current_user: models.Users = Depends(auth_utils.get_current_user),
):
    crud.ensure_listen(session, current_user, bible_id)
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        recordings = session.exec(
            select(models.Recordings, models.Chapters, models.Books)
            .join(models.Chapters, models.Chapters.chapter_id == models.Recordings.chapter_id)
            .join(models.Books, models.Books.book_id == models.Chapters.book_id)
            .where(models.Books.bible_id == bible_id)
        ).all()
        counter = {}
        for rec, chap, book in recordings:
            key = (chap.canon_book_name, chap.canon_book_chapter)
            counter[key] = counter.get(key, 0) + 1
            suffix = f"_{counter[key]:03d}" if counter[key] > 1 else ""
            ext = ".webm" if rec.file_mime == "audio/webm" else ".wav" if rec.file_mime == "audio/wav" else ".bin"
            path = f"{chap.canon_book_name}/{chap.canon_book_chapter:02d}{suffix}{ext}"
            zf.writestr(path, rec.file)
    mem.seek(0)
    return StreamingResponse(mem, media_type="application/zip", headers={"Content-Disposition": "attachment; filename=bible.zip"})


@app.get("/", include_in_schema=False)
def root():
    return FileResponse("app/static/login.html")
