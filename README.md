# Personal Audio Bible (Minimal Prototype)

A small FastAPI + SQLite project that demonstrates the Personal Audio Bible workflow. It offers JWT-based auth, a minimal schema mirroring the provided DR model, and a simple two-page static frontend.

## Quick start
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# Then open http://127.0.0.1:8000/static/login.html
```

The database file `app.db` lives in the project root. Tables are created automatically on startup, and `app/seed.py` seeds a single Bible with a few John chapters. Run `python -m app.seed` anytime to re-seed.

## Project layout
- `app/main.py` – FastAPI app, endpoints, and static hosting.
- `app/db.py` – SQLModel engine/session helpers.
- `app/settings.py` – Basic configuration (SQLite URL, JWT settings).
- `app/models.py` – SQLModel table definitions reflecting the DR model plus minimal extras.
- `app/schemas.py` – Pydantic request/response models.
- `app/auth.py` – Password hashing and JWT helpers.
- `app/crud.py` – Access control helpers and small utilities.
- `app/seed.py` – Idempotent seed data for one sample Bible.
- `app/static/` – Two static pages (`login.html`, `app.html`) with plain JS and CSS.
- `requirements.txt` – Python dependencies.
- `schema.sql` – Optional schema outline for reference.
- `scripture.csv` – Canon data (books/chapters/verses/text) used to seed the Bible and provide verse lookups.

## API outline
- `POST /api/register` – create user + auth grants for Bible 1 and return token.
- `POST /api/login` – login via username or email.
- `GET /api/me` – current user.
- `GET /api/bibles` – list bibles the user can access.
- `GET /api/bibles/{id}/books` – books for a bible (requires listen/manage).
- `GET /api/books/{id}/chapters` – chapters for a book.
- `GET /api/versions` – list available scripture versions from `scripture.csv`.
- `GET /api/verses` – fetch verse text for a book/chapter/range/version (used to auto-fill transcription).
- `GET /api/bibles/{id}/recordings` – list recordings with WPM.
- `GET /api/bibles/{id}/analytics` – aggregated metrics (WPM stats with min/max/mean/median/std + histogram, word counts, durations).
- `POST /api/recordings` – upload audio (multipart/form-data) + metadata.
- `GET /api/recordings/{id}/audio` – stream audio (increments play count).
- `PUT /api/recordings/{id}` – update verse range/transcription.
- `DELETE /api/recordings/{id}` – remove a recording.
- `GET /api/bibles/{id}/download` – download a `bible.zip` of recordings.

## Frontend walkthrough
1. Visit `/static/login.html` to register or log in. On success the JWT is stored in `localStorage` and you are sent to `app.html`.
2. On `app.html`:
   - Choose the seeded Bible, then pick a book and chapter.
   - Use the Start/Stop buttons to record in-browser (MediaRecorder), then upload with verse range and optional transcription.
   - The Library table lists recordings, allows playback (auth-aware fetch → blob URL), and deletion.
   - Use "Download bible.zip" to retrieve all recordings grouped by book/chapter.

## Notes
- Passwords are hashed with bcrypt via passlib; JWTs are signed with a generated secret key.
- Access control follows the ManageAuths/ListenAuths links. Registration automatically grants both for Bible 1.
- Validation enforces verse ranges against the canon chapter sample and prevents empty uploads.
- Styling is intentionally monochrome and framework-free for clarity.
- Recordings store `word_count` and `wpm` on save; `/api/bibles/{id}/analytics` reads those values to return aggregate stats.
