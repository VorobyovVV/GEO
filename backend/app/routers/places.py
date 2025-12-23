import json
from typing import List, Any, Dict, Optional

import psycopg2.extras
from fastapi import APIRouter, HTTPException, Query

from app.db import get_db_conn
from app.schemas import (
    PlaceCreate,
    PlaceUpdate,
    RateRequest,
    PolygonRequest,
    DistanceResponse,
    ReviewCreate,
)
from app.services.places import row_to_place, refresh_avg_rating

router = APIRouter(prefix="/places", tags=["places"])


@router.post("", response_model=Dict[str, Any])
def create_place(payload: PlaceCreate):
    sql = """
        INSERT INTO places (name, category, description, address, tags, hours, geom)
        VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
        RETURNING id, name, category, description, address, tags, avg_rating, hours,
                  ST_AsGeoJSON(geom) AS geometry, created_at;
    """
    params = (
        payload.name,
        payload.category,
        payload.description,
        payload.address,
        payload.tags or [],
        psycopg2.extras.Json(payload.hours) if payload.hours is not None else None,
        payload.lon,
        payload.lat,
    )
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    return row_to_place(row)


@router.get("", response_model=List[Dict[str, Any]])
def list_places(
    category: Optional[str] = None,
    tag: Optional[str] = Query(None, description="Filter by a tag"),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    clauses = []
    params: List[Any] = []
    if category:
        clauses.append("category = %s")
        params.append(category)
    if tag:
        clauses.append("%s = ANY(tags)")
        params.append(tag)
    if min_rating is not None:
        clauses.append("avg_rating >= %s")
        params.append(min_rating)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT id, name, category, description, address, tags, avg_rating, hours,
               ST_AsGeoJSON(geom) AS geometry, created_at
        FROM places
        {where}
        ORDER BY id DESC
        LIMIT %s OFFSET %s;
    """
    params.extend([limit, offset])
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [row_to_place(r) for r in rows]


@router.get("/nearby", response_model=List[Dict[str, Any]])
def nearby_places(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    limit: int = Query(10, ge=1, le=100),
):
    sql = """
        SELECT id, name, category, description, address, tags, avg_rating, hours,
               ST_AsGeoJSON(geom) AS geometry,
               ST_DistanceSphere(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) AS distance_m,
               created_at
        FROM places
        ORDER BY distance_m
        LIMIT %s;
    """
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (lon, lat, limit))
        rows = cur.fetchall()
    return [row_to_place(r) | {"distance_m": float(r["distance_m"])} for r in rows]


@router.get("/{place_id}", response_model=Dict[str, Any])
def get_place(place_id: int):
    sql = """
        SELECT id, name, category, description, address, tags, avg_rating, hours,
               ST_AsGeoJSON(geom) AS geometry, created_at
        FROM places
        WHERE id = %s;
    """
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (place_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Place not found")
    return row_to_place(row)


@router.put("/{place_id}", response_model=Dict[str, Any])
def update_place(place_id: int, payload: PlaceUpdate):
    updates = []
    params: List[Any] = []
    if payload.name is not None:
        updates.append("name = %s")
        params.append(payload.name)
    if payload.category is not None:
        updates.append("category = %s")
        params.append(payload.category)
    if payload.description is not None:
        updates.append("description = %s")
        params.append(payload.description)
    if payload.address is not None:
        updates.append("address = %s")
        params.append(payload.address)
    if payload.tags is not None:
        updates.append("tags = %s")
        params.append(payload.tags)
    if payload.hours is not None:
        updates.append("hours = %s")
        params.append(psycopg2.extras.Json(payload.hours))
    if payload.lat is not None and payload.lon is not None:
        updates.append("geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326)")
        params.extend([payload.lon, payload.lat])
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    sql = f"""
        UPDATE places
        SET {', '.join(updates)}
        WHERE id = %s
        RETURNING id, name, category, description, address, tags, avg_rating, hours,
                  ST_AsGeoJSON(geom) AS geometry, created_at;
    """
    params.append(place_id)
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Place not found")
    return row_to_place(row)


@router.delete("/{place_id}")
def delete_place(place_id: int):
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM places WHERE id = %s RETURNING id;", (place_id,))
        deleted = cur.fetchone()
        if not deleted:
            raise HTTPException(status_code=404, detail="Place not found")
    return {"status": "deleted", "id": place_id}


@router.get("/within", response_model=List[Dict[str, Any]])
def places_within_radius(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_m: float = Query(1000, gt=0, le=50_000),
):
    sql = """
        SELECT id, name, category, description, address, tags, avg_rating, hours,
               ST_AsGeoJSON(geom) AS geometry, created_at
        FROM places
        WHERE ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s
        );
    """
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (lon, lat, radius_m))
        rows = cur.fetchall()
    return [row_to_place(r) for r in rows]


@router.post("/within-polygon", response_model=List[Dict[str, Any]])
def places_within_polygon(payload: PolygonRequest):
    sql = """
        SELECT id, name, category, description, address, tags, avg_rating, hours,
               ST_AsGeoJSON(geom) AS geometry, created_at
        FROM places
        WHERE ST_Within(
            geom,
            ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
        );
    """
    geojson_str = json.dumps(payload.geojson)
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (geojson_str,))
        rows = cur.fetchall()
    return [row_to_place(r) for r in rows]


@router.post("/{place_id}/rate")
def rate_place(place_id: int, payload: RateRequest):
    # backward compatible: store in reviews
    upsert_sql = """
        INSERT INTO reviews (place_id, user_id, rating, text)
        VALUES (%s, %s, %s, %s)
        RETURNING place_id;
    """
    try:
        with get_db_conn() as conn, conn.cursor() as cur:
            cur.execute(upsert_sql, (place_id, None, payload.rating, payload.comment))
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Place not found")
            avg_rating = refresh_avg_rating(conn, place_id)
            conn.commit()
    except psycopg2.errors.ForeignKeyViolation:
        raise HTTPException(status_code=404, detail="Place not found")
    return {"place_id": place_id, "avg_rating": avg_rating}


@router.post("/{place_id}/reviews")
def create_review(place_id: int, payload: ReviewCreate):
    insert_sql = """
        INSERT INTO reviews (place_id, user_id, rating, text)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
    """
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(insert_sql, (place_id, None, payload.rating, payload.text))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Place not found")
        avg_rating = refresh_avg_rating(conn, place_id)
        conn.commit()
    return {"place_id": place_id, "avg_rating": avg_rating}


@router.get("/{place_id}/distance", response_model=DistanceResponse)
def place_distance(
    place_id: int,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    sql = """
        SELECT
            id,
            ST_DistanceSphere(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) AS distance_m
        FROM places
        WHERE id = %s;
    """
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (lon, lat, place_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Place not found")
    return DistanceResponse(id=row["id"], distance_m=float(row["distance_m"]))


@router.get("/stats/by-category")
def stats_by_category():
    sql = """
        SELECT category, COUNT(*) AS count, AVG(avg_rating) AS avg_rating
        FROM places
        GROUP BY category
        ORDER BY count DESC;
    """
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return [
        {
            "category": r["category"],
            "count": int(r["count"]),
            "avg_rating": float(r["avg_rating"]) if r["avg_rating"] is not None else None,
        }
        for r in rows
    ]


@router.get("/tags", response_model=List[str])
def list_tags(search: Optional[str] = Query(None, min_length=1, description="ILIKE filter for tags")):
    base_sql = """
        SELECT DISTINCT tag
        FROM places
        CROSS JOIN UNNEST(tags) AS tag
    """
    params: List[Any] = []
    if search:
        base_sql += " WHERE tag ILIKE %s"
        params.append(f"%{search}%")
    base_sql += " ORDER BY tag ASC LIMIT 200;"
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute(base_sql, params)
        rows = cur.fetchall()
    return [r[0] for r in rows]


@router.get("/search", response_model=List[Dict[str, Any]])
def text_search(q: str = Query(..., min_length=2), limit: int = Query(20, ge=1, le=200)):
    sql = """
        SELECT id, name, category, description, address, tags, avg_rating, hours,
               ST_AsGeoJSON(geom) AS geometry, created_at
        FROM places
        WHERE name ILIKE %s OR address ILIKE %s OR description ILIKE %s
        ORDER BY id DESC
        LIMIT %s;
    """
    pattern = f"%{q}%"
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (pattern, pattern, pattern, limit))
        rows = cur.fetchall()
    return [row_to_place(r) for r in rows]


@router.get("/notifications")
def recent_notifications(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_m: float = Query(1000, gt=0, le=50_000),
):
    sql = """
        SELECT id, name, category, description, address, tags, avg_rating, hours,
               ST_AsGeoJSON(geom) AS geometry, created_at
        FROM places
        WHERE is_moderated = TRUE
          AND created_at > NOW() - INTERVAL '7 days'
          AND ST_DWithin(
            geom::geography,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
            %s
          )
        ORDER BY created_at DESC
        LIMIT 100;
    """
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (lon, lat, radius_m))
        rows = cur.fetchall()
    return [row_to_place(r) for r in rows]


@router.get("/export/geojson")
def export_geojson(bbox: str = Query(..., description="lon1,lat1,lon2,lat2")):
    try:
        lon1, lat1, lon2, lat2 = [float(x) for x in bbox.split(",")]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid bbox format, expected lon1,lat1,lon2,lat2")
    sql = """
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', json_agg(
                json_build_object(
                    'type', 'Feature',
                    'geometry', ST_AsGeoJSON(geom)::json,
                    'properties', json_build_object(
                        'id', id,
                        'name', name,
                        'category', category,
                        'address', address,
                        'tags', tags,
                        'avg_rating', avg_rating,
                        'created_at', created_at
                    )
                )
            )
        )
        FROM (
            SELECT * FROM places
            WHERE ST_Intersects(
                geom,
                ST_MakeEnvelope(%s, %s, %s, %s, 4326)
            )
        ) AS sub;
    """
    with get_db_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (lon1, lat1, lon2, lat2))
        row = cur.fetchone()
        return row[0] or {"type": "FeatureCollection", "features": []}


@router.get("/clustered")
def clustered(zoom: int = Query(12, ge=1, le=20)):
    # heuristic k by zoom
    k = max(1, min(30, int(zoom * 1.5)))
    sql = f"""
        WITH clusters AS (
            SELECT ST_ClusterKMeans(geom, %s) OVER () AS cid, id, name, category,
                   address, tags, avg_rating, hours, created_at, geom
            FROM places
        )
        SELECT cid,
               ST_AsGeoJSON(ST_Centroid(ST_Collect(geom))) AS geometry,
               COUNT(*) AS count
        FROM clusters
        GROUP BY cid;
    """
    with get_db_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(sql, (k,))
        rows = cur.fetchall()
    return [
        {
            "cluster_id": int(r["cid"]),
            "count": int(r["count"]),
            "geometry": json.loads(r["geometry"]),
        }
        for r in rows
    ]

