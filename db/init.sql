CREATE EXTENSION IF NOT EXISTS postgis;

-- Интересные места города
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS places (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    address TEXT,
    tags TEXT[] DEFAULT '{}'::TEXT[],
    avg_rating NUMERIC(3, 2),
    hours JSONB,
    geom GEOMETRY(Point, 4326) NOT NULL,
    is_moderated BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS place_ratings (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating NUMERIC(2, 1) NOT NULL CHECK (rating >= 0 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (place_id, user_id)
);

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    place_id INTEGER NOT NULL REFERENCES places(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    rating NUMERIC(2, 1) NOT NULL CHECK (rating >= 0 AND rating <= 5),
    text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS routes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    geom GEOMETRY(LineString, 4326) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_places_geom ON places USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_places_category ON places (category);
CREATE INDEX IF NOT EXISTS idx_places_tags ON places USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_reviews_place_id ON reviews (place_id);
CREATE INDEX IF NOT EXISTS idx_routes_geom ON routes USING GIST (geom);

-- Примеры вокруг центра Москвы
INSERT INTO places (name, category, description, address, tags, avg_rating, hours, geom)
VALUES
    ('Видовая площадка', 'viewpoint', 'Смотровая с панорамой на центр', 'Воробьёвы горы', ARRAY['панорама','фото'], 4.8,
     '{"mon-sun":"00:00-24:00"}',
     ST_SetSRID(ST_MakePoint(37.5597, 55.7100), 4326)),
    ('Кофейня на Арбате', 'cafe', 'Спешелти кофе и десерты', 'Арбат, 12', ARRAY['coffee','wifi'], 4.6,
     '{"mon-fri":"08:00-22:00","sat-sun":"09:00-23:00"}',
     ST_SetSRID(ST_MakePoint(37.6041, 55.7522), 4326)),
    ('Сквер у Чистых прудов', 'park', 'Тихое место с лавочками и Wi-Fi', 'Чистопрудный бульвар', ARRAY['лавочки','озеро','wifi'], 4.5,
     '{"mon-sun":"00:00-24:00"}',
     ST_SetSRID(ST_MakePoint(37.6389, 55.7655), 4326)),
    ('Спортплощадка на набережной', 'sport', 'Турники, брусья, воркаут зона', 'Берег Яузы', ARRAY['спорт','воркаут','свободно'], 4.4,
     '{"mon-sun":"06:00-23:00"}',
     ST_SetSRID(ST_MakePoint(37.6800, 55.7760), 4326))
ON CONFLICT DO NOTHING;

