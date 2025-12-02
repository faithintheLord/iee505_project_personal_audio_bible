from sqlmodel import Session, select

from . import models
from .db import engine
from .models import utc_now_iso


CANON_SAMPLE = {
    "John": {
        1: 51,
        2: 25,
        3: 36,
    }
}


def seed():
    with Session(engine) as session:
        # Bible
        bible = session.exec(select(models.Bibles).where(models.Bibles.bible_id == 1)).first()
        if not bible:
            bible = models.Bibles(bible_id=1, name="Sample Bible", language="English", version="Simple")
            session.add(bible)

        # Canon books/chapters
        for order, (book_name, chapters) in enumerate(CANON_SAMPLE.items(), start=1):
            canon_book = session.exec(
                select(models.CanonBooks).where(models.CanonBooks.canon_book_name == book_name)
            ).first()
            if not canon_book:
                canon_book = models.CanonBooks(
                    canon_book_name=book_name, canonical_order=order, testament="New"
                )
                session.add(canon_book)
            for chapter_num, verse_count in chapters.items():
                canon_chapter = session.exec(
                    select(models.CanonChapters).where(
                        models.CanonChapters.canon_book_name == book_name,
                        models.CanonChapters.canon_book_chapter == chapter_num,
                    )
                ).first()
                if not canon_chapter:
                    session.add(
                        models.CanonChapters(
                            canon_book_name=book_name,
                            canon_book_chapter=chapter_num,
                            verse_count=verse_count,
                        )
                    )

        # Books and chapters for bible
        for book_name, chapters in CANON_SAMPLE.items():
            book = session.exec(
                select(models.Books).where(
                    models.Books.bible_id == 1, models.Books.canon_book_name == book_name
                )
            ).first()
            if not book:
                book = models.Books(bible_id=1, canon_book_name=book_name)
                session.add(book)
                session.flush()
            for chapter_num, verse_count in chapters.items():
                chapter = session.exec(
                    select(models.Chapters).where(
                        models.Chapters.book_id == book.book_id,
                        models.Chapters.canon_book_name == book_name,
                        models.Chapters.canon_book_chapter == chapter_num,
                    )
                ).first()
                if not chapter:
                    session.add(
                        models.Chapters(
                            book_id=book.book_id,
                            canon_book_name=book_name,
                            canon_book_chapter=chapter_num,
                        )
                    )
        session.commit()


if __name__ == "__main__":
    seed()
    print("Seed data inserted at", utc_now_iso())
