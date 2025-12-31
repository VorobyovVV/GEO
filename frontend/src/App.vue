<template>
  <div class="layout">
    <aside class="sidebar" :style="{ width: sidebarWidth + 'px' }">
      <div class="resize-handle" @mousedown.prevent="startResize"></div>
      <header class="header">
        <div>
          <h1>Карта интересных мест</h1>
          <p class="small">PostGIS + FastAPI + Vue + Leaflet</p>
        </div>
        <span class="badge">v2</span>
      </header>

      <nav class="nav">
        <button :class="{ active: activeSection === 'add' }" @click="goSection('add')">Добавить</button>
        <button :class="{ active: activeSection === 'filters' }" @click="goSection('filters')">Фильтры</button>
        <button :class="{ active: activeSection === 'list' }" @click="goSection('list')">Список</button>
        <button :class="{ active: activeSection === 'map' }" @click="goSection('map')">Карта</button>
      </nav>

      <section class="section" ref="addSection">
        <h2>Добавить место</h2>
        <p class="small">Кликните по карте — координаты попадут в форму</p>
        <form @submit.prevent="createPlace">
          <label>Название<input v-model="placeForm.name" required /></label>
          <label>Категория<input v-model="placeForm.category" required /></label>
          <label>Описание<textarea v-model="placeForm.description" rows="2"></textarea></label>
      <label>Адрес<input v-model="placeForm.address" /></label>
      <label>Теги (через запятую)<input v-model="placeForm.tags" placeholder="кофе, wifi" /></label>
      <label>Рейтинг (0–5)<input v-model.number="ratingInput" type="number" step="0.1" min="0" max="5" placeholder="4.5" /></label>
      <div class="hours-block">
        <div class="hours-head">
          <span>Часы работы</span>
          <button type="button" class="outline small-btn" @click="resetHours">Сбросить</button>
        </div>
        <div class="hours-grid">
          <div v-for="day in hoursForm" :key="day.key" class="hours-row">
            <label class="hours-day">
              <input type="checkbox" v-model="day.enabled" />
              <span>{{ day.label }}</span>
            </label>
            <input type="time" v-model="day.from" :disabled="!day.enabled" />
            <input type="time" v-model="day.to" :disabled="!day.enabled" />
          </div>
        </div>
      </div>
          <div class="row">
            <div><label>Широта<input v-model.number="placeForm.lat" type="number" step="any" required /></label></div>
            <div><label>Долгота<input v-model.number="placeForm.lon" type="number" step="any" required /></label></div>
          </div>
          <button type="submit" :disabled="placeLoading">Добавить</button>
          <p class="error">{{ placeError }}</p>
        </form>
      </section>

      <section class="section" ref="filtersSection">
        <h2>Фильтры</h2>
        <div class="row">
          <div><label>Тег<input v-model="filters.tag" /></label></div>
          <div><label>Мин. рейтинг<input v-model.number="filters.minRating" type="number" step="0.1" min="0" max="5" /></label></div>
        </div>
        <div class="row actions-row">
          <button class="outline" @click="loadPlaces">Обновить</button>
          <button @click="loadNearby">Ближайшие</button>
          <button class="outline" @click="locateMe">Моё местоположение</button>
          <button class="outline" @click="clearRoute">Сбросить маршрут</button>
        </div>
      </section>

      <section class="section" ref="listSection">
        <h2>Список</h2>
        <div v-if="places.length === 0" class="small">Нет данных</div>
        <div v-for="item in places" :key="item.id" class="card">
          <div class="card-header">
            <div class="clickable" @click="focusPlace(item)">
            <strong>{{ item.name }}</strong>
            <span class="pill">{{ item.category }}</span>
            </div>
            <div class="card-actions">
              <button class="link-btn" @click.stop="routeToPlace(item)">Маршрут</button>
              <button class="link-btn danger" @click.stop="deletePlace(item)">Удалить</button>
            </div>
          </div>
          <div class="muted clickable" @click="focusPlace(item)">{{ item.address }}</div>
          <div class="tags clickable" @click="focusPlace(item)">{{ (item.tags || []).join(', ') }}</div>
          <div class="muted clickable" @click="focusPlace(item)">Рейтинг: {{ item.avg_rating ?? '—' }}</div>
        </div>
      </section>
    </aside>

    <main class="map-wrap" ref="mapSection">
      <div id="map" ref="mapRef"></div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import L from 'leaflet';
