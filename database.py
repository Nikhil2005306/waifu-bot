# database.py

import sqlite3
from config import Config
from datetime import datetime

class Database:
    def __init__(self, db_path=Config.DB_PATH):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.setup()
        self.setup_profile_tables()  # ensure profile tables also exist

    # ---------------- Setup ----------------
    def setup(self):
        """Create tables if they don’t exist and ensure columns exist"""
        # Users table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language TEXT DEFAULT 'en',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                daily_crystals INTEGER DEFAULT 0,
                weekly_crystals INTEGER DEFAULT 0,
                monthly_crystals INTEGER DEFAULT 0,
                daily_claim TEXT,
                weekly_claim TEXT,
                monthly_claim TEXT,
                first_logged INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

        # Groups table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                chat_id INTEGER PRIMARY KEY,
                title TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

        # Logs table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                user_id INTEGER,
                chat_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

        # Ensure columns exist for legacy DBs
        for col in ["daily_claim", "weekly_claim", "monthly_claim", "first_logged"]:
            self._add_missing_column(col)

    def _add_missing_column(self, column_name):
        """Add column if it does not exist"""
        self.cursor.execute("PRAGMA table_info(users)")
        columns = [info[1] for info in self.cursor.fetchall()]
        if column_name not in columns:
            if column_name == "first_logged":
                self.cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} INTEGER DEFAULT 0")
            else:
                self.cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} TEXT")
            self.conn.commit()

    # ---------------- User Management ----------------
    def add_user(self, user_id, username=None, first_name=None):
        self.cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        """, (user_id, username, first_name))
        self.conn.commit()

    def is_first_logged(self, user_id):
        self.cursor.execute("SELECT first_logged FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] == 1 if row else False

    def set_first_logged(self, user_id):
        self.cursor.execute("UPDATE users SET first_logged = 1 WHERE user_id = ?", (user_id,))
        self.conn.commit()

    # ---------------- Crystal Management ----------------
    def add_crystals(self, user_id, **kwargs):
        """Add crystals to user (daily, weekly, monthly)"""
        for k, v in kwargs.items():
            if k in ["daily", "weekly", "monthly"]:
                col = f"{k}_crystals"
                self.cursor.execute(f"UPDATE users SET {col} = {col} + ? WHERE user_id = ?", (v, user_id))
        self.conn.commit()

    def get_crystals(self, user_id):
        """
        Return (daily, weekly, monthly, total, last_claim)
        last_claim is latest of daily_claim, weekly_claim, monthly_claim
        """
        self.cursor.execute("""
            SELECT daily_crystals, weekly_crystals, monthly_crystals,
                   daily_claim, weekly_claim, monthly_claim
            FROM users WHERE user_id=?
        """, (user_id,))
        row = self.cursor.fetchone()
        if not row:
            return (0, 0, 0, 0, None)
        daily, weekly, monthly, daily_c, weekly_c, monthly_c = row
        total = daily + weekly + monthly
        timestamps = [ts for ts in [daily_c, weekly_c, monthly_c] if ts]
        last_claim = max(timestamps) if timestamps else None
        return (daily, weekly, monthly, total, last_claim)

    def get_last_claim(self, user_id, claim_type):
        """Return ISO string of last claim for daily/weekly/monthly"""
        col = f"{claim_type}_claim"
        self.cursor.execute(f"SELECT {col} FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def update_last_claim(self, user_id, claim_type, time_iso):
        col = f"{claim_type}_claim"
        self.cursor.execute(f"UPDATE users SET {col} = ? WHERE user_id = ?", (time_iso, user_id))
        self.conn.commit()

    # ---------------- Group Management ----------------
    def add_group(self, chat_id, title):
        self.cursor.execute("""
            INSERT OR IGNORE INTO groups (chat_id, title)
            VALUES (?, ?)
        """, (chat_id, title))
        self.conn.commit()

    def get_total_groups(self):
        self.cursor.execute("SELECT COUNT(*) FROM groups")
        return self.cursor.fetchone()[0]

    # ---------------- Logging ----------------
    def log_event(self, event_type, user_id=None, chat_id=None, details=None):
        self.cursor.execute("""
            INSERT INTO logs (event_type, user_id, chat_id, details)
            VALUES (?, ?, ?, ?)
        """, (event_type, user_id, chat_id, details))
        self.conn.commit()

    # ---------------- Profile System ----------------
    def setup_profile_tables(self):
        """Create profile-related tables if they don’t exist"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                level INTEGER DEFAULT 1,
                rank TEXT DEFAULT 'Newbie',
                badge TEXT DEFAULT 'None',
                total_collected INTEGER DEFAULT 0,
                progress INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 0,
                global_position TEXT DEFAULT 'Unranked',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_rarities (
                user_id INTEGER,
                rarity TEXT,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, rarity),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        self.conn.commit()

    def get_user_profile(self, user_id):
        """Fetch user profile and rarities"""
        self.cursor.execute("""
            SELECT level, rank, badge, total_collected, progress, balance, global_position
            FROM user_profiles WHERE user_id = ?
        """, (user_id,))
        row = self.cursor.fetchone()

        if not row:
            return None

        profile = {
            "level": row[0],
            "rank": row[1],
            "badge": row[2],
            "total_collected": row[3],
            "progress": row[4],
            "balance": row[5],
            "global_position": row[6],
        }

        self.cursor.execute("SELECT rarity, count FROM user_rarities WHERE user_id = ?", (user_id,))
        rarities = {rarity: count for rarity, count in self.cursor.fetchall()}
        profile["rarities"] = rarities

        return profile

    def add_or_update_profile(self, user_id, **kwargs):
        """Insert or update user profile data"""
        # Default values if not provided
        defaults = {
            "level": 1,
            "rank": "Newbie",
            "badge": "None",
            "total_collected": 0,
            "progress": 0,
            "balance": 0,
            "global_position": "Unranked",
        }
        defaults.update(kwargs)

        self.cursor.execute("""
            INSERT INTO user_profiles (user_id, level, rank, badge, total_collected, progress, balance, global_position)
            VALUES (:user_id, :level, :rank, :badge, :total_collected, :progress, :balance, :global_position)
            ON CONFLICT(user_id) DO UPDATE SET
                level = excluded.level,
                rank = excluded.rank,
                badge = excluded.badge,
                total_collected = excluded.total_collected,
                progress = excluded.progress,
                balance = excluded.balance,
                global_position = excluded.global_position
        """, {"user_id": user_id, **defaults})
        self.conn.commit()

    def update_user_rarity(self, user_id, rarity, count=1):
        """Increment rarity count for a user"""
        self.cursor.execute("""
            INSERT INTO user_rarities (user_id, rarity, count)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, rarity) DO UPDATE SET
                count = count + excluded.count
        """, (user_id, rarity, count))
        self.conn.commit()

    # ---------- WAIFU CARDS SCHEMA ENSURER (add this) ----------
    def ensure_waifu_cards_schema(self):
        # Create table if not exists
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS waifu_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                anime TEXT,
                rarity TEXT,
                event TEXT,
                media_type TEXT,
                media_file TEXT,
                media_file_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

        # Ensure columns exist (for legacy DBs)
        self.cursor.execute("PRAGMA table_info(waifu_cards)")
        cols = {c[1] for c in self.cursor.fetchall()}

        # columns we want to guarantee
        wanted = [
            ("media_type", "TEXT"),
            ("media_file", "TEXT"),
            ("media_file_id", "TEXT"),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        ]
        for col_name, col_type in wanted:
            if col_name not in cols:
                self.cursor.execute(f"ALTER TABLE waifu_cards ADD COLUMN {col_name} {col_type}")
                self.conn.commit()


    def get_user_rarity_count(self, user_id: int, rarity: str) -> int:
        """
        Returns the number of waifu cards a user owns for a specific rarity.
        """
        self.cursor.execute("""
            SELECT SUM(amount) FROM user_waifus uw
            JOIN waifu_cards wc ON uw.waifu_id = wc.id
            WHERE uw.user_id = ? AND wc.rarity = ?
        """, (user_id, rarity))
        result = self.cursor.fetchone()
        return result[0] if result[0] is not None else 0

    # ---------------- Close ----------------
    def close(self):
        self.conn.close()
