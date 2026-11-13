# ⚡ CascadeIQ

> Real-time flood disaster coordination platform for the Punjab / Sutlej River Basin.

[![Live Demo](https://img.shields.io/badge/demo-cascade--iq--omega.vercel.app-3b82f6?style=flat-square&logo=vercel)](https://cascade-iq-omega.vercel.app)
[![API](https://img.shields.io/badge/API-Railway-7c3aed?style=flat-square&logo=railway)](https://backend-production-5df77628.up.railway.app/docs)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb?style=flat-square&logo=react)](https://react.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+PostGIS-336791?style=flat-square&logo=postgresql)](https://postgis.net)

CascadeIQ tracks flood zones, incidents, and resources across the Sutlej basin — and uses a **cascade graph model** to show how flooding in one zone propagates risk to zones downstream, before human coordinators would even notice.

---

## 🌊 The Problem

Flood coordination in Punjab involves dozens of agencies, none of which share a common operational picture:

- **Information fragmentation** — IMD data, field reports, and satellite imagery all live in separate silos
- **Delayed resource allocation** — manual phone trees mean rescue assets arrive after the floodwaters have moved on
- **Cascade blindness** — nobody can see upstream failures cascading downstream until it's too late to pre-position

CascadeIQ is built to close all three gaps.

---

## ✨ Features

| Feature | What it does |
|---|---|
| **Zone risk map** | Interactive Leaflet.js map with PostGIS polygon overlays, color-coded by real-time risk level |
| **Cascade graph** | Directed zone graph — severity propagates downstream via BFS when upstream risk escalates |
| **ML risk predictor** | scikit-learn weighted scorer across 5 features → LOW / MODERATE / HIGH / CRITICAL labels |
| **Incident tracking** | Field-submitted incidents with PostGIS point geometry and severity classification |
| **Resource optimizer** | Gap-based deployment recommendations matching available resources to high-need zones |
| **Deployment tracker** | Lifecycle management for resource deployments: PENDING → ACTIVE → COMPLETED |
| **GROQ briefings** | LLM-generated situation summaries for coordinators, refreshed on demand |
| **Weather integration** | Hourly rainfall and weather data pulled from OpenWeather API per zone |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│  React 18 SPA                       │  → Vercel CDN (edge)
│  Leaflet.js · Recharts · Axios      │
└─────────────┬───────────────────────┘
              │ HTTPS / REST
┌─────────────▼───────────────────────┐
│  FastAPI (ASGI) + uvicorn           │  → Railway
│  SQLAlchemy 2.0 · asyncpg           │
│  Pydantic · python-jose             │
└─────────────┬───────────────────────┘
              │ asyncpg
┌─────────────▼───────────────────────┐
│  PostgreSQL 15 + PostGIS 3.4        │  → Supabase (Seoul)
│  GiST spatial index                 │
│  ST_DWithin · ST_Contains           │
└─────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

**Backend** — FastAPI, SQLAlchemy 2.0, asyncpg, Pydantic, uvicorn, python-jose, scikit-learn, GROQ SDK  
**Frontend** — React 18 (CRA), Leaflet.js, Recharts, Axios, React Router  
**Database** — PostgreSQL 15, PostGIS 3.4, Supabase  
**Infrastructure** — Railway (API), Vercel (frontend), Supabase (DB, Seoul region)  
**External APIs** — OpenWeather (weather), GROQ (LLM briefings)

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15 with PostGIS extension (or a Supabase project)

### Backend

```bash
git clone https://github.com/harkaran911/cascadeiq.git
cd cascadeiq/backend

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/cascadeiq
OPENWEATHER_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
SECRET_KEY=any_random_string_here
```

Run migrations and start:

```bash
alembic upgrade head       # or: python init_db.py
uvicorn main:app --reload
```

API docs available at `http://localhost:8000/docs`

### Frontend

```bash
cd ../frontend
npm install
```

Create a `.env` file:

```env
REACT_APP_API_URL=http://localhost:8000
```

```bash
npm start
```

---

## 🗄️ Database Schema

Five core entities, all spatially-aware:

```sql
Zone          -- id, name, district, risk_level, geometry POLYGON(4326), population_density
Incident      -- id, zone_id FK, severity, incident_type, location POINT(4326), created_at
Resource      -- id, zone_id FK, resource_type, quantity, status
Deployment    -- id, resource_id FK, from_zone_id FK, to_zone_id FK, status, urgency_score
WeatherData   -- id, zone_id FK, rainfall_mm, temperature, humidity, recorded_at
```

Spatial queries use PostGIS `ST_DWithin` for proximity-based resource matching and `ST_Contains` for point-in-zone incident classification.

---

## 📡 Key API Endpoints

```
GET  /api/zones                        → All zones with current risk levels
GET  /api/zones/{id}                   → Zone detail + cascade neighbors
GET  /api/cascade                      → Full cascade graph (nodes + edges + risk scores)
POST /api/incidents                    → Submit a new incident (lat/lng auto-classified to zone)
GET  /api/incidents                    → All active incidents
GET  /api/resources                    → Resource inventory across all zones
GET  /api/resources/optimize           → Deployment recommendations (gap analysis)
GET  /api/resources/deployments        → Active and pending deployments
POST /api/resources/deployments/{id}/approve → Approve a deployment
GET  /api/weather/{zone_id}            → Latest weather data for a zone
POST /api/briefing/{zone_id}           → Generate GROQ LLM situation briefing
```

Full interactive docs at `{API_URL}/docs` (auto-generated by FastAPI).

---

## ⚠️ Known Limitations

- **No authentication** — any user can submit incidents or access the API
- **Zone boundaries are hardcoded** — not synced with official Punjab district maps
- **ML model is a weighted proxy** — no real historical flood training data yet
- **Cold start latency** — Railway free tier adds ~15–30s after inactivity
- **Single weather point per zone** — doesn't capture micro-hydrological variation

---

## 🔭 Future Scope

- **IoT river gauges** — MQTT-based real-time water level feeds from physical sensors
- **Sentinel-1 SAR integration** — satellite inundation mapping for areas without field access
- **Mobile PWA** — offline-capable incident reporting for NDRF field teams
- **WhatsApp bot** — push alerts to village-level coordinators via WhatsApp Business API
- **JWT auth + RBAC** — admin / coordinator / viewer roles with 2FA
- **LSTM flood model** — retrain on 20 years of IMD Punjab historical data

---

## 📁 Project Structure

```
cascadeiq/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── database.py          # Async DB session setup
│   ├── routers/
│   │   ├── zones.py
│   │   ├── incidents.py
│   │   ├── resources.py
│   │   ├── weather.py
│   │   └── briefing.py
│   ├── services/
│   │   ├── cascade_graph.py # BFS cascade propagation engine
│   │   ├── ml_predictor.py  # Risk scoring model
│   │   └── optimizer.py     # Resource gap analysis
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── ZoneMap.jsx   # Leaflet map with PostGIS polygons
    │   │   ├── Dashboard.jsx
    │   │   ├── IncidentFeed.jsx
    │   │   └── ResourcePanel.jsx
    │   ├── api/
    │   │   └── index.js      # Axios API client
    │   └── App.js
    └── package.json
```

---

## 🔧 Deployment Notes

### CORS (important)

The backend uses `allow_credentials=False` with `allow_origins=["*"]`. **Do not** switch to `allow_credentials=True` with wildcard origins — browsers will block it. If you need credentialed requests later, switch to explicit origin allowlisting.

### Railway

Set all environment variables in the Railway dashboard under **Variables**. The `DATABASE_URL` from Supabase should use the `postgresql+asyncpg://` prefix for async SQLAlchemy.

### Supabase

Enable the PostGIS extension from the Supabase SQL editor:
```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

---

## 📸 Screenshots

| Dashboard | Zone Map |
|---|---|
| ![Dashboard](docs/screenshot_dashboard.png) | ![Map](docs/screenshot_map.png) |

---

## 📄 License

MIT — do whatever you want with it.

---

<div align="center">
  Built for <strong>24CSP-337 · Full Stack II</strong> · Chandigarh University · 2026<br>
  <a href="https://cascade-iq-omega.vercel.app">Live Demo</a> ·
  <a href="https://backend-production-5df77628.up.railway.app/docs">API Docs</a>
</div>
