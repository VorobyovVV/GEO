import json
from typing import Dict, Any

import psycopg2.extras


def row_to_place(row) -> Dict[str, Any]:
    """Convert DB row to dict for JSON response."""
    return {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "description": row.get("description"),
        "address": row.get("address"),
        "tags": row.get("tags") or [],
        "avg_rating": float(row["avg_rating"]) if row.get("avg_rating") is not None else None,
        "hours": row.get("hours"),
        "geometry": json.loads(row["geometry"]) if row.get("geometry") else None,
        "created_at": row.get("created_at"),
    }


def refresh_avg_rating(conn, place_id: int) -> float:
    """Recalculate and update avg_rating after rating changes (from reviews)."""
    sql = """
        WITH stats AS (
            SELECT AVG(rating) AS avg_rating
            FROM reviews
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