import iconUrl from 'leaflet/dist/images/marker-icon.png';
import iconRetinaUrl from 'leaflet/dist/images/marker-icon-2x.png';
import shadowUrl from 'leaflet/dist/images/marker-shadow.png';
import axios from 'axios';

const mapRef = ref(null);
let map = null;
let markersLayer = null;
const markerIndex = new Map();
let userMarker = null;
let routeLayer = null;
const sidebarWidth = ref(400);
const resizing = ref(false);
const resizeStartX = ref(0);
const resizeStartWidth = ref(0);
const addSection = ref(null);
const filtersSection = ref(null);
const listSection = ref(null);
const mapSection = ref(null);
const activeSection = ref('map');

const placeForm = reactive({
  name: '',
  category: '',
  description: '',
  address: '',
  tags: '',
  hours: '',
  lat: 55.751244,
  lon: 37.618423,
});
const ratingInput = ref(null);
const hoursForm = reactive([
  { key: 'mon', label: 'Пн', enabled: true, from: '09:00', to: '21:00' },
  { key: 'tue', label: 'Вт', enabled: true, from: '09:00', to: '21:00' },
  { key: 'wed', label: 'Ср', enabled: true, from: '09:00', to: '21:00' },
  { key: 'thu', label: 'Чт', enabled: true, from: '09:00', to: '21:00' },
  { key: 'fri', label: 'Пт', enabled: true, from: '09:00', to: '21:00' },
  { key: 'sat', label: 'Сб', enabled: false, from: '10:00', to: '18:00' },
  { key: 'sun', label: 'Вс', enabled: false, from: '10:00', to: '18:00' },
]);
const placeError = ref('');
const placeLoading = ref(false);
const filters = reactive({ tag: '', minRating: null });
const places = ref([]);
const currentLocation = ref(null);

const api = axios.create({ baseURL: '/api' });

const markerIcon = L.icon({
  iconUrl,
  iconRetinaUrl,
  shadowUrl,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -32],
  shadowSize: [41, 41],
});

function startResize(e) {
  resizing.value = true;
  resizeStartX.value = e.clientX;
  resizeStartWidth.value = sidebarWidth.value;
  window.addEventListener('mousemove', onResize);
  window.addEventListener('mouseup', stopResize);
}

function onResize(e) {
  if (!resizing.value) return;
  const delta = e.clientX - resizeStartX.value;
  const next = Math.min(700, Math.max(280, resizeStartWidth.value + delta));
  sidebarWidth.value = next;
  if (map) {
    // defer to allow layout to settle
    requestAnimationFrame(() => map.invalidateSize());
  }
}

function stopResize() {
  resizing.value = false;
  window.removeEventListener('mousemove', onResize);
  window.removeEventListener('mouseup', stopResize);
}

function scrollToEl(el) {
  if (el?.value) {
    el.value.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function goSection(section) {
  activeSection.value = section;
  const mapping = {
    add: addSection,
    filters: filtersSection,
    list: listSection,
    map: mapSection,
  };
  scrollToEl(mapping[section] || mapSection);
}

async function loadPlaces() {
  if (!map || !markersLayer) return;
  const params = {};
  if (filters.tag) params.tag = filters.tag;
  if (filters.minRating) params.min_rating = filters.minRating;
  const { data } = await api.get('/places', { params });
  places.value = data;
  rebuildMarkers();
}

async function deletePlace(item) {
  if (!item?.id) return;
  const ok = window.confirm(`Удалить место «${item.name}»?`);
  if (!ok) return;
  try {
    await api.delete(`/places/${item.id}`);
    places.value = places.value.filter((p) => p.id !== item.id);
    rebuildMarkers();
  } catch (err) {
    alert('Не удалось удалить: ' + (err.response?.data?.detail || err.message));
  }
}

async function loadNearby() {
  if (!navigator.geolocation) return alert('Геолокация недоступна');
  navigator.geolocation.getCurrentPosition(async (pos) => {
    const { latitude, longitude } = pos.coords;
    setUserLocation(latitude, longitude);
    const params = { lat: latitude, lon: longitude, limit: 20 };
    const { data } = await api.get('/places/nearby', { params });
    places.value = data;
    rebuildMarkers();
    map.setView([latitude, longitude], 14);
  });
}

function setUserLocation(lat, lon) {
  currentLocation.value = { lat, lon };
  if (!map) return;
  if (userMarker) {
    userMarker.setLatLng([lat, lon]);
  } else {
    userMarker = L.circleMarker([lat, lon], {
      radius: 8,
      color: '#2563eb',
      fillColor: '#60a5fa',
      fillOpacity: 0.7,
      weight: 2,
    }).addTo(map);
    userMarker.bindPopup('Вы здесь');
  }
}

function clearRoute() {
  if (routeLayer) {
    routeLayer.clearLayers();
  }
}

async function locateMe() {
  if (!navigator.geolocation) return alert('Геолокация недоступна');
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { latitude, longitude } = pos.coords;
      setUserLocation(latitude, longitude);
      map?.setView([latitude, longitude], 13);
    },
    (err) => alert('Не удалось получить геолокацию: ' + err.message),
  );
}

