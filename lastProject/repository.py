import os
import sqlite3
from datetime import datetime

DATABASE_NAME = "games.db"


class GameRepository:
    def __init__(self, base_dir):
        self.db_path = os.path.join(base_dir, DATABASE_NAME)

    def initialize(self):
        self._create_schema()

    def _get_connection(self, row_factory=None):
        conn = sqlite3.connect(self.db_path)
        if row_factory:
            conn.row_factory = row_factory
        return conn

    def _create_schema(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(
                """
                CREATE TABLE IF NOT EXISTS master_games (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    release_year INTEGER NOT NULL,
                    platforms TEXT NOT NULL,
                    genres TEXT NOT NULL,
                    developer TEXT NOT NULL DEFAULT '',
                    publisher TEXT NOT NULL DEFAULT '',
                    franchise TEXT,
                    release_date TEXT NOT NULL,
                    platform_category TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    popularity INTEGER NOT NULL DEFAULT 0,
                    screenshots TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS user_games (
                    game_id INTEGER PRIMARY KEY,
                    owned INTEGER NOT NULL DEFAULT 0,
                    played INTEGER NOT NULL DEFAULT 0,
                    completion_pct INTEGER NOT NULL DEFAULT 0,
                    main_story_completed INTEGER NOT NULL DEFAULT 0,
                    hours_played REAL NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    completion_year TEXT NOT NULL DEFAULT '',
                    platforms_played TEXT NOT NULL DEFAULT '',
                    last_updated TEXT NOT NULL,
                    FOREIGN KEY(game_id) REFERENCES master_games(id)
                );
                """
            )
            conn.commit()


    def list_master_games(self, filters):
        query, params = self._build_master_query(filters, include_order=True)
        with self._get_connection(sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def list_library_games(self, filters):
        query, params = self._build_master_query(filters, include_order=False)
        base_filter = (
            " AND (COALESCE(u.owned, 0) = 1 "
            "OR COALESCE(u.played, 0) = 1 "
            "OR COALESCE(u.completion_pct, 0) > 0 "
            "OR COALESCE(u.main_story_completed, 0) = 1)"
        )
        query += base_filter
        query = self._apply_order(query, filters)
        with self._get_connection(sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def list_platforms(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT platforms FROM master_games")
            rows = cursor.fetchall()
        platforms = set()
        for (platforms_text,) in rows:
            if not platforms_text:
                continue
            for platform in platforms_text.split(","):
                platform = platform.strip()
                if platform:
                    platforms.add(platform)
        return sorted(platforms, key=lambda value: value.lower())

    def get_game(self, game_id):
        with self._get_connection(sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT m.*, COALESCE(u.owned, 0) AS owned,
                       COALESCE(u.played, 0) AS played,
                       COALESCE(u.completion_pct, 0) AS completion_pct,
                       COALESCE(u.hours_played, 0) AS hours_played,
                       COALESCE(u.notes, '') AS notes,
                       COALESCE(u.completion_year, '') AS completion_year,
                       COALESCE(u.platforms_played, '') AS platforms_played,
                       COALESCE(u.main_story_completed, 0) AS main_story_completed,
                       u.last_updated AS last_updated
                FROM master_games m
                LEFT JOIN user_games u ON m.id = u.game_id
                WHERE m.id = ?
                """,
                (game_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def upsert_user_game(
        self,
        game_id,
        owned,
        played,
        main_story_completed,
        completion_pct,
        hours_played,
        notes,
        completion_year,
        platforms_played,
    ):
        timestamp = datetime.utcnow().isoformat(timespec="seconds")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_games (game_id, owned, played, completion_pct,
                                        main_story_completed, hours_played, notes,
                                        completion_year, platforms_played, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id) DO UPDATE SET
                    owned = excluded.owned,
                    played = excluded.played,
                    completion_pct = excluded.completion_pct,
                    main_story_completed = excluded.main_story_completed,
                    hours_played = excluded.hours_played,
                    notes = excluded.notes,
                    completion_year = excluded.completion_year,
                    platforms_played = excluded.platforms_played,
                    last_updated = excluded.last_updated
                """,
                (
                    game_id,
                    int(owned),
                    int(played),
                    int(completion_pct),
                    int(main_story_completed),
                    float(hours_played),
                    notes,
                    completion_year,
                    platforms_played,
                    timestamp,
                ),
            )
            conn.commit()

    def stats_summary(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM master_games")
            total_games = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM user_games WHERE owned = 1")
            owned = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM user_games WHERE played = 1")
            played = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM user_games WHERE completion_pct > 0")
            completed = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM user_games WHERE completion_pct = 100")
            full = cursor.fetchone()[0]
            ratio = (completed / total_games) * 100 if total_games else 0
            return {
                "total_games": total_games,
                "owned": owned,
                "played": played,
                "completed": completed,
                "full": full,
                "completion_ratio": ratio,
            }

    def _build_master_query(self, filters, include_order):
        query = (
            "SELECT m.*, COALESCE(u.owned, 0) AS owned, "
            "COALESCE(u.played, 0) AS played, "
            "COALESCE(u.completion_pct, 0) AS completion_pct, "
            "COALESCE(u.hours_played, 0) AS hours_played, "
            "COALESCE(u.notes, '') AS notes, "
            "COALESCE(u.completion_year, '') AS completion_year, "
            "COALESCE(u.platforms_played, '') AS platforms_played, "
            "COALESCE(u.main_story_completed, 0) AS main_story_completed, "
            "u.last_updated AS last_updated "
            "FROM master_games m "
            "LEFT JOIN user_games u ON m.id = u.game_id "
            "WHERE 1 = 1"
        )
        params = []

        search = filters.get("search")
        if search:
            query += " AND m.title LIKE ?"
            params.append(f"%{search}%")

        platform = filters.get("platform")
        if platform:
            query += " AND m.platforms LIKE ?"
            params.append(f"%{platform}%")

        genre = filters.get("genre")
        if genre:
            query += " AND m.genres LIKE ?"
            params.append(f"%{genre}%")

        publisher = filters.get("publisher")
        if publisher:
            query += " AND m.publisher LIKE ?"
            params.append(f"%{publisher}%")

        developer = filters.get("developer")
        if developer:
            query += " AND m.developer LIKE ?"
            params.append(f"%{developer}%")

        year_from = filters.get("year_from")
        if year_from is not None:
            query += " AND m.release_year >= ?"
            params.append(year_from)

        year_to = filters.get("year_to")
        if year_to is not None:
            query += " AND m.release_year <= ?"
            params.append(year_to)

        if filters.get("owned_only"):
            query += " AND COALESCE(u.owned, 0) = 1"

        if filters.get("played_only"):
            query += " AND COALESCE(u.played, 0) = 1"

        if filters.get("main_story_only"):
            query += " AND COALESCE(u.main_story_completed, 0) = 1"

        if filters.get("completed_only"):
            query += " AND COALESCE(u.completion_pct, 0) > 0"

        if filters.get("full_only"):
            query += " AND COALESCE(u.completion_pct, 0) = 100"

        if include_order:
            query = self._apply_order(query, filters)
        return query, params

    def _apply_order(self, query, filters):
        sort_by = filters.get("sort_by") or "popularity"
        sort_dir = filters.get("sort_dir") or "desc"
        order_columns = {
            "title": "m.title",
            "release_year": "m.release_year",
            "popularity": "m.popularity",
        }
        order_column = order_columns.get(sort_by, "m.popularity")
        direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
        return f"{query} ORDER BY {order_column} {direction}"
