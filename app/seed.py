from collections import defaultdict
from sqlmodel import Session, select

from . import models
from .db import engine
from .models import utc_now_iso
from .scripture import get_books_meta, load_scripture_data


def seed():
    scripture = load_scripture_data()
    books_meta = scripture.books_meta
    chapter_counts = scripture.chapter_counts
    versions = scripture.versions or ["KJV"]
    default_version = versions[0]

    with Session(engine) as session:
        # Bible
        bible = session.exec(select(models.Bibles).where(models.Bibles.bible_id == 1)).first()
        if not bible:
            bible = models.Bibles(
                bible_id=1,
                name="Sample Bible",
                language="English",
                version=default_version,
            )
            session.add(bible)
        else:
            bible.version = default_version

        # Canon books/chapters
        for book in books_meta:
            book_name = book["canon_book_name"]
            order = book["canonical_order"]
            testament = book["testament"]
            canon_book = session.exec(
                select(models.CanonBooks).where(models.CanonBooks.canon_book_name == book_name)
            ).first()
            if not canon_book:
                canon_book = models.CanonBooks(canon_book_name=book_name, canonical_order=order, testament=testament)
                session.add(canon_book)
            else:
                canon_book.canonical_order = order
                canon_book.testament = testament

            chapter_nums = sorted({ch for (b, ch), _ in chapter_counts.items() if b == book_name})
            for chapter_num in chapter_nums:
                verse_count = chapter_counts[(book_name, chapter_num)]
                canon_chapter = session.exec(
                    select(models.CanonChapters).where(
                        models.CanonChapters.canon_book_name == book_name,
                        models.CanonChapters.canon_book_chapter == chapter_num,
                    )
                ).first()
                if not canon_chapter:
                    canon_chapter = models.CanonChapters(
                        canon_book_name=book_name,
                        canon_book_chapter=chapter_num,
                        verse_count=verse_count,
                    )
                    session.add(canon_chapter)

        # Books and chapters for bible 1
        for book in books_meta:
            book_name = book["canon_book_name"]
            book = session.exec(
                select(models.Books).where(
                    models.Books.bible_id == 1, models.Books.canon_book_name == book_name
                )
            ).first()
            if not book:
                book = models.Books(bible_id=1, canon_book_name=book_name)
                session.add(book)
                session.flush()
            chapter_nums = sorted({ch for (b, ch), _ in chapter_counts.items() if b == book_name})
            for chapter_num in chapter_nums:
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
