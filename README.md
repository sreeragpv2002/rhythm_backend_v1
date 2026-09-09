# Rhythm Backend 🎵

A high-performance FastAPI backend for the **Rhythm** music streaming application. Powered by JioSaavn (via Sumit Kolhe API) with multi-language aggregation, caching, Firestore user state (recent plays, favorites, language preferences, custom playlists), and an automated CI/CD pipeline.

---

## 🚀 Features

- **Personalized Home API (`GET /api/v1/home`)**:
  - Aggregates user recent plays, trending songs, featured playlists, trending albums, top artists, and language items.
  - **Clean Minimal Schema**: Compact cards with `id`, `name`, `title`, `image`, `image_url`, and `type`.
  - **Accurate Song Covers**: Intelligent compilation/playlist filtering ensures real original track covers are displayed instead of playlist artwork.
  - **Multi-Language Aggregation**: Interleaves tracks across selected languages (`malayalam`, `tamil`, `hindi`, `kannada`, `telugu`, `english`).
  - **1-Day In-Memory Cache**: 24-hour TTL caching for JioSaavn home sections with instant user play invalidation.

- **Unified Details API (`GET /api/v1/details`)**:
  - Single polymorphic endpoint supporting `song`, `playlist`, `artist`, and `album`.
  - Also available via explicit endpoints: `/api/v1/songs/{id}`, `/api/v1/playlists/{id}`, `/api/v1/artists/{id}`, `/api/v1/albums/{id}`.
  - For songs, includes **automated related song suggestions** (`suggested_songs`).

- **User Language Preferences (`/api/v1/languages`)**:
  - Allowed languages: `malayalam`, `tamil`, `hindi`, `kannada`, `telugu`, `english`.
  - Set (`POST`) and update (`PUT`) preferred languages saved directly to Firestore.

- **Favorites & Playlist Management (`/api/v1/favorites`, `/api/v1/user-playlists`)**:
  - System **Favorites** playlist auto-created for every user.
  - Add to favorites (`POST /api/v1/favorites`), remove from favorites (`DELETE /api/v1/favorites/{song_id}`), check status (`GET /api/v1/favorites/check`).
  - Custom playlists CRUD (`POST`, `GET`, `DELETE`) with subcollection song management.

- **Automated CI/CD Pipeline**:
  - GitHub Actions workflow running Ruff linting, Python syntax compilation, FastAPI initialization, and offline unit test suites on every push and pull request.

---

## 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+)
- **Server**: Uvicorn (ASGI)
- **Database**: Google Cloud Firestore & Firebase Admin SDK
- **Data Source**: Sumit Kolhe JioSaavn API (`https://saavn.sumit.co`)
- **Linting & Code Quality**: Ruff
- **CI/CD**: GitHub Actions

---

## 📁 Project Structure

```text
rhythm_backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── details.py         # Unified Details API & suggestions
│   │       │   ├── favorites.py       # Favorites & Favorites-as-a-playlist
│   │       │   ├── home.py            # Home feed & card formatting
│   │       │   ├── languages.py       # Language preferences API
│   │       │   ├── playlists.py       # Custom user playlists CRUD
│   │       │   └── recent_plays.py    # Recent plays tracking
│   │       └── router.py              # APIRouter aggregation
│   ├── models/                        # Pydantic schemas
│   │   ├── details.py
│   │   ├── home.py
│   │   ├── language.py
│   │   ├── playlist.py
│   │   └── recent_play.py
│   ├── services/                      # Business logic layer
│   │   ├── playlist_service.py
│   │   └── saavn_service.py
│   └── main.py                        # FastAPI application entrypoint
├── core/
│   ├── cache.py                       # In-memory TTL cache (86400s)
│   ├── config.py                      # Pydantic Settings
│   └── firebase.py                    # Firebase & Firestore SDK helper
├── tests/
│   ├── run_tests.py                   # Full end-to-end integration test suite
│   ├── test_api.py                    # Pytest test definitions
│   └── test_ci_offline.py             # Offline unit tests for CI
├── .github/
│   └── workflows/
│       └── pipeline.yml               # GitHub Actions CI/CD workflow
├── Dockerfile                         # Container configuration
├── requirements.txt                   # Production dependencies
└── pyproject.toml                     # Ruff & build configuration
```

---

## ⚙️ Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Description | Default |
| --- | --- | --- |
| `SAAVN_BASE_URL` | JioSaavn API gateway | `https://saavn.sumit.co` |
| `HOME_CACHE_TTL_SECONDS` | Cache duration for home feed (24h) | `86400` |
| `FIREBASE_CREDENTIALS_PATH` | Path to service account JSON | `credentials/firebase-service-account.json` |
| `FIREBASE_CREDENTIALS_JSON` | Service account JSON string (for CI/Cloud) | None |
| `GRPC_DNS_RESOLVER` | Resolver for Linux gRPC network | `native` |

> ⚠️ **Security Warning**: Never commit `credentials/` or `firebase-service-account.json` to version control.

---

## 🚀 Running Locally

### 1. Create and activate a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the development server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Access Swagger UI documentation at: `http://localhost:8000/docs`

---

## 🧪 Testing & Validation

### Run Offline Unit Tests (No Cloud credentials needed)
```bash
python -m unittest tests/test_ci_offline.py
```

### Run Full Integration Test Suite (Requires Firebase)
```bash
python tests/run_tests.py
```

### Code Quality Check
```bash
ruff check app core tests
```

---

## 🐳 Docker Deployment

```bash
# Build the image
docker build -t rhythm-backend .

# Run the container
docker run -d -p 8000:8000 \
  -e FIREBASE_CREDENTIALS_JSON='{"type":"service_account",...}' \
  --name rhythm-backend rhythm-backend
```
