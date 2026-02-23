"""Additional tests for card image cache behavior."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime

from utils import card_images


def test_card_image_cache_migrates_face_index_column(tmp_path):
    """Existing databases without face_index should be migrated safely."""
    cache_dir = tmp_path / "cache"
    db_path = cache_dir / "images.db"
    cache_dir.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE card_images (
                uuid TEXT NOT NULL,
                name TEXT NOT NULL,
                set_code TEXT,
                collector_number TEXT,
                image_size TEXT NOT NULL,
                file_path TEXT NOT NULL,
                downloaded_at TEXT NOT NULL,
                scryfall_uri TEXT,
                artist TEXT
            )
            """)
        conn.execute(
            """
            INSERT INTO card_images (
                uuid, name, set_code, collector_number, image_size, file_path, downloaded_at,
                scryfall_uri, artist
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "uuid-old",
                "Legacy Entry",
                "SET",
                "001",
                "normal",
                "legacy/path.jpg",
                datetime.now(card_images.UTC).isoformat(),
                None,
                None,
            ),
        )
        conn.commit()

    cache = card_images.CardImageCache(cache_dir=cache_dir, db_path=db_path)
    assert cache.db_path.exists()  # ensure initialization succeeded

    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(card_images)")}
        assert "face_index" in columns
        migrated_row = conn.execute("SELECT uuid, face_index, name FROM card_images").fetchone()

    assert migrated_row == ("uuid-old", 0, "Legacy Entry")


def test_resolves_windows_style_relative_paths(tmp_path):
    """Backslash-separated cache entries should be normalized and resolved."""
    cache_dir = tmp_path / "cache"
    db_path = cache_dir / "images.db"
    cache = card_images.CardImageCache(cache_dir=cache_dir, db_path=db_path)

    expected_path = cache.cache_dir / "normal" / "uuid-win.png"
    expected_path.write_bytes(b"image")

    with sqlite3.connect(cache.db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO card_images (
                uuid, face_index, name, set_code, collector_number, image_size, file_path,
                downloaded_at, scryfall_uri, artist
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "uuid-win",
                0,
                "Windows Path",
                "SET",
                "007",
                "normal",
                "normal\\uuid-win.png",
                datetime.now(card_images.UTC).isoformat(),
                None,
                None,
            ),
        )
        conn.commit()

    resolved = cache.get_image_by_uuid("uuid-win", size="normal")
    assert resolved == expected_path


def test_is_bulk_data_outdated_respects_cached_metadata(tmp_path, monkeypatch):
    """Bulk metadata comparison should rely on cached DB entries when present."""
    cache_dir = tmp_path / "card_images"
    bulk_path = cache_dir / "bulk_data.json"
    bulk_path.parent.mkdir(parents=True, exist_ok=True)
    bulk_path.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(card_images, "BULK_DATA_CACHE", bulk_path, raising=False)

    cache = card_images.CardImageCache(cache_dir=cache_dir, db_path=cache_dir / "images.db")
    downloader = card_images.BulkImageDownloader(cache)

    metadata = {
        "updated_at": "2024-01-01T00:00:00Z",
        "download_uri": "http://example.com/bulk",
    }
    monkeypatch.setattr(downloader, "_fetch_bulk_metadata", lambda: metadata)

    with sqlite3.connect(cache.db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO bulk_data_meta (id, downloaded_at, total_cards, bulk_data_uri)
            VALUES (1, ?, ?, ?)
            """,
            (metadata["updated_at"], 0, metadata["download_uri"]),
        )
        conn.commit()

    is_outdated, returned_metadata = downloader.is_bulk_data_outdated()

    assert is_outdated is False
    assert returned_metadata["download_uri"] == metadata["download_uri"]


def test_get_image_path_calls_db_only_once_for_same_name(tmp_path, monkeypatch):
    """get_image_path() should hit _get_image_path_from_db only once per unique key."""
    cache = card_images.CardImageCache(
        cache_dir=tmp_path / "cache", db_path=tmp_path / "cache" / "images.db"
    )
    image_file = cache.cache_dir / "normal" / "test.jpg"
    image_file.parent.mkdir(parents=True, exist_ok=True)
    image_file.write_bytes(b"fake")

    call_count = 0
    original_from_db = cache._get_image_path_from_db

    def counting_from_db(card_name: str, size: str):
        nonlocal call_count
        call_count += 1
        return original_from_db(card_name, size)

    monkeypatch.setattr(cache, "_get_image_path_from_db", counting_from_db)

    # Seed the DB directly so the first lookup succeeds
    cache.add_image(
        uuid="uuid-once",
        name="Test Card",
        set_code="SET",
        collector_number="001",
        image_size="normal",
        file_path=image_file,
    )
    # Clear path cache so the first real call goes to DB
    cache._path_cache.clear()

    result1 = cache.get_image_path("Test Card", "normal")
    result2 = cache.get_image_path("Test Card", "normal")

    assert result1 == result2 == image_file
    assert call_count == 1, f"Expected DB called once, got {call_count}"


def test_get_image_path_returns_path_after_add_image_when_initial_miss(tmp_path):
    """After a None lookup, add_image() must invalidate the cache so next call returns the path."""
    cache = card_images.CardImageCache(
        cache_dir=tmp_path / "cache", db_path=tmp_path / "cache" / "images.db"
    )

    # First lookup returns None (card not yet downloaded)
    result_before = cache.get_image_path("New Card", "normal")
    assert result_before is None

    # Simulate download completing
    image_file = cache.cache_dir / "normal" / "uuid-new.jpg"
    image_file.parent.mkdir(parents=True, exist_ok=True)
    image_file.write_bytes(b"fake")
    cache.add_image(
        uuid="uuid-new",
        name="New Card",
        set_code="SET",
        collector_number="002",
        image_size="normal",
        file_path=image_file,
    )

    # Lookup after add_image() must return the path
    result_after = cache.get_image_path("New Card", "normal")
    assert result_after == image_file


def test_get_image_path_is_thread_safe(tmp_path):
    """Concurrent calls to get_image_path() for the same key must not raise."""
    cache = card_images.CardImageCache(
        cache_dir=tmp_path / "cache", db_path=tmp_path / "cache" / "images.db"
    )
    image_file = cache.cache_dir / "normal" / "uuid-thread.jpg"
    image_file.parent.mkdir(parents=True, exist_ok=True)
    image_file.write_bytes(b"fake")
    cache.add_image(
        uuid="uuid-thread",
        name="Thread Card",
        set_code="SET",
        collector_number="003",
        image_size="normal",
        file_path=image_file,
    )
    cache._path_cache.clear()

    results: list[object] = []
    errors: list[Exception] = []

    def worker():
        try:
            results.append(cache.get_image_path("Thread Card", "normal"))
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Thread errors: {errors}"
    assert all(r == image_file for r in results)
