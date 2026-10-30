import sqlite3
import os
from datetime import datetime
from app.config import Config

def init_db():
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
    with sqlite3.connect(Config.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                api_key TEXT,
                email TEXT,
                password TEXT,
                workspace TEXT,
                owner_id TEXT,
                key_name TEXT,
                used_tor BOOLEAN,
                ip_used TEXT,
                status TEXT NOT NULL,
                error TEXT
            )
        """)
        # Ensure password column exists in older database files
        cursor.execute("PRAGMA table_info(api_keys)")
        columns = [col[1] for col in cursor.fetchall()]
        if "password" not in columns:
            cursor.execute("ALTER TABLE api_keys ADD COLUMN password TEXT")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mail_credentials (
                email TEXT PRIMARY KEY,
                password TEXT,
                created_at TEXT
            )
        """)
        conn.commit()

def save_mail_credential(email: str, password: str):
    init_db()
    if not email or not password:
        return
    with sqlite3.connect(Config.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO mail_credentials (email, password, created_at)
            VALUES (?, ?, ?)
        """, (email.lower().strip(), password, datetime.utcnow().isoformat() + "Z"))
        conn.commit()

def get_password_for_email(email: str) -> str:
    if not email:
        return None
    init_db()
    with sqlite3.connect(Config.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM mail_credentials WHERE email = ?", (email.lower().strip(),))
        row = cursor.fetchone()
        return row[0] if row else None

def save_key_record(
    status: str,
    api_key: str = None,
    email: str = None,
    password: str = None,
    workspace: str = None,
    owner_id: str = None,
    key_name: str = None,
    used_tor: bool = False,
    ip_used: str = None,
    error: str = None
) -> int:
    init_db()
    if not password and email:
        password = get_password_for_email(email)

    with sqlite3.connect(Config.DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO api_keys (
                timestamp, api_key, email, password, workspace, owner_id,
                key_name, used_tor, ip_used, status, error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat() + "Z",
            api_key,
            email,
            password,
            workspace,
            owner_id,
            key_name,
            1 if used_tor else 0,
            ip_used,
            status,
            error
        ))
        conn.commit()
        return cursor.lastrowid

def get_recent_keys(limit: int = 50, status: str = None) -> list:
    init_db()
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if status:
            cursor.execute("""
                SELECT id, timestamp, api_key, email, password, workspace, owner_id,
                       key_name, used_tor, ip_used, status, error
                FROM api_keys
                WHERE status = ?
                ORDER BY id DESC
                LIMIT ?
            """, (status, limit))
        else:
            cursor.execute("""
                SELECT id, timestamp, api_key, email, password, workspace, owner_id,
                       key_name, used_tor, ip_used, status, error
                FROM api_keys
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
