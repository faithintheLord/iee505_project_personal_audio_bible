import csv
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

# Canonical book order for reference and ordering.
CANONICAL_ORDER = [
    "Genesis",
    "Exodus",
    "Leviticus",
    "Numbers",
    "Deuteronomy",
    "Joshua",
    "Judges",
    "Ruth",
    "1 Samuel",
    "2 Samuel",
    "1 Kings",
    "2 Kings",
    "1 Chronicles",
    "2 Chronicles",
    "Ezra",
    "Nehemiah",
    "Esther",
    "Job",
    "Psalms",
    "Proverbs",
    "Ecclesiastes",
    "Song of Solomon",
    "Isaiah",
    "Jeremiah",
    "Lamentations",
    "Ezekiel",
    "Daniel",
    "Hosea",
    "Joel",
    "Amos",
    "Obadiah",
    "Jonah",
    "Micah",
    "Nahum",
    "Habakkuk",
    "Zephaniah",
    "Haggai",
    "Zechariah",
    "Malachi",
    "Matthew",
    "Mark",
    "Luke",
    "John",
    "Acts",
    "Romans",
    "1 Corinthians",
    "2 Corinthians",
    "Galatians",
    "Ephesians",
    "Philippians",
    "Colossians",
    "1 Thessalonians",
    "2 Thessalonians",
    "1 Timothy",
    "2 Timothy",
    "Titus",
    "Philemon",
    "Hebrews",
    "James",
    "1 Peter",
    "2 Peter",
    "1 John",
    "2 John",
    "3 John",
    "Jude",
    "Revelation",
]

SCRIPTURE_PATH = Path(__file__).resolve().parent.parent / "scripture.csv"


class ScriptureData:
    def __init__(self):
        self.verse_lookup: Dict[Tuple[str, int, str, int], str] = {}
        self.chapter_counts: Dict[Tuple[str, int], int] = {}
        self.books_meta: List[Dict] = []
        self.versions: List[str] = []


@lru_cache()
def load_scripture_data() -> ScriptureData:
    data = ScriptureData()
    if not SCRIPTURE_PATH.exists():
        return data

    version_set = set()
    chapter_max: Dict[Tuple[str, int], int] = {}
    seen_books = set()

    with SCRIPTURE_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            book = row["CanonBookName"].strip()
            chapter = int(row["CanonBookChapter"])
            verse_num = int(row["CanonChapterVerse"])
            version = row.get("Version", "KJV").strip() or "KJV"
            text = row.get("Text", "").strip()
            data.verse_lookup[(book, chapter, version, verse_num)] = text
            version_set.add(version)
            chapter_max[(book, chapter)] = max(chapter_max.get((book, chapter), 0), verse_num)
            seen_books.add(book)

    order_map = {name: idx + 1 for idx, name in enumerate(CANONICAL_ORDER)}
    books_ordered = sorted(seen_books, key=lambda b: order_map.get(b, 999))
    for book in books_ordered:
        order = order_map.get(book, len(CANONICAL_ORDER) + 1)
        testament = "Old" if order <= 39 else "New"
        data.books_meta.append(
            {"canon_book_name": book, "canonical_order": order, "testament": testament}
        )

    data.chapter_counts = chapter_max
    data.versions = sorted(version_set)
    return data


def get_books_meta() -> List[Dict]:
    return load_scripture_data().books_meta


def get_versions() -> List[str]:
    return load_scripture_data().versions


def get_chapter_count(book: str, chapter: int) -> int:
    return load_scripture_data().chapter_counts.get((book, chapter), 0)


def get_passage_text(book: str, chapter: int, start: int, end: int, version: str) -> str:
    data = load_scripture_data()
    verses = []
    for verse_num in range(start, end + 1):
        text = data.verse_lookup.get((book, chapter, version, verse_num))
        if text is None:
            return ""
        verses.append(f"{verse_num} {text}".strip())
    return " ".join(verses)
