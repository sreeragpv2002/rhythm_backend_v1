import os
import uuid
from datetime import datetime
from typing import Any

# Set gRPC DNS resolver to native to avoid c-ares DNS timeouts on Linux
os.environ.setdefault("GRPC_DNS_RESOLVER", "native")

import firebase_admin
from firebase_admin import auth, credentials, firestore
from firebase_admin.exceptions import FirebaseError

from core.config import settings

_db: firestore.Client | None = None


def initialize_firebase():
    """
    Initializes Firebase Admin SDK as a singleton and returns Firestore client.
    """
    global _db
    if _db is not None:
        return _db

    if not firebase_admin._apps:
        cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if cred_json:
            import json
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
        else:
            cred_path = settings.FIREBASE_CREDENTIALS_PATH
            if not os.path.exists(cred_path):
                raise FileNotFoundError(f"Firebase credentials not found at: {cred_path}")
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db


def get_firestore_db():
    return initialize_firebase()


def get_firestore_user_data(user_id: str) -> dict[str, Any] | None:
    """
    Retrieve user document from Firestore 'users' collection.
    """
    db = get_firestore_db()
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()
    if user_doc.exists:
        return user_doc.to_dict()
    return None


def verify_user_exists(user_id: str) -> bool:
    """
    Verifies if a user exists in Firebase:
    1. Checks Firestore 'users/{user_id}' document.
    2. Fallback: Checks Firebase Auth via UID.
    """
    if not user_id:
        return False

    db = get_firestore_db()
    # 1. Check Firestore document
    user_doc = db.collection("users").document(user_id).get()
    if user_doc.exists:
        return True

    # 2. Check Firebase Authentication
    try:
        user_record = auth.get_user(user_id)
        if user_record:
            return True
    except auth.UserNotFoundError:
        pass
    except FirebaseError:
        pass
    except Exception:
        pass

    return False


def save_recent_play(user_id: str, song_data: dict[str, Any]) -> dict[str, Any]:
    """
    Saves or updates a recently played song in Firestore under:
    users/{user_id}/recent_plays/{song_id}
    """
    db = get_firestore_db()
    song_id = song_data.get("id")
    if not song_id:
        raise ValueError("Song data must include an 'id'")

    doc_ref = db.collection("users").document(user_id).collection("recent_plays").document(song_id)

    # Prepare document data
    data_to_store = {
        **song_data,
        "played_at": firestore.SERVER_TIMESTAMP,
    }

    doc_ref.set(data_to_store, merge=True)

    # Return with current ISO timestamp for response convenience
    result = dict(data_to_store)
    result["played_at"] = datetime.utcnow().isoformat() + "Z"
    return result


