import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from src.core.config import APPDATA_DIR

logger = logging.getLogger(__name__)

DB_PATH = APPDATA_DIR / "profilepull.db"

class Database:
    def __init__(self):
        self.db_path = str(DB_PATH)
        self.init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE,
                platform TEXT NOT NULL,
                profile_url TEXT,
                local_path TEXT,
                video_count INTEGER DEFAULT 0,
                first_downloaded_at TEXT,
                last_downloaded_at TEXT
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                download_id INTEGER REFERENCES downloads(id),
                video_id TEXT,
                title TEXT,
                filename TEXT,
                view_count INTEGER,
                view_folder TEXT,
                downloaded_at TEXT,
                is_short INTEGER DEFAULT 0
            );
            """)
            conn.commit()
            
            # Migrate existing tables seamlessly without losing historical user data
            try:
                cursor.execute("ALTER TABLE videos ADD COLUMN is_short INTEGER DEFAULT 0;")
                conn.commit()
            except sqlite3.OperationalError:
                pass # Column already exists
                
        except Exception as e:
            logger.error(f"Failed to init DB: {e}")
        finally:
            conn.close()

    def check_duplicate(self, username: str, platform: str) -> bool:
        """Returns True if user exists from a DIFFERENT platform."""
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT platform FROM downloads WHERE username = ? COLLATE NOCASE LIMIT 1", (username,))
            result = cursor.fetchone()
            if result:
                existing_platform = result[0]
                if existing_platform.lower() != platform.lower():
                    return True  # True means a duplicate from a different platform exists
            return False
        finally:
            conn.close()

    def get_or_create_download(self, username: str, platform: str, profile_url: str, local_path: str) -> int:
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM downloads WHERE username = ? AND platform = ? COLLATE NOCASE", (username, platform))
            result = cursor.fetchone()
            now_str = datetime.now().isoformat()
            if result:
                download_id = result[0]
                cursor.execute("UPDATE downloads SET last_downloaded_at = ?, local_path = ? WHERE id = ?", (now_str, local_path, download_id))
            else:
                cursor.execute("""
                    INSERT INTO downloads (username, platform, profile_url, local_path, first_downloaded_at, last_downloaded_at) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username, platform, profile_url, local_path, now_str, now_str))
                download_id = cursor.lastrowid
            conn.commit()
            return download_id
        finally:
            conn.close()

    def add_video(self, download_id: int, video_id: str, title: str, filename: str, view_count: int, view_folder: str, is_short: bool = False):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            # Check if video already exists
            cursor.execute("SELECT id FROM videos WHERE download_id = ? AND video_id = ?", (download_id, video_id))
            if not cursor.fetchone():
                now_str = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO videos (download_id, video_id, title, filename, view_count, view_folder, downloaded_at, is_short)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (download_id, video_id, title, filename, view_count, view_folder, now_str, 1 if is_short else 0))
                # Update download count
                cursor.execute("UPDATE downloads SET video_count = video_count + 1 WHERE id = ?", (download_id,))
                conn.commit()
        finally:
            conn.close()

    def get_all_videos_for_download(self, download_id: int) -> list:
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos WHERE download_id = ?", (download_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def update_video_view_count(self, video_db_id: int, new_view_count: int, new_folder: str):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE videos SET view_count = ?, view_folder = ? WHERE id = ?", (new_view_count, new_folder, video_db_id))
            conn.commit()
        finally:
            conn.close()

    def get_all_downloads(self) -> list:
        conn = self._get_conn()
        try:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM downloads ORDER BY last_downloaded_at DESC")
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def clear_history(self):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM videos")
            cursor.execute("DELETE FROM downloads")
            conn.commit()
        finally:
            conn.close()

    def delete_download(self, download_id: int):
        conn = self._get_conn()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM videos WHERE download_id = ?", (download_id,))
            cursor.execute("DELETE FROM downloads WHERE id = ?", (download_id,))
            conn.commit()
        finally:
            conn.close()

db = Database()
