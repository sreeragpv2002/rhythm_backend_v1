# Rhythm - Music Streaming Platform Backend

A production-ready music streaming backend built with Django REST Framework, supporting multiple user roles, multilingual capabilities (English/Arabic), and three separate platforms: Customer App, Broadcaster Panel, and Admin Panel.

## Features

- 🎵 **Multi-Platform Support**: Customer App, Broadcaster Panel, Admin Panel
- 🌍 **Multilingual**: English and Arabic with RTL support
- 🔐 **Authentication**: JWT + Google OAuth 2.0
- 🎨 **Tag System**: Categorize music by mood, genre, and theme
- 🎧 **Audio Streaming**: Optimized music streaming
- 📱 **RESTful API**: Clean, versioned API design
- 📚 **API Documentation**: Swagger UI and Postman collection

## Tech Stack

- **Framework**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL
- **Authentication**: JWT (Simple JWT) + Google OAuth
- **API Documentation**: drf-spectacular (Swagger/OpenAPI)
- **Internationalization**: django-modeltranslation
- **File Handling**: Pillow
- **Optional**: Redis + Celery for caching and background tasks

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- pip and virtualenv

### Installation

1. **Clone the repository**
   ```bash
   cd rhythm_backend
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   copy .env.example .env
   # Edit .env with your configuration
   ```

5. **Create PostgreSQL database**
   ```sql
   CREATE DATABASE rhythm_db;
   CREATE USER postgres WITH PASSWORD 'your-password';
   GRANT ALL PRIVILEGES ON DATABASE rhythm_db TO postgres;
   ```

6. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Create translation files**
   ```bash
   python manage.py makemessages -l ar
   python manage.py compilemessages
   ```

8. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

9. **Run development server**
   ```bash
   python manage.py runserver
   ```

## API Documentation

Once the server is running, access the API documentation:

- **Swagger UI**: http://localhost:8000/api/schema/swagger-ui/
- **ReDoc**: http://localhost:8000/api/schema/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/
- **Django Admin**: http://localhost:8000/admin/

## Postman Collection

Import the Postman collection from `docs/postman_collection.json` to test all API endpoints.

**Environment Variables**:
- `base_url`: http://localhost:8000
- `access_token`: (auto-set from login)
- `refresh_token`: (auto-set from login)

## Project Structure

```
rhythm_backend/
├── accounts/              # User authentication & profiles
├── music/                 # Music, artists, albums, playlists
├── api/                   # API utilities & response formatting
├── rhythm_backend/        # Project settings
│   └── settings/
│       ├── base.py       # Base settings
│       ├── development.py # Dev settings
│       └── production.py  # Prod settings
├── locale/               # Translation files (.po/.mo)
├── docs/                 # API documentation
├── media/                # Uploaded files
└── manage.py
```

## User Roles

1. **Customer**: Browse and stream music, create playlists
2. **Broadcaster**: Upload and manage music catalog
3. **Admin**: Full system access and content moderation

## Multi-language Support

The platform supports English and Arabic:

- **Model Fields**: Translatable fields (name, title, description)
- **API Responses**: Based on `Accept-Language` header
- **Error Messages**: Fully translated

**Example Request**:
```bash
curl -H "Accept-Language: ar" http://localhost:8000/api/v1/music/
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register/` - Register new user
- `POST /api/v1/auth/login/` - Login and get JWT token
- `POST /api/v1/auth/token/refresh/` - Refresh access token
- `GET /api/v1/auth/profile/` - Get user profile

### Music (Customer)
- `GET /api/v1/music/` - Browse music
- `GET /api/v1/music/?tags=feelgood,energetic` - Filter by tags
- `GET /api/v1/music/?language=ARABIC` - Filter by language
- `GET /api/v1/music/{id}/stream/` - Stream audio
- `GET /api/v1/artists/` - Browse artists
- `GET /api/v1/albums/` - Browse albums

### Playlists
- `GET /api/v1/playlists/` - List user playlists
- `POST /api/v1/playlists/` - Create playlist
- `PUT /api/v1/playlists/{id}/` - Update playlist
- `DELETE /api/v1/playlists/{id}/` - Delete playlist

### Broadcaster
- `POST /api/v1/broadcaster/music/` - Upload music
- `GET /api/v1/broadcaster/music/` - Manage catalog
- `PUT /api/v1/broadcaster/music/{id}/` - Edit metadata

### Admin
- Full CRUD for users, artists, albums, music, tags
- Broadcaster verification
- Content moderation

## Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Updating Translations
```bash
python manage.py makemessages -l ar
python manage.py compilemessages
```

## Deployment

### Docker
```bash
docker-compose up -d
```

### Production Settings
Set environment variable:
```bash
export DJANGO_SETTINGS_MODULE=rhythm_backend.settings.production
```

## License

MIT License

## Support

For issues and questions, please open an issue on the repository.