async function routeToPlace(item) {
  const coords = item.geometry?.coordinates;
  if (!coords || coords.length < 2) return;
  // Если нет текущей локации — запросим
  if (!currentLocation.value) {
    await new Promise((resolve) => {
      if (!navigator.geolocation) {
        alert('Геолокация недоступна');
        resolve();
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setUserLocation(pos.coords.latitude, pos.coords.longitude);
          resolve();
        },
        (err) => {
          alert('Не удалось получить геолокацию: ' + err.message);
          resolve();
        },
      );
    });
  }
  if (!currentLocation.value) return;
  const from = [currentLocation.value.lat, currentLocation.value.lon];
  const to = [coords[1], coords[0]];
  clearRoute();

  // Попытка маршрута по дорогам через OSRM, иначе прямая.
  try {
    const url = `https://router.project-osrm.org/route/v1/driving/${from[1]},${from[0]};${to[1]},${to[0]}?overview=full&geometries=geojson`;
    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      const route = data?.routes?.[0];
      if (route?.geometry?.coordinates?.length) {
        const latlngs = route.geometry.coordinates.map(([lon, lat]) => [lat, lon]);
        const line = L.polyline(latlngs, { color: '#10b981', weight: 5, opacity: 0.9 });
        routeLayer.addLayer(line);
        map.fitBounds(line.getBounds(), { padding: [40, 40] });
        const marker = markerIndex.get(item.id);
        if (marker) marker.openPopup();
        return;
      }
    }
  } catch (e) {
    // fallback ниже
  }

  const straight = L.polyline([from, to], {
    color: '#10b981',
    weight: 4,
    opacity: 0.9,
    dashArray: '8 6',
  });
  routeLayer.addLayer(straight);
  map.fitBounds(straight.getBounds(), { padding: [40, 40] });
  const marker = markerIndex.get(item.id);
  if (marker) marker.openPopup();
}

function buildHoursObject() {
  const hours = {};
  hoursForm.forEach((d) => {
    if (d.enabled && d.from && d.to) {
      hours[d.key] = `${d.from}-${d.to}`;
    }
  });
  return hours;
}

function resetHours() {
  hoursForm.forEach((d) => {
    d.enabled = ['mon', 'tue', 'wed', 'thu', 'fri'].includes(d.key);
    d.from = d.enabled ? '09:00' : '10:00';
    d.to = d.enabled ? '21:00' : '18:00';
  });
  placeForm.hours = '';
}

async function createPlace() {
  placeLoading.value = true;
  placeError.value = '';
  try {
    const body = {
      name: placeForm.name,
      category: placeForm.category,
      description: placeForm.description || null,
      address: placeForm.address || null,
      tags: placeForm.tags
        ? placeForm.tags.split(',').map((t) => t.trim()).filter(Boolean)
        : [],
      hours: placeForm.hours
        ? JSON.parse(placeForm.hours)
        : (() => {
            const built = buildHoursObject();
            return Object.keys(built).length ? built : null;
          })(),
      lat: placeForm.lat,
      lon: placeForm.lon,
    };
    const { data } = await api.post('/places', body);
    if (ratingInput.value !== null && ratingInput.value !== undefined && ratingInput.value !== '') {
      const val = Math.max(0, Math.min(5, Number(ratingInput.value)));
      if (!Number.isNaN(val)) {
        await api.post(`/places/${data.id}/rate`, { rating: val });
      }
    }
    await loadPlaces();
    resetPlaceForm();
  } catch (err) {
    placeError.value = 'Ошибка: ' + (err.response?.data?.detail || err.message);
  } finally {
    placeLoading.value = false;
  }
}

