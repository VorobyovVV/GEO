from datetime import datetime
from typing import List, Optional, Any, Dict

from pydantic import BaseModel, Field, validator


class PlaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=2000)
    address: Optional[str] = Field(None, max_length=255)
    tags: List[str] = Field(default_factory=list)
    hours: Optional[Dict[str, Any]] = Field(None, description="Arbitrary JSON with working hours info")


class PlaceCreate(PlaceBase):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class PlaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=2000)
    address: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None
    hours: Optional[Dict[str, Any]] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)

    @validator("lat")
    def lat_requires_lon(cls, v, values):
        if v is not None and values.get("lon") is None:
            raise ValueError("Provide lon when updating lat")
        return v

    @validator("lon")
    def lon_requires_lat(cls, v, values):
        if v is not None and values.get("lat") is None:
            raise ValueError("Provide lat when updating lon")
        return v


class RateRequest(BaseModel):
    rating: float = Field(..., ge=0, le=5)
    comment: Optional[str] = Field(None, max_length=2000)


class PolygonRequest(BaseModel):
    geojson: Dict[str, Any] = Field(..., description="Polygon or MultiPolygon GeoJSON")


class DistanceResponse(BaseModel):
    id: int
    distance_m: float


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    role: Optional[str] = Field(None, description="Optional role (admin/user) when allowed")


class UserOut(BaseModel):
    id: int
    username: str
    created_at: Optional[datetime]
    role: Optional[str]


class ReviewCreate(BaseModel):
    rating: float = Field(..., ge=0, le=5)
    text: Optional[str] = Field(None, max_length=4000)


class RouteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    points: List[List[float]] = Field(..., description="Array of [lon, lat]")
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class PlaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=2000)
    address: Optional[str] = Field(None, max_length=255)
    tags: List[str] = Field(default_factory=list)
    hours: Optional[Dict[str, Any]] = Field(None, description="Arbitrary JSON with working hours info")


class PlaceCreate(PlaceBase):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class PlaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=2000)
    address: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None
    hours: Optional[Dict[str, Any]] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)

    @validator("lat")
    def lat_requires_lon(cls, v, values):
        if v is not None and values.get("lon") is None:
            raise ValueError("Provide lon when updating lat")
        return v

    @validator("lon")
    def lon_requires_lat(cls, v, values):
        if v is not None and values.get("lat") is None:
            raise ValueError("Provide lat when updating lon")
        return v


class RateRequest(BaseModel):
    rating: float = Field(..., ge=0, le=5)
    comment: Optional[str] = Field(None, max_length=2000)


class PolygonRequest(BaseModel):
    geojson: Dict[str, Any] = Field(..., description="Polygon or MultiPolygon GeoJSON")


class DistanceResponse(BaseModel):
    id: int
    distance_m: float


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    created_at: Optional[datetime]

