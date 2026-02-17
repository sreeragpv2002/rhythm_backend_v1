# Quick Start Guide - Rhythm Backend

## 🚀 Setup Instructions

### 1. Install Dependencies
```bash
cd c:\Users\USER\Downloads\rhythm_backend
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
copy .env.example .env
# Edit .env with your database credentials
```

### 3. Create Database
```sql
CREATE DATABASE rhythm_db;
```

### 4. Run Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create Superuser
```bash
python manage.py createsuperuser
```

### 6. Run Server
```bash
python manage.py runserver
```

### 7. Access the Application
- **API Base:** http://localhost:8000/api/v1/
- **Admin Panel:** http://localhost:8000/admin/
- **Swagger Docs:** http://localhost:8000/api/schema/swagger-ui/
- **ReDoc:** http://localhost:8000/api/schema/redoc/

---

## 📝 Create Sample Data

### Via Admin Panel (http://localhost:8000/admin/)

1. **Create Tags:**
   - Mood: #feelgood, #energetic, #relaxing, #romantic
   - Genre: #pop, #rock, #jazz, #hiphop
   - Theme: #workout, #study, #party, #sleep

2. **Create Artists:**
   - Add artist name (English and Arabic)
   - Upload artist image

3. **Create Albums:**
   - Link to artist
   - Add cover image

4. **Upload Music:**
   - Link to artist and album
   - Upload audio file
   - Set language
   - Add tags

5. **Create Advertisements:**
   - Set ad type and placement
   - Upload media files
   - Set priority

---

## 🧪 Test the APIs

### 1. Register a User
```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!",
    "password2": "SecurePass123!",
    "first_name": "Test",
    "last_name": "User",
    "role": "CUSTOMER"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'
```

Save the `access` token from the response.

### 3. Get Home Feed
```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8000/api/v1/home/
```

### 4. Search Music
```bash
curl "http://localhost:8000/api/v1/music/search/?q=love&language=ENGLISH"
```

### 5. Create Playlist
```bash
curl -X POST http://localhost:8000/api/v1/playlists/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Playlist", "is_public": false}'
```

---

## 📚 Documentation

- **API Documentation:** `docs/API_DOCUMENTATION.md`
- **Swagger UI:** http://localhost:8000/api/schema/swagger-ui/
- **README:** `README.md`

---

## 🐳 Docker Setup (Alternative)

```bash
docker-compose up -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

Access at http://localhost:8000

---

## 🎯 Key Endpoints

### Customer APIs
- `GET /api/v1/home/` - Personalized home feed
- `GET /api/v1/music/search/` - Search music
- `GET /api/v1/music/` - Browse music
- `POST /api/v1/music/{id}/stream/` - Stream music
- `GET /api/v1/playlists/` - List playlists
- `GET /api/v1/favorites/` - List favorites

### Authentication
- `POST /api/v1/auth/register/` - Register
- `POST /api/v1/auth/login/` - Login
- `POST /api/v1/auth/token/refresh/` - Refresh token

---

## ⚡ Quick Tips

1. **Use Swagger UI** for interactive API testing
2. **Check admin panel** to create sample data
3. **Set language** via `Accept-Language: ar` header
4. **Use pagination** with `?page=1&page_size=20`
5. **Filter music** by `?language=ARABIC&tags=feelgood`