function resetPlaceForm() {
  placeForm.name = '';
  placeForm.category = '';
  placeForm.description = '';
  placeForm.address = '';
  placeForm.tags = '';
  placeForm.hours = '';
  ratingInput.value = null;
  resetHours();
}

function rebuildMarkers() {
  if (!markersLayer) return;
  markerIndex.clear();
  markersLayer.clearLayers();
  places.value.forEach((p) => {
    const coords = p.geometry?.coordinates;
    if (!coords || coords.length < 2) return;
    const lat = coords[1];
    const lon = coords[0];
    const marker = L.marker([lat, lon], { icon: markerIcon });
    const popupHtml = `
      <div class="popup">
        <div class="popup-head">
          <div class="popup-title">${p.name}</div>
          ${p.category ? `<span class="popup-pill">${p.category}</span>` : ''}
        </div>
        <div class="popup-sub">${p.address || 'Адрес не указан'}</div>
        ${
          p.avg_rating !== null && p.avg_rating !== undefined
            ? `<div class="popup-meta">★ ${p.avg_rating}</div>`
            : ''
        }
        <div class="popup-actions">
          <button class="popup-btn" data-action="route">Маршрут</button>
          <button class="popup-btn outline" data-action="clear">Сбросить</button>
        </div>
      </div>
    `;
    marker.bindPopup(popupHtml);
    marker.on('popupopen', (e) => {
      const content = e.popup._contentNode;
      const routeBtn = content.querySelector('[data-action="route"]');
      const clearBtn = content.querySelector('[data-action="clear"]');
      routeBtn?.addEventListener('click', () => {
        routeToPlace(p);
        e.popup.close();
      });
      clearBtn?.addEventListener('click', () => {
        clearRoute();
        e.popup.close();
      });
    });
    marker.addTo(markersLayer);
    markerIndex.set(p.id, marker);
  });
}

function focusPlace(item) {
  const coords = item.geometry?.coordinates;
  if (!coords || coords.length < 2 || !map) return;
  const lat = coords[1];
  const lon = coords[0];
  map.setView([lat, lon], 15);
  const marker = markerIndex.get(item.id);
  if (marker) {
    marker.openPopup();
  }
}

async function ensureMap() {
  if (map) {
    map.invalidateSize();
    return;
  }
  if (!mapRef.value) return;
  map = L.map(mapRef.value, { attributionControl: false }).setView([placeForm.lat, placeForm.lon], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap',
  }).addTo(map);
  markersLayer = L.layerGroup().addTo(map);
  routeLayer = L.layerGroup().addTo(map);
  map.on('click', (e) => {
    placeForm.lat = parseFloat(e.latlng.lat.toFixed(6));
    placeForm.lon = parseFloat(e.latlng.lng.toFixed(6));
  });
  await loadPlaces();
}

onMounted(async () => {
  await ensureMap();
});
</script>

