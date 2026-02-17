# Rhythm Music Streaming API - Customer Endpoints

This document provides comprehensive documentation for all customer-facing API endpoints.

## Base URL
```
http://localhost:8000/api/v1/
```

## Authentication
Most endpoints require JWT authentication. Include the access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## 🏠 Home Feed API

### Get Personalized Home Feed
**Endpoint:** `GET /home/`  
**Authentication:** Required  
**Description:** Get personalized home feed with recommendations based on user interests and listening history

**Response:**
```json
{
  "success": true,
  "message": "Home feed loaded successfully",
  "data": {
    "recently_played": [...],
    "favorites": [...],
    "recommended_by_artists": [...],
    "recommended_by_mood": [...],
    "trending": [...],
    "new_releases": [...],
    "popular_in_your_language": [...]
  }
}
```

---

## 🎵 Music Browsing & Streaming

### List All Music
**Endpoint:** `GET /music/`  
**Authentication:** Optional  
**Query Parameters:**
- `language` - Filter by language (ENGLISH, ARABIC, INSTRUMENTAL, BILINGUAL)
- `tags` - Comma-separated tag names (e.g., `feelgood,energetic`)
- `artist_id` - Filter by artist ID
- `album_id` - Filter by album ID
- `page` - Page number
- `page_size` - Results per page (max 100)

**Example:** `GET /music/?language=ARABIC&tags=feelgood,pop&page=1`

### Get Music Details
**Endpoint:** `GET /music/{id}/`  
**Authentication:** Optional

### Stream Music
**Endpoint:** `POST /music/{id}/stream/`  
**Authentication:** Optional (but recommended for tracking)  
**Description:** Stream music and track play count. Automatically adds to recently played for authenticated users.

### Search Music
**Endpoint:** `GET /music/search/?q=search_term`  
**Authentication:** Optional  
**Query Parameters:**
- `q` - Search query (required)
- `language` - Filter by language
- `tags` - Filter by tags

**Example:** `GET /music/search/?q=love&language=ENGLISH&tags=romantic`

### Trending Music
**Endpoint:** `GET /music/trending/`  
**Authentication:** Optional  
**Description:** Get top 20 trending music tracks

### Discover by Mood/Genre
**Endpoint:** `GET /music/discover/?tag=feelgood`  
**Authentication:** Optional  
**Query Parameters:**
- `tag` - Tag name (required)

---

## 🎤 Artists

### List Artists
**Endpoint:** `GET /artists/`  
**Authentication:** Optional  
**Query Parameters:**
- `search` - Search by name or bio
- `ordering` - Sort by `name` or `-created_at`

### Get Artist Details
**Endpoint:** `GET /artists/{id}/`

### Get Artist's Music
**Endpoint:** `GET /artists/{id}/music/`

### Get Artist's Albums
**Endpoint:** `GET /artists/{id}/albums/`

---

## 💿 Albums

### List Albums
**Endpoint:** `GET /albums/`  
**Authentication:** Optional  
**Query Parameters:**
- `search` - Search by title or artist name
- `ordering` - Sort by `title`, `-release_date`, etc.

### Get Album Details
**Endpoint:** `GET /albums/{id}/`

### Get Album Tracks
**Endpoint:** `GET /albums/{id}/tracks/`

---

## 🏷️ Tags (Mood/Genre/Theme)

### List All Tags
**Endpoint:** `GET /tags/`  
**Authentication:** Optional

### Get Tags by Category
**Endpoint:** `GET /tags/by_category/`  
**Response:**
```json
{
  "success": true,
  "data": {
    "MOOD": [...],
    "GENRE": [...],
    "THEME": [...]
  }
}
```

### Get Music by Tag
**Endpoint:** `GET /tags/{id}/music/`

---

## 📝 Playlists

### List Playlists
**Endpoint:** `GET /playlists/`  
**Authentication:** Required  
**Description:** Returns user's own playlists and public playlists

### Get My Playlists
**Endpoint:** `GET /playlists/my_playlists/`  
**Authentication:** Required

### Create Playlist
**Endpoint:** `POST /playlists/`  
**Authentication:** Required  
**Body:**
```json
{
  "name": "My Workout Mix",
  "is_public": false
}
```

### Get Playlist Details
**Endpoint:** `GET /playlists/{id}/`

### Update Playlist
**Endpoint:** `PUT /playlists/{id}/`  
**Authentication:** Required (owner only)

### Delete Playlist
**Endpoint:** `DELETE /playlists/{id}/`  
**Authentication:** Required (owner only)

### Add Track to Playlist
**Endpoint:** `POST /playlists/{id}/add_track/`  
**Authentication:** Required (owner only)  
**Body:**
```json
{
  "music_id": 123
}
```

### Remove Track from Playlist
**Endpoint:** `POST /playlists/{id}/remove_track/`  
**Authentication:** Required (owner only)  
**Body:**
```json
{
  "music_id": 123
}
```

