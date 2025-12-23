## Карта интересных мест

Интерактивная карта города с добавлением точек, фильтрами, поиском, маршрутами и рейтингами. Стек: FastAPI + Postgres/PostGIS + Vue 3 + Leaflet.

---

## Идея и функции
- Карта (Leaflet): клики ставят координаты для формы, попапы, зум/фокус на выбранной точке.
- Добавление места: название, категория, описание, адрес, теги, часы (JSON или конструктор), координаты; сразу можно проставить рейтинг.
- Фильтры: по тегу, минимальному рейтингу; «Ближайшие» через геолокацию; текстовый поиск.
- Гео-запросы: ближайшие, в радиусе, внутри полигона, экспорт GeoJSON по bbox, кластеризация по zoom.
- Рейтинги и отзывы: POST к месту, пересчёт среднего.
- Уведомления: новые модерированные места за 7 дней в радиусе.
- Маршруты: сохранение LineString из массива точек, выдача маршрутов пользователя.
- Авторизация: signup/login → JWT, проверка `/auth/me` или `/users/me`.

---

## Стек
- Backend: FastAPI, psycopg2, pydantic-settings, passlib[bcrypt], python-jose, uvicorn.
- DB: Postgres + PostGIS (Point/LineString, индексы GiST/GiN).
- Frontend: Vue 3 (Vite), Leaflet, Axios, Nginx (в Docker).
- Контейнеры: Docker Compose (db, backend, frontend).

---

## Модель данных (db/init.sql)
- `users`: id, username (unique), password_hash, role (user/admin), created_at.
- `places`: id, user_id?, name, category, description, address, tags[], avg_rating, hours JSONB, geom Point(4326), is_moderated, created_at; индексы geom/category/tags.
- `place_ratings`: place_id+user_id unique, rating, comment.
- `reviews`: place_id, user_id, rating, text, created_at (используется при rate/review сейчас с user_id NULL).
- `routes`: user_id, name, geom LineString(4326).
- Сидинг: 4 точки вокруг центра Москвы.

---

## API (основное)
- `/health` GET — ping.
- Auth `/auth`:
  - POST `/signup` → Token (создать пользователя; admin если в `ADMIN_USERS`).
  - POST `/login` (form username/password) → Token.
  - GET `/me` → текущий пользователь.
- Users:
  - GET `/users/me` → текущий пользователь.
- Places `/places`:
  - POST `` → создать место.
  - GET `` → список; фильтры `category`, `tag`, `min_rating`, пагинация.
  - GET `/nearby` → ближайшие к lat/lon.
  - GET `/{id}` → место.
  - PUT `/{id}` → обновить.
  - DELETE `/{id}` → удалить.
  - POST `/{id}/rate` → оценка + пересчёт среднего.
  - POST `/{id}/reviews` → отзыв + пересчёт.
  - GET `/{id}/distance` → расстояние до lat/lon.
  - GET `/within` → точки в радиусе lat/lon/radius_m.
  - POST `/within-polygon` → точки внутри GeoJSON полигона.
  - GET `/stats/by-category` → агрегация по категориям.
  - GET `/tags` → уникальные теги (ILIKE).
  - GET `/search` → текстовый поиск.
  - GET `/notifications` → новые за 7 дней в радиусе (is_moderated=true).
  - GET `/export/geojson` → FeatureCollection по bbox.
  - GET `/clustered` → k-means кластеры (зависит от zoom).
- Routes `/routes` (требует Bearer):
  - POST `` → создать маршрут (name, points [[lon, lat], …], ≥2 точки).
  - GET `` → маршруты текущего пользователя (limit/offset).

---

## Переменные окружения
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`.
- `JWT_SECRET`, `JWT_ALGORITHM` (HS256), `JWT_EXPIRES_MINUTES`.
- `CORS_ORIGINS` (CSV), `ADMIN_USERS` (CSV имён для роли admin).

---

## Запуск через Docker Compose
Требования: свободны порты 8080 (фронт), 8000 (API), 5432 (БД).

Из корня:
```bash
docker compose build --no-cache backend
docker compose up
```

Сервисы:
- Фронт: http://localhost:8080
- Swagger: http://localhost:8000/docs
- Postgres/PostGIS: localhost:5432 (postgres/postgres или значения из env, БД `geodb`)

Если порт 5432 занят — поправьте проброс в `docker-compose.yml`, например `55432:5432`, и подключайтесь на 55432.

---

## Быстрый просмотр фронта без Docker
```bash
cd /Users/vlad/univer/GeoBD/frontend
python -m http.server 8080
```
API тогда по http://localhost:8000 (при необходимости указать полный URL в fetch/Axios и включить CORS).

---

## Как зайти
1) Открыть фронт http://localhost:8080  
2) В блоке аккаунта: ввести логин/пароль → «Регистрация» (создаёт пользователя), токен сохраняется в localStorage.  
3) Авторизованные действия: добавление мест, рейтинги/отзывы, маршруты.  
4) Проверка токена: `/users/me` или `/auth/me` в Swagger, статус в UI.  

