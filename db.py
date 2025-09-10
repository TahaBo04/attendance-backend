import os, datetime
from typing import List, Dict, Any, Optional
import psycopg

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL env var is required (Render Postgres / Neon / Supabase).")

def db_conn():
    return psycopg.connect(DB_URL, autocommit=True)

def db_init():
    with db_conn() as con, con.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS students(
            id SERIAL PRIMARY KEY,
            student_id TEXT UNIQUE,
            full_name TEXT,
            class TEXT,
            face_enc BYTEA
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance(
            id SERIAL PRIMARY KEY,
            student_id TEXT,
            timestamp TEXT,
            camera_id TEXT,
            status TEXT
        )""")

def get_students() -> List[Dict[str, Any]]:
    with db_conn() as con, con.cursor() as cur:
        cur.execute("SELECT student_id, full_name, face_enc FROM students ORDER BY full_name")
        rows = cur.fetchall()
    return [{"student_id": r[0], "full_name": r[1], "face_enc": r[2]} for r in rows]

def upsert_student(student_id: str, full_name: str, face_enc_bytes: bytes, class_name: Optional[str] = None):
    with db_conn() as con, con.cursor() as cur:
        cur.execute("""
        INSERT INTO students(student_id, full_name, class, face_enc)
        VALUES (%s,%s,%s,%s)
        ON CONFLICT (student_id) DO UPDATE
            SET full_name = EXCLUDED.full_name,
                class = EXCLUDED.class,
                face_enc = EXCLUDED.face_enc
        """, (student_id, full_name, class_name, face_enc_bytes))

def mark_attendance(student_id: str, timestamp_iso: str, camera_id: str, status: str):
    with db_conn() as con, con.cursor() as cur:
        cur.execute("""
        INSERT INTO attendance(student_id, timestamp, camera_id, status)
        VALUES (%s,%s,%s,%s)
        """, (student_id, timestamp_iso, camera_id, status))

def recent_attendance(student_id: str, within_minutes: int) -> bool:
    since = (datetime.datetime.utcnow() - datetime.timedelta(minutes=within_minutes)).isoformat()
    with db_conn() as con, con.cursor() as cur:
        cur.execute("""
        SELECT 1 FROM attendance
        WHERE student_id = %s AND timestamp >= %s
        LIMIT 1
        """, (student_id, since))
        return cur.fetchone() is not None

def list_today() -> List[Dict[str, Any]]:
    # UTC midnight
    today = datetime.datetime.utcnow().date().isoformat()
    with db_conn() as con, con.cursor() as cur:
        cur.execute("""
        SELECT a.student_id, s.full_name, a.timestamp, a.camera_id
        FROM attendance a
        LEFT JOIN students s ON s.student_id = a.student_id
        WHERE a.timestamp >= %s
        ORDER BY a.timestamp DESC
        """, (today,))
        rows = cur.fetchall()
    return [{"student_id": r[0], "full_name": r[1], "timestamp": r[2], "camera_id": r[3]} for r in rows]