---

## ❤️ Favorites

### List Favorites
**Endpoint:** `GET /favorites/`  
**Authentication:** Required

### Add to Favorites
**Endpoint:** `POST /favorites/`  
**Authentication:** Required  
**Body:**
```json
{
  "music_id": 123
}
```

### Remove from Favorites
**Endpoint:** `DELETE /favorites/remove/`  
**Authentication:** Required  
**Body:**
```json
{
  "music_id": 123
}
```

---

## 🕐 Recently Played

### Get Recently Played
**Endpoint:** `GET /recently-played/`  
**Authentication:** Required  
**Description:** Returns last 50 recently played tracks

---

## 📢 Advertisements

### Get Ads by Placement
**Endpoint:** `GET /ads/by_placement/?placement=HOME_TOP`  
**Authentication:** Optional  
**Query Parameters:**
- `placement` - Ad placement (HOME_TOP, HOME_MIDDLE, PLAYER, SEARCH, PLAYLIST)

**Placements:**
- `HOME_TOP` - Top of home screen
- `HOME_MIDDLE` - Middle of home screen
- `PLAYER` - Music player screen
- `SEARCH` - Search results
- `PLAYLIST` - Playlist view

### Track Ad Impression
**Endpoint:** `POST /ads/{id}/track_impression/`  
**Authentication:** Optional  
**Body:**
```json
{
  "ad_id": 1,
  "session_id": "unique-session-id"
}
```

### Track Ad Click
**Endpoint:** `POST /ads/{id}/track_click/`  
**Authentication:** Optional  
**Body:**
```json
{
  "ad_id": 1,
  "session_id": "unique-session-id"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Click tracked",
  "data": {
    "redirect_url": "https://example.com/ad-destination"
  }
}
```

---

## 👤 User Profile

### Get My Profile
**Endpoint:** `GET /auth/profiles/me/`  
**Authentication:** Required

### Update My Profile
**Endpoint:** `PUT /auth/profiles/me/`  
**Authentication:** Required  
**Body:**
```json
{
  "language": "ar",
  "bio": "Music lover",
  "listening_preferences": {
    "favorite_genres": ["pop", "rock"],
    "preferred_language": "ENGLISH"
  }
}
```

---

## 🔐 Authentication

### Register
**Endpoint:** `POST /auth/register/`  
**Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "password2": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "role": "CUSTOMER"
}
```

### Login
**Endpoint:** `POST /auth/login/`  
**Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "refresh": "refresh_token_here",
    "access": "access_token_here",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "role": "CUSTOMER",
      "is_email_verified": false
    }
  }
}
```

### Refresh Token
**Endpoint:** `POST /auth/token/refresh/`  
**Body:**
```json
{
  "refresh": "refresh_token_here"
}
```

---

## 📊 Response Format

All API responses follow this standard format:

### Success Response
```json
{
  "success": true,
  "message": "Operation successful",
  "data": {}
}
```

### Error Response
```json
{
  "success": false,
  "message": "Error message",
  "errors": {}
}
```

### Paginated Response
```json
{
  "success": true,
  "message": "Data retrieved successfully",
  "data": {
    "count": 100,
    "next": "http://api.example.com/music/?page=2",
    "previous": null,
    "results": [],
    "page_size": 20,
    "total_pages": 5,
    "current_page": 1
  }
}
```

---

## 🌐 Multi-Language Support

The API supports English and Arabic. Set the language preference:

1. **Via Header:**
   ```
   Accept-Language: ar
   ```

2. **Via User Profile:**
   Update your profile's `language` field to `en` or `ar`

All translatable fields will have `_en` and `_ar` versions in the database.

---

## 🎯 Example Use Cases

### 1. Build a Home Screen
```
GET /home/
```
Returns all sections needed for a personalized home screen.

### 2. Search for Arabic Love Songs
```
GET /music/search/?q=love&language=ARABIC&tags=romantic
```

### 3. Create a Workout Playlist
```
POST /playlists/
{
  "name": "Workout Mix",
  "is_public": false
}

POST /playlists/{id}/add_track/
{
  "music_id": 123
}
```

### 4. Discover Energetic Music
```
GET /music/discover/?tag=energetic
```

### 5. Track Music Play
```
POST /music/{id}/stream/
```
This automatically:
- Increments play count
- Adds to recently played
- Updates broadcaster stats

---

## 🔒 Permission Levels

- **Public:** No authentication required
- **Customer:** Requires authentication with CUSTOMER role
- **Broadcaster:** Requires authentication with BROADCASTER role (verified)
- **Admin:** Requires authentication with ADMIN role

---

## 📱 Mobile App Integration Tips

1. **Session Management:** Store JWT tokens securely
2. **Offline Mode:** Cache recently played and favorites
3. **Ad Tracking:** Generate unique session IDs for anonymous users
4. **Language:** Detect device language and set user preference
5. **Pagination:** Use `page_size=50` for better mobile performance
