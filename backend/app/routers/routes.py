import json
from typing import List, Any, Dict

import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_db_conn
from app.deps import get_current_user
from app.schemas import RouteCreate

router = APIRouter(prefix="/routes", tags=["routes"])


def _row_to_route(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "user_id": row["user_id"],
        "geometry": json.loads(row["geometry"]) if row.get("geometry") else None,
        "created_at": row.get("created_at"),
    }


@router.post("", response_model=Dict[str, Any])
def create_route(payload: RouteCreate, current_user=Depends(get_current_user)):
    if not payload.points or len(payload.points) < 2:
        raise HTTPException(status_code=400, detail="Route requires at least 2 points")
    line_geojson = json.dumps({"type": "LineString", "coordinates": payload.points})
    sql = """
        INSERT INTO routes (user_id, name, geom)
        VALUES (%s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
        RETURNING id, user_id, name, ST_AsGeoJSON(geom) AS geometry, created_at;
    """
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (current_user["id"], payload.name, line_geojson))
        row = cur.fetchone()
    return _row_to_route(row)


@router.get("", response_model=List[Dict[str, Any]])
def list_routes(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), current_user=Depends(get_current_user)):
    sql = """
        SELECT id, user_id, name, ST_AsGeoJSON(geom) AS geometry, created_at
        FROM routes
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s;
    """
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (current_user["id"], limit, offset))
        rows = cur.fetchall()
    return [_row_to_route(r) for r in rows]

