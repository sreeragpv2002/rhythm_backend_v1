# Rhythm Backend 🎵

A high-performance FastAPI backend for the **Rhythm** music streaming application. Powered by YouTube Music (via `ytmusicapi`) with multi-language aggregation, caching, Firestore user state (recent plays, favorites, language preferences, custom playlists), and an automated CI/CD pipeline.

---

## 🚀 Features

- **Personalized Home API (`GET /api/v1/home`)**:
  - Aggregates user recent plays, trending songs, featured playlists, trending albums, top artists, and language items.
  - **Clean Minimal Schema**: Compact cards with `id`, `name`, `title`, `image`, `image_url`, and `type`.
  - **Accurate Song Covers**: Intelligent metadata extraction ensures high-resolution track covers are displayed.
  - **Multi-Language Aggregation**: Interleaves tracks across selected languages (`malayalam`, `tamil`, `hindi`, `kannada`, `telugu`, `english`).
  - **1-Day In-Memory Cache**: 24-hour TTL caching for home sections with instant user play invalidation.

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
- **Data Source**: YouTube Music via [`ytmusicapi`](https://ytmusicapi.readthedocs.io/)
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
│   │   └── ytmusic_service.py
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
| `PORT` | Web server listening port (dynamically set by Render) | `8000` |
| `RENDER` | Render environment indicator (automatically set to `true` by Render) | None |
| `ENABLE_SERVER_YTDLP` | Toggle yt-dlp execution on server (disabled by default on Render) | `false` on Render / `true` on local |
| `SAAVN_BASE_URL` | JioSaavn API gateway | `https://saavn.sumit.co` |
| `HOME_CACHE_TTL_SECONDS` | Cache duration for home feed (24h) | `86400` |
| `FIREBASE_CREDENTIALS_PATH` | Path to service account JSON | `credentials/firebase-service-account.json` |
| `FIREBASE_CREDENTIALS_JSON` | Service account JSON string (for CI/Cloud) | None |
| `GRPC_DNS_RESOLVER` | Resolver for Linux gRPC network | `native` |
| `PROXY_URL` | Optional proxy URL (HTTP/HTTPS/SOCKS5) for yt-dlp | None |

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

# Run the container (binds to port 8000 by default)
docker run -d -p 8000:8000 \
  -e FIREBASE_CREDENTIALS_JSON='{"type":"service_account",...}' \
  --name rhythm-backend rhythm-backend
```

---

## ☁️ Deploying to Render

This repository includes a [`render.yaml`](file:///home/sree/sree/rhythm_backend/render.yaml) blueprint and dynamic port binding support for easy deployment on [Render](https://render.com/).

### Dynamic Port Handling
- Render dynamically assigns an internal port via the `PORT` environment variable (typically `10000`).
- The [`Dockerfile`](file:///home/sree/sree/rhythm_backend/Dockerfile) starts Uvicorn via `sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"`, ensuring compatibility with both Render cloud servers (`$PORT`) and local development (`localhost:8000`).

### yt-dlp Local vs Server Behavior
- **Localhost Development (`localhost:8000`)**: yt-dlp runs natively as your primary audio stream extractor. Residential IPs are not blocked by YouTube.
- **Render Cloud Server**: Render sets `RENDER=true`. yt-dlp is automatically **skipped** on the server to prevent YouTube datacenter IP blocking/delays, immediately using decentralized fallback stream APIs (**Piped** & **Invidious**).
- **Optional Server yt-dlp Override**: If you attach a residential proxy, set `PROXY_URL` or `ENABLE_SERVER_YTDLP=true` in Render's environment variables.

### Deploy Steps on Render:
1. Push your repository to GitHub / GitLab.
2. In the Render Dashboard, click **New +** -> **Blueprint**.
3. Select your repository. Render will automatically detect [`render.yaml`](file:///home/sree/sree/rhythm_backend/render.yaml).
4. Add your Firebase credentials either as:
   - **Environment Variable**: `FIREBASE_CREDENTIALS_JSON` (paste your service account JSON string).
   - **Secret File**: `/etc/secrets/firebase-service-account.json` (upload the JSON file).
5. (Optional) Add YouTube cookies if needed:
   - **Secret File**: `/etc/secrets/cookies.txt`.
6. Deploy! Your API will be live with automatic `/health` checks.

