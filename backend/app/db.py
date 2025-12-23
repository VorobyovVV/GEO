import psycopg2
from app.core.config import get_settings


def get_db_conn():
    """Open a new database connection using environment variables."""
    settings = get_settings()
    return psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )
import os
import psycopg2
import psycopg2.extras


def get_db_conn():
    """Open a new database connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "geodb"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
    )


def refresh_avg_rating(conn, place_id: int) -> float:
    """Recalculate and update avg_rating after rating changes."""
    sql = """
        WITH stats AS (
            SELECT AVG(rating) AS avg_rating
            FROM place_ratings
            WHERE place_id = %s
        )
        UPDATE places
        SET avg_rating = stats.avg_rating
        FROM stats
        WHERE id = %s
        RETURNING COALESCE(stats.avg_rating, 0) AS avg_rating;
    """
    with conn.cursor() as cur:
        cur.execute(sql, (place_id, place_id))
        row = cur.fetchone()
    return float(row[0]) if row else 0.0

