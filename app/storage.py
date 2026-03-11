import os
import sqlite3
import json
from datetime import datetime
from typing import Optional
from app.models import Promotion


DB_PATH = os.environ.get("DB_PATH", "promotions.db")


class Storage:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS promotions (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id      INTEGER UNIQUE,
                    destination     TEXT,
                    origin_city     TEXT,
                    origin_code     TEXT,
                    destination_city TEXT,
                    destination_code TEXT,
                    airline         TEXT,
                    program         TEXT,
                    cabin_class     TEXT,
                    miles_per_segment INTEGER,
                    outbound_dates  TEXT,
                    return_dates    TEXT,
                    raw_text        TEXT,
                    collected_at    TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_destination ON promotions(destination)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_airline ON promotions(airline)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_program ON promotions(program)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_miles ON promotions(miles_per_segment)")

    def save(self, promo: Promotion) -> Optional[int]:
        """Insert a promotion, ignore duplicates. Returns new row id or None."""
        with self._conn() as conn:
            try:
                cur = conn.execute("""
                    INSERT OR IGNORE INTO promotions
                        (message_id, destination, origin_city, origin_code,
                         destination_city, destination_code, airline, program,
                         cabin_class, miles_per_segment, outbound_dates, return_dates,
                         raw_text, collected_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    promo.message_id,
                    promo.destination,
                    promo.origin_city,
                    promo.origin_code,
                    promo.destination_city,
                    promo.destination_code,
                    promo.airline,
                    promo.program,
                    promo.cabin_class,
                    promo.miles_per_segment,
                    json.dumps(promo.outbound_dates),
                    json.dumps(promo.return_dates),
                    promo.raw_text,
                    promo.collected_at.isoformat() if promo.collected_at else datetime.utcnow().isoformat(),
                ))
                return cur.lastrowid if cur.rowcount else None
            except sqlite3.Error:
                return None

    def save_many(self, promos: list[Promotion]) -> int:
        return sum(1 for p in promos if self.save(p) is not None)

    def _row_to_promo(self, row: sqlite3.Row) -> Promotion:
        return Promotion(
            id=row["id"],
            message_id=row["message_id"],
            destination=row["destination"],
            origin_city=row["origin_city"],
            origin_code=row["origin_code"],
            destination_city=row["destination_city"],
            destination_code=row["destination_code"],
            airline=row["airline"],
            program=row["program"],
            cabin_class=row["cabin_class"],
            miles_per_segment=row["miles_per_segment"],
            outbound_dates=json.loads(row["outbound_dates"]),
            return_dates=json.loads(row["return_dates"]),
            raw_text=row["raw_text"],
            collected_at=datetime.fromisoformat(row["collected_at"]),
        )

    def get_all(
        self,
        destination: Optional[str] = None,
        airline: Optional[str] = None,
        program: Optional[str] = None,
        max_miles: Optional[int] = None,
        origin_code: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Promotion]:
        where_clauses = []
        params: list = []

        if destination:
            where_clauses.append("LOWER(destination) LIKE ?")
            params.append(f"%{destination.lower()}%")
        if airline:
            where_clauses.append("LOWER(airline) LIKE ?")
            params.append(f"%{airline.lower()}%")
        if program:
            where_clauses.append("LOWER(program) LIKE ?")
            params.append(f"%{program.lower()}%")
        if max_miles:
            where_clauses.append("miles_per_segment <= ?")
            params.append(max_miles)
        if origin_code:
            where_clauses.append("UPPER(origin_code) = ?")
            params.append(origin_code.upper())

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        params += [limit, offset]

        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM promotions {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?",
                params,
            ).fetchall()
        return [self._row_to_promo(r) for r in rows]

    def get_by_id(self, promo_id: int) -> Optional[Promotion]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM promotions WHERE id = ?", (promo_id,)).fetchone()
        return self._row_to_promo(row) if row else None

    def count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM promotions").fetchone()[0]
