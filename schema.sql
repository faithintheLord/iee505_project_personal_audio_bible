-- Outline of tables used by the prototype
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT
);

CREATE TABLE auths (
    auth_id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id)
);

CREATE TABLE bibles (
    bible_id INTEGER PRIMARY KEY,
    name TEXT,
    language TEXT,
    version TEXT
);

CREATE TABLE listenauths (
    auth_id INTEGER REFERENCES auths(auth_id),
    bible_id INTEGER REFERENCES bibles(bible_id),
    PRIMARY KEY (auth_id, bible_id)
);

CREATE TABLE manageauths (
    auth_id INTEGER REFERENCES auths(auth_id),
    bible_id INTEGER REFERENCES bibles(bible_id),
    PRIMARY KEY (auth_id, bible_id)
);

CREATE TABLE canonbooks (
    canon_book_name TEXT PRIMARY KEY,
    canonical_order INTEGER,
    testament TEXT
);

CREATE TABLE canonchapters (
    canon_book_name TEXT REFERENCES canonbooks(canon_book_name),
    canon_book_chapter INTEGER,
    verse_count INTEGER,
    PRIMARY KEY (canon_book_name, canon_book_chapter)
);

CREATE TABLE books (
    book_id INTEGER PRIMARY KEY,
    bible_id INTEGER REFERENCES bibles(bible_id),
    canon_book_name TEXT REFERENCES canonbooks(canon_book_name)
);

CREATE TABLE chapters (
    chapter_id INTEGER PRIMARY KEY,
    book_id INTEGER REFERENCES books(book_id),
    canon_book_name TEXT,
    canon_book_chapter INTEGER,
    FOREIGN KEY (canon_book_name, canon_book_chapter)
        REFERENCES canonchapters(canon_book_name, canon_book_chapter)
);

CREATE TABLE recordings (
    recording_id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id),
    chapter_id INTEGER REFERENCES chapters(chapter_id),
    date_recorded TEXT,
    date_last_accessed TEXT,
    verse_index_start INTEGER,
    verse_index_end INTEGER,
    accessed_count INTEGER DEFAULT 0,
    file BLOB,
    file_mime TEXT,
    duration_seconds REAL,
    transcription_text TEXT
);
