from typing import Optional, Dict, Any

import psycopg2.extras


def get_user_by_username(conn, username: str) -> Optional[Dict[str, Any]]:
    sql = "SELECT id, username, password_hash, role, created_at FROM users WHERE username = %s"
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (username,))
        row = cur.fetchone()
        if row:
            return dict(row)
    return None


def get_user_by_id(conn, user_id: int) -> Optional[Dict[str, Any]]:
    sql = "SELECT id, username, password_hash, role, created_at FROM users WHERE id = %s"
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (user_id,))
        row = cur.fetchone()
        if row:
            return dict(row)
    return None