def get_recent_plays(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Retrieves recent plays for a user from Firestore ordered by played_at descending.
    """
    db = get_firestore_db()
    recent_ref = db.collection("users").document(user_id).collection("recent_plays")

    # Query ordered by played_at descending
    query = recent_ref.order_by("played_at", direction=firestore.Query.DESCENDING).limit(limit)
    docs = query.stream()

    items = []
    for doc in docs:
        item = doc.to_dict()
        # Convert timestamp to ISO string if present
        if "played_at" in item and item["played_at"] is not None:
            played_at = item["played_at"]
            if hasattr(played_at, "isoformat"):
                item["played_at"] = played_at.isoformat()
            elif hasattr(played_at, "timestamp"):
                item["played_at"] = datetime.utcfromtimestamp(played_at.timestamp()).isoformat() + "Z"
            else:
                item["played_at"] = str(played_at)
        items.append(item)

    return items


def save_user_languages(user_id: str, languages: list[str]) -> dict[str, Any]:
    """
    Saves or updates user's preferred languages in Firestore under:
    users/{user_id}
    """
    db = get_firestore_db()
    user_ref = db.collection("users").document(user_id)
    data_to_store = {
        "languages": languages,
        "languages_updated_at": firestore.SERVER_TIMESTAMP,
    }
    user_ref.set(data_to_store, merge=True)
    return {
        "user_id": user_id,
        "languages": languages,
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }


def get_user_languages(user_id: str) -> list[str]:
    """
    Retrieves user's saved languages from Firestore.
    """
    db = get_firestore_db()
    user_doc = db.collection("users").document(user_id).get()
    if user_doc.exists:
        data = user_doc.to_dict()
        return data.get("languages", [])
    return []


def _format_timestamp(ts: Any) -> str:
    if hasattr(ts, "isoformat"):
        return ts.isoformat()
    elif hasattr(ts, "timestamp"):
        return datetime.utcfromtimestamp(ts.timestamp()).isoformat() + "Z"
    return str(ts) if ts else datetime.utcnow().isoformat() + "Z"


def get_or_create_favorites_playlist(user_id: str) -> dict[str, Any]:
    """
    Ensures the system 'Favorites' playlist exists for user_id at:
    users/{user_id}/playlists/favorites
    """
    db = get_firestore_db()
    pl_ref = db.collection("users").document(user_id).collection("playlists").document("favorites")
    doc = pl_ref.get()
    if doc.exists:
        data = doc.to_dict()
        data["id"] = "favorites"
        return data

    fav_data = {
        "id": "favorites",
        "name": "Favorites",
        "description": "Your favorite tracks",
        "is_favorite": True,
        "user_id": user_id,
        "song_count": 0,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
        "image": "https://c.saavncdn.com/editorial/charts_TrendingSongs_173062_20240408064433_500x500.jpg",
        "image_url": "https://c.saavncdn.com/editorial/charts_TrendingSongs_173062_20240408064433_500x500.jpg",
    }
    pl_ref.set(fav_data)
    result = dict(fav_data)
    result["created_at"] = datetime.utcnow().isoformat() + "Z"
    result["updated_at"] = datetime.utcnow().isoformat() + "Z"
    return result


def create_user_playlist(user_id: str, name: str, description: str | None = None) -> dict[str, Any]:
    """
    Creates a new custom user playlist in Firestore under:
    users/{user_id}/playlists/{playlist_id}
    """
    db = get_firestore_db()
    playlist_id = f"pl_{uuid.uuid4().hex[:12]}"
    pl_ref = db.collection("users").document(user_id).collection("playlists").document(playlist_id)

    now_iso = datetime.utcnow().isoformat() + "Z"
    pl_data = {
        "id": playlist_id,
        "name": name,
        "description": description or "",
        "is_favorite": False,
        "user_id": user_id,
        "song_count": 0,
        "created_at": firestore.SERVER_TIMESTAMP,
        "updated_at": firestore.SERVER_TIMESTAMP,
        "image": "",
        "image_url": "",
    }
    pl_ref.set(pl_data)
    result = dict(pl_data)
    result["created_at"] = now_iso
    result["updated_at"] = now_iso
    return result


def get_user_playlists(user_id: str) -> list[dict[str, Any]]:
    """
    Retrieves all playlists for a user, always ensuring the 'Favorites' playlist
    is included at the top of the list.
    """
    db = get_firestore_db()
    # Guarantee favorites playlist exists
    get_or_create_favorites_playlist(user_id)

    col_ref = db.collection("users").document(user_id).collection("playlists")
    docs = col_ref.stream()

    playlists = []
    favorites_pl = None

    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        if item.get("created_at"):
            item["created_at"] = _format_timestamp(item["created_at"])
        if item.get("updated_at"):
            item["updated_at"] = _format_timestamp(item["updated_at"])

        if item.get("is_favorite") or doc.id == "favorites":
            item["is_favorite"] = True
            favorites_pl = item
        else:
            item["is_favorite"] = False
            playlists.append(item)

    # Sort custom playlists by created_at descending if available
    playlists.sort(key=lambda p: str(p.get("created_at", "")), reverse=True)

    # Place favorites playlist at the very beginning
    if favorites_pl:
        playlists.insert(0, favorites_pl)

    return playlists


def get_user_playlist_details(user_id: str, playlist_id: str, limit: int = 50) -> dict[str, Any] | None:
    """
    Retrieves playlist document and its list of songs ordered by added_at descending.
    """
    db = get_firestore_db()
    if playlist_id == "favorites":
        get_or_create_favorites_playlist(user_id)

    pl_ref = db.collection("users").document(user_id).collection("playlists").document(playlist_id)
    pl_doc = pl_ref.get()
    if not pl_doc.exists:
        return None

    playlist_data = pl_doc.to_dict()
    playlist_data["id"] = playlist_id
    if playlist_data.get("created_at"):
        playlist_data["created_at"] = _format_timestamp(playlist_data["created_at"])
    if playlist_data.get("updated_at"):
        playlist_data["updated_at"] = _format_timestamp(playlist_data["updated_at"])

    # Query songs in subcollection
    songs_ref = pl_ref.collection("songs")
    query = songs_ref.order_by("added_at", direction=firestore.Query.DESCENDING).limit(limit)
    song_docs = query.stream()

    songs = []
    for s_doc in song_docs:
        s_data = s_doc.to_dict()
        s_data["id"] = s_doc.id
        if s_data.get("added_at"):
            s_data["added_at"] = _format_timestamp(s_data["added_at"])
        songs.append(s_data)

    playlist_data["songs"] = songs
    playlist_data["song_count"] = len(songs)

    # If playlist has no cover image or empty, adopt cover from first song
    if (not playlist_data.get("image_url")) and len(songs) > 0:
        first_img = songs[0].get("image_url") or songs[0].get("image")
        if isinstance(first_img, list) and len(first_img) > 0:
            last = first_img[-1]
            first_img = last.get("url", "") if isinstance(last, dict) else str(last)
        if first_img and isinstance(first_img, str):
            playlist_data["image"] = first_img
            playlist_data["image_url"] = first_img

    return playlist_data


def add_song_to_playlist(user_id: str, playlist_id: str, song_data: dict[str, Any]) -> dict[str, Any]:
    """
    Adds a song to the user's playlist subcollection at:
    users/{user_id}/playlists/{playlist_id}/songs/{song_id}
    Updates playlist song_count and updated_at.
    """
    db = get_firestore_db()
    song_id = song_data.get("id")
    if not song_id:
        raise ValueError("Song data must include an 'id'")

    if playlist_id == "favorites":
        get_or_create_favorites_playlist(user_id)

    pl_ref = db.collection("users").document(user_id).collection("playlists").document(playlist_id)
    pl_doc = pl_ref.get()
    if not pl_doc.exists:
        raise ValueError(f"Playlist '{playlist_id}' not found for user '{user_id}'")

    song_ref = pl_ref.collection("songs").document(str(song_id))
    was_existing = song_ref.get().exists

    data_to_store = {
        **song_data,
        "id": str(song_id),
        "added_at": firestore.SERVER_TIMESTAMP,
    }
    song_ref.set(data_to_store, merge=True)

    # Update playlist metadata
    update_fields = {
        "updated_at": firestore.SERVER_TIMESTAMP,
    }
    if not was_existing:
        update_fields["song_count"] = firestore.Increment(1)
        # If playlist has no image, set image string from this first song
        raw_img = song_data.get("image_url") or song_data.get("image")
        img_str = ""
        if isinstance(raw_img, list) and len(raw_img) > 0:
            last = raw_img[-1]
            img_str = last.get("url", "") if isinstance(last, dict) else str(last)
        elif isinstance(raw_img, str):
            img_str = raw_img

        if img_str and not pl_doc.to_dict().get("image_url"):
            update_fields["image"] = img_str
            update_fields["image_url"] = img_str

    pl_ref.update(update_fields)

    result = dict(data_to_store)
    result["added_at"] = datetime.utcnow().isoformat() + "Z"
    return result


def remove_song_from_playlist(user_id: str, playlist_id: str, song_id: str) -> bool:
    """
    Removes a song from a user playlist.
    """
    db = get_firestore_db()
    pl_ref = db.collection("users").document(user_id).collection("playlists").document(playlist_id)
    pl_doc = pl_ref.get()
    if not pl_doc.exists:
        return False

    song_ref = pl_ref.collection("songs").document(str(song_id))
    song_doc = song_ref.get()
    if not song_doc.exists:
        return False

    song_ref.delete()
    pl_ref.update({
        "updated_at": firestore.SERVER_TIMESTAMP,
        "song_count": firestore.Increment(-1)
    })
    return True


def delete_user_playlist(user_id: str, playlist_id: str) -> bool:
    """
    Deletes a custom user playlist and all its songs.
    Blocks deletion of the system 'favorites' playlist.
    """
    if playlist_id == "favorites":
        raise ValueError("The 'Favorites' playlist cannot be deleted.")

    db = get_firestore_db()
    pl_ref = db.collection("users").document(user_id).collection("playlists").document(playlist_id)
    if not pl_ref.get().exists:
        return False

    # Delete all songs in subcollection
    songs = pl_ref.collection("songs").stream()
    for s in songs:
        s.reference.delete()

    pl_ref.delete()
    return True


def is_song_favorited(user_id: str, song_id: str) -> bool:
    """
    Checks if a song is present in the user's favorites playlist.
    """
    db = get_firestore_db()
    song_ref = db.collection("users").document(user_id).collection("playlists").document("favorites").collection("songs").document(str(song_id))
    return song_ref.get().exists