<style scoped>
.layout { display: flex; min-height: 100vh; background: #f8fafc; }
.layout { height: 100vh; overflow: hidden; }
.sidebar {
  position: relative;
  width: 400px; padding: 18px; overflow-y: auto; height: 100vh;
  border-right: 1px solid #e2e8f0; background: #ffffff;
  box-shadow: 2px 0 10px rgba(15,23,42,0.05);
}
.resize-handle {
  position: absolute;
  top: 0; right: -4px; width: 8px; height: 100%;
  cursor: col-resize;
  background: transparent;
}
.resize-handle:hover { background: rgba(37,99,235,0.12); }
.map-wrap { flex: 1; position: sticky; top: 0; height: 100vh; }
#map { width: 100%; height: 100%; }
h1 { margin: 0 0 6px; font-size: 22px; }
h2 { margin: 12px 0 6px; font-size: 16px; color: #1e293b; }
.small { font-size: 12px; color: #64748b; margin: 0 0 10px; }
label { display: block; margin-top: 10px; font-size: 13px; color: #475569; }
input, textarea {
  width: 100%; padding: 10px 12px; margin-top: 6px;
  border: 1px solid #e2e8f0; border-radius: 10px; background: #f8fafc;
  font-size: 14px; transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}
input:focus, textarea:focus {
  outline: none; border-color: #2563eb; background: #fff;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
}
button {
  margin-top: 12px; padding: 10px 12px; cursor: pointer;
  border: none; border-radius: 10px; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  box-shadow: 0 10px 20px rgba(37,99,235,0.18);
  transition: transform 0.1s ease, box-shadow 0.2s ease, filter 0.2s;
}
button:disabled { opacity: 0.6; cursor: not-allowed; box-shadow: none; }
button:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 14px 28px rgba(37,99,235,0.22); }
.outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; box-shadow: none; }
.full { width: 100%; }
.section {
  background: #fff; border: 1px solid #e2e8f0; border-radius: 14px;
  padding: 14px; margin-top: 12px; box-shadow: 0 6px 18px rgba(15,23,42,0.04);
}
.card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 10px 12px; margin-top: 10px; background: #f8fafc; }
.tags { color: #0ea5e9; font-size: 12px; }
.row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.row > div { flex: 1 1 140px; }
.row button { flex: 1 1 45%; min-width: 140px; }
.actions-row { gap: 8px; }
.actions-row button { padding: 10px 10px; }
.status { font-size: 12px; color: #16a34a; }
.error { color: #dc2626; font-size: 12px; }
.header { display: flex; align-items: center; justify-content: space-between; }
.badge { display: inline-flex; align-items: center; gap: 6px; background: #e0f2fe; color: #0369a1; padding: 6px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.muted { color: #64748b; font-size: 13px; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.card-actions { display: flex; gap: 8px; }
.pill { background: #e2e8f0; color: #0f172a; padding: 2px 8px; border-radius: 999px; font-size: 12px; }
.nav { display: flex; gap: 6px; margin-top: 12px; flex-wrap: wrap; }
.nav button {
  padding: 8px 10px; border-radius: 10px; border: 1px solid #e2e8f0;
  background: #fff; color: #0f172a; cursor: pointer; font-weight: 600; box-shadow: none;
}
.nav button.active { background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #fff; border-color: transparent; box-shadow: 0 10px 20px rgba(37,99,235,0.2); }
.clickable { cursor: pointer; transition: transform 0.05s ease; }
.clickable:hover { transform: translateY(-1px); box-shadow: 0 10px 20px rgba(15,23,42,0.08); }
.small-btn { padding: 8px 10px; margin-top: 0; }
.hours-block { margin-top: 10px; }
.hours-head { display: flex; align-items: center; justify-content: space-between; }
.hours-grid { display: grid; gap: 8px; margin-top: 8px; }
.hours-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; align-items: center; }
.hours-row input[type="time"] { padding: 8px 10px; }
.hours-day { display: flex; gap: 6px; align-items: center; font-size: 13px; color: #475569; }
.popup { display: flex; flex-direction: column; gap: 8px; min-width: 200px; }
.popup-head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.popup-title { font-weight: 700; font-size: 16px; color: #0f172a; }
.popup-sub { color: #475569; font-size: 13px; }
.popup-meta { color: #f59e0b; font-size: 13px; font-weight: 700; }
.popup-pill {
  background: #e0f2fe;
  color: #0369a1;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}
.popup-actions { display: flex; gap: 8px; }
.popup-btn {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 8px 16px rgba(37,99,235,0.18);
}
.popup-btn.outline {
  background: #fff;
  color: #0f172a;
  border: 1px solid #e2e8f0;
  box-shadow: none;
}
.popup-btn:hover { filter: brightness(1.03); }
.link-btn {
  background: none;
  border: none;
  color: #2563eb;
  font-weight: 600;
  cursor: pointer;
  padding: 6px 8px;
}
.link-btn:hover { text-decoration: underline; }
.link-btn.danger { color: #dc2626; }

@media (max-width: 1024px) {
  .layout {
    flex-direction: column;
  }
  .sidebar {
    width: 100% !important;
    height: auto;
    position: relative;
    border-right: none;
    box-shadow: none;
  }
  .map-wrap {
    position: relative;
    height: 60vh;
  }
  #map {
    height: 60vh;
  }
  .resize-handle {
    display: none;
  }
}

@media (max-width: 640px) {
  .row { flex-direction: column; align-items: stretch; }
  .nav { width: 100%; }
  button, .outline { width: 100%; }
  .card-header { flex-direction: column; align-items: flex-start; }
  .card-actions { width: 100%; justify-content: flex-start; flex-wrap: wrap; }
}
</style>

