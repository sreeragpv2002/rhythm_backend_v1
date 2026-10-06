import asyncio
import logging
from typing import Any

from ytmusicapi import YTMusic

from core.cache import ttl_cache
from core.config import settings

logger = logging.getLogger(__name__)


def parse_languages(lang_str: str | None) -> list[str]:
    """
    Parses comma-separated language strings like 'english, malayalam, tamil'
    into a clean list of language strings ['english', 'malayalam', 'tamil'].
    """
    if not lang_str:
        return []
    return [lang.strip().lower() for lang in lang_str.split(",") if lang.strip()]


def extract_image_url(image_data: Any) -> str:
    """
    Extracts the highest quality image URL string from YouTube Music / thumbnail data.
    Handles lists of thumbnail dicts, nested dicts, or raw string URLs.
    """
    if not image_data:
        return ""
    if isinstance(image_data, str):
        return image_data
    if isinstance(image_data, dict):
        if "url" in image_data:
            return image_data["url"]
        if "thumbnails" in image_data and isinstance(image_data["thumbnails"], list):
            image_data = image_data["thumbnails"]
    if isinstance(image_data, list) and len(image_data) > 0:
        last = image_data[-1]
        if isinstance(last, dict) and "url" in last:
            return last["url"]
        elif isinstance(last, str):
            return last
    return ""


def is_compilation_song(song: dict[str, Any]) -> bool:
    """
    Compatibility filter to check if a song item is from a compilation album or playlist.
    """
    album_name = ""
    album = song.get("album")
    if isinstance(album, dict):
        album_name = (album.get("name") or "").lower()
    elif isinstance(album, str):
        album_name = album.lower()

    compilation_keywords = [
        "top trending", "trending songs", "playlist", "compilation",
        "various artists", "top 50", "top 20", "top 100", "best of 20"
    ]
    return any(kw in album_name for kw in compilation_keywords)


def interleave_results(results_list: list[list[dict[str, Any]]], total_limit: int | None = None) -> list[dict[str, Any]]:
    """
    Round-robin interleaves items from multiple language result groups.
    Ensures every requested language is fairly represented without only showing the first one.
    Deduplicates items by their 'id'.
    """
    if not results_list:
        return []
    if len(results_list) == 1:
        items = results_list[0]
        return items[:total_limit] if total_limit else items

    interleaved = []
    seen_ids = set()
    max_len = max((len(r) for r in results_list), default=0)

    for idx in range(max_len):
        for group in results_list:
            if idx < len(group):
                item = group[idx]
                item_id = item.get("id")
                if item_id and item_id not in seen_ids:
                    seen_ids.add(item_id)
                    interleaved.append(item)
                elif not item_id:
                    interleaved.append(item)

                if total_limit and len(interleaved) >= total_limit:
                    return interleaved

    return interleaved


def normalize_yt_song(item: dict[str, Any], language: str | None = None) -> dict[str, Any]:
    """
    Normalizes a YouTube Music song / video object into Rhythm's canonical song schema.
    """
    video_id = item.get("videoId") or item.get("id") or ""
    title = item.get("title") or item.get("name") or ""

    thumbnails = item.get("thumbnails") or item.get("thumbnail") or item.get("image") or []
    image_url = extract_image_url(thumbnails)

    # Extract artists
    artists = item.get("artists") or []
    artist_names = []
    if isinstance(artists, list):
        for a in artists:
            if isinstance(a, dict) and a.get("name"):
                artist_names.append(a["name"])
            elif isinstance(a, str):
                artist_names.append(a)
    elif isinstance(artists, dict):
        primary = artists.get("primary", [])
        if isinstance(primary, list):
            artist_names = [a.get("name", "") for a in primary if isinstance(a, dict) and a.get("name")]

    subtitle = ", ".join(artist_names) if artist_names else (item.get("author") or item.get("artist") or None)

    album = item.get("album")
    album_name = album.get("name", "") if isinstance(album, dict) else (album or "")
    album_id = album.get("id", "") if isinstance(album, dict) else ""

    duration_sec = item.get("duration_seconds")
    if duration_sec is None and item.get("lengthSeconds"):
        try:
            duration_sec = int(item["lengthSeconds"])
        except (ValueError, TypeError):
            duration_sec = None

    return {
        "id": str(video_id),
        "name": title,
        "title": title,
        "type": "song",
        "image": image_url,
        "image_url": image_url,
        "subtitle": subtitle,
        "artist": subtitle or "",
        "artists": {"primary": artists} if isinstance(artists, list) else artists,
        "album": {"name": album_name, "id": album_id} if album_name else None,
        "duration": duration_sec,
        "duration_formatted": item.get("duration") or item.get("length") or "",
        "language": language or item.get("language"),
        "url": f"https://music.youtube.com/watch?v={video_id}" if video_id else "",
    }


def normalize_yt_playlist(item: dict[str, Any], language: str | None = None) -> dict[str, Any]:
    """
    Normalizes a YouTube Music playlist object into Rhythm's canonical playlist schema.
    """
    pl_id = item.get("browseId") or item.get("id") or item.get("playlistId") or ""
    title = item.get("title") or item.get("name") or ""
    thumbnails = item.get("thumbnails") or item.get("thumbnail") or item.get("image") or []
    image_url = extract_image_url(thumbnails)

    author = item.get("author")
    if isinstance(author, dict):
        author_name = author.get("name", "")
    elif isinstance(author, list) and len(author) > 0:
        first = author[0]
        author_name = first.get("name", "") if isinstance(first, dict) else str(first)
    else:
        author_name = str(author or "")

    return {
        "id": str(pl_id),
        "name": title,
        "title": title,
        "type": "playlist",
        "image": image_url,
        "image_url": image_url,
        "subtitle": author_name or "Playlist",
        "author": author_name,
        "song_count": item.get("itemCount") or item.get("trackCount"),
        "language": language or item.get("language"),
        "url": f"https://music.youtube.com/playlist?list={pl_id}" if pl_id else "",
    }


def normalize_yt_album(item: dict[str, Any], language: str | None = None) -> dict[str, Any]:
    """
    Normalizes a YouTube Music album object into Rhythm's canonical album schema.
    """
    alb_id = item.get("browseId") or item.get("id") or item.get("albumId") or ""
    title = item.get("title") or item.get("name") or ""
    thumbnails = item.get("thumbnails") or item.get("thumbnail") or item.get("image") or []
    image_url = extract_image_url(thumbnails)

    artists = item.get("artists") or []
    artist_names = [a.get("name", "") for a in artists if isinstance(a, dict) and a.get("name")]
    subtitle = ", ".join(artist_names) if artist_names else (item.get("year") or "Album")

    return {
        "id": str(alb_id),
        "name": title,
        "title": title,
        "type": "album",
        "image": image_url,
        "image_url": image_url,
        "subtitle": subtitle,
        "artists": artists,
        "year": item.get("year"),
        "language": language or item.get("language"),
        "url": f"https://music.youtube.com/browse/{alb_id}" if alb_id else "",
    }


def normalize_yt_artist(item: dict[str, Any], language: str | None = None) -> dict[str, Any]:
    """
    Normalizes a YouTube Music artist object into Rhythm's canonical artist schema.
    """
    art_id = item.get("browseId") or item.get("id") or item.get("channelId") or ""
    name = item.get("artist") or item.get("name") or item.get("title") or ""
    thumbnails = item.get("thumbnails") or item.get("thumbnail") or item.get("image") or []
    image_url = extract_image_url(thumbnails)

    return {
        "id": str(art_id),
        "name": name,
        "title": name,
        "type": "artist",
        "image": image_url,
        "image_url": image_url,
        "subtitle": item.get("subscribers") or "Artist",
        "language": language or item.get("language"),
        "url": f"https://music.youtube.com/channel/{art_id}" if art_id else "",
    }


class YTMusicService:
    def __init__(self):
        self._yt: YTMusic | None = None

    @property
    def yt(self) -> YTMusic:
        if self._yt is None:
            self._yt = YTMusic()
        return self._yt

    async def search_songs(self, query: str = "latest songs", limit: int = 10, language: str | None = None) -> list[dict[str, Any]]:
        """
        Search for songs on YouTube Music, cached for 1 day.
        """
        cache_key = f"yt_search_songs:{query}:{limit}:{language or 'all'}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            fetch_limit = max(limit, 10)
            full_query = f"{language} {query}" if language and language.lower() not in query.lower() else query
            try:
                raw = self.yt.search(query=full_query, filter="songs", limit=fetch_limit)
                results = [normalize_yt_song(item, language=language) for item in raw]
                return results[:limit]
            except Exception as e:
                logger.error(f"Error in search_songs for '{full_query}': {e}")
                return []

        results = await asyncio.to_thread(_fetch)
        if results:
            ttl_cache.set(cache_key, results, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return results

    async def search_playlists(self, query: str = "Top Playlists", limit: int = 10, language: str | None = None) -> list[dict[str, Any]]:
        """
        Search for playlists on YouTube Music, cached for 1 day.
        """
        cache_key = f"yt_search_playlists:{query}:{limit}:{language or 'all'}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            fetch_limit = max(limit, 10)
            full_query = f"{language} {query}" if language and language.lower() not in query.lower() else query
            try:
                raw = self.yt.search(query=full_query, filter="playlists", limit=fetch_limit)
                results = [normalize_yt_playlist(item, language=language) for item in raw]
                return results[:limit]
            except Exception as e:
                logger.error(f"Error in search_playlists for '{full_query}': {e}")
                return []

        results = await asyncio.to_thread(_fetch)
        if results:
            ttl_cache.set(cache_key, results, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return results

    async def search_albums(self, query: str = "Top Albums", limit: int = 10, language: str | None = None) -> list[dict[str, Any]]:
        """
        Search for albums on YouTube Music, cached for 1 day.
        """
        cache_key = f"yt_search_albums:{query}:{limit}:{language or 'all'}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            fetch_limit = max(limit, 10)
            full_query = f"{language} {query}" if language and language.lower() not in query.lower() else query
            try:
                raw = self.yt.search(query=full_query, filter="albums", limit=fetch_limit)
                results = [normalize_yt_album(item, language=language) for item in raw]
                return results[:limit]
            except Exception as e:
                logger.error(f"Error in search_albums for '{full_query}': {e}")
                return []

        results = await asyncio.to_thread(_fetch)
        if results:
            ttl_cache.set(cache_key, results, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return results

    async def search_artists(self, query: str = "Top Artists", limit: int = 10, language: str | None = None) -> list[dict[str, Any]]:
        """
        Search for artists on YouTube Music, cached for 1 day.
        """
        cache_key = f"yt_search_artists:{query}:{limit}:{language or 'all'}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            fetch_limit = max(limit, 10)
            full_query = f"{language} {query}" if language and language.lower() not in query.lower() else query
            try:
                raw = self.yt.search(query=full_query, filter="artists", limit=fetch_limit)
                results = [normalize_yt_artist(item, language=language) for item in raw]
                return results[:limit]
            except Exception as e:
                logger.error(f"Error in search_artists for '{full_query}': {e}")
                return []

        results = await asyncio.to_thread(_fetch)
        if results:
            ttl_cache.set(cache_key, results, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return results

    async def fetch_home_sections(self, language: str | None = None, limit: int = 10) -> dict[str, list[dict[str, Any]]]:
        """
        Fetches trending songs, featured playlists, trending albums, and top artists.
        Supports single or multiple comma-separated languages (e.g. 'english, malayalam, tamil').
        When multiple languages are provided, fetches items for all languages and round-robin interleaves them.
        Caches the combined sections for 1 day (settings.HOME_CACHE_TTL_SECONDS = 86400s).
        """
        langs = parse_languages(language)
        normalized_langs = ",".join(sorted(langs)) if langs else "all"
        cache_key = f"yt_home_sections:{normalized_langs}:{limit}"

        cached_sections = ttl_cache.get(cache_key)
        if cached_sections is not None:
            logger.info(f"Serving YouTube Music home sections from cache (key: {cache_key})")
            return cached_sections

        if len(langs) <= 1:
            lang = langs[0] if langs else None
            song_query = f"{lang} top hit songs" if lang else "top hit songs"
            playlist_query = f"{lang} top playlists" if lang else "top playlists"
            album_query = f"{lang} top albums" if lang else "top albums"
            artist_query = f"{lang} top artists" if lang else "top artists"

            songs, playlists, albums, artists = await asyncio.gather(
                self.search_songs(query=song_query, limit=limit, language=lang),
                self.search_playlists(query=playlist_query, limit=limit, language=lang),
                self.search_albums(query=album_query, limit=limit, language=lang),
                self.search_artists(query=artist_query, limit=limit, language=lang),
                return_exceptions=True
            )

            sections = {
                "trending_songs": songs if isinstance(songs, list) else [],
                "featured_playlists": playlists if isinstance(playlists, list) else [],
                "trending_albums": albums if isinstance(albums, list) else [],
                "top_artists": artists if isinstance(artists, list) else [],
            }
        else:
            fetch_limit = limit
            song_tasks = [self.search_songs(query=f"{lang} top hit songs", limit=fetch_limit, language=lang) for lang in langs]
            playlist_tasks = [self.search_playlists(query=f"{lang} top playlists", limit=fetch_limit, language=lang) for lang in langs]
            album_tasks = [self.search_albums(query=f"{lang} top albums", limit=fetch_limit, language=lang) for lang in langs]
            artist_tasks = [self.search_artists(query=f"{lang} top artists", limit=fetch_limit, language=lang) for lang in langs]

            all_results = await asyncio.gather(
                asyncio.gather(*song_tasks, return_exceptions=True),
                asyncio.gather(*playlist_tasks, return_exceptions=True),
                asyncio.gather(*album_tasks, return_exceptions=True),
                asyncio.gather(*artist_tasks, return_exceptions=True),
            )

            songs_by_lang = [r for r in all_results[0] if isinstance(r, list)]
            playlists_by_lang = [r for r in all_results[1] if isinstance(r, list)]
            albums_by_lang = [r for r in all_results[2] if isinstance(r, list)]
            artists_by_lang = [r for r in all_results[3] if isinstance(r, list)]

            effective_limit = max(limit, len(langs))

            sections = {
                "trending_songs": interleave_results(songs_by_lang, total_limit=effective_limit),
                "featured_playlists": interleave_results(playlists_by_lang, total_limit=effective_limit),
                "trending_albums": interleave_results(albums_by_lang, total_limit=effective_limit),
                "top_artists": interleave_results(artists_by_lang, total_limit=effective_limit),
            }

        if any(len(v) > 0 for v in sections.values()):
            ttl_cache.set(cache_key, sections, ttl=settings.HOME_CACHE_TTL_SECONDS)
            logger.info(f"Cached YouTube Music home sections for 1 day ({settings.HOME_CACHE_TTL_SECONDS}s)")

        return sections

    async def universal_search(self, query: str, limit: int = 10) -> dict[str, Any]:
        """
        Performs a universal search across songs, albums, artists, and playlists.
        """
        cache_key = f"yt_universal_search:{query}:{limit}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            logger.info(f"Serving universal search '{query}' from cache")
            return cached

        songs, playlists, albums, artists = await asyncio.gather(
            self.search_songs(query=query, limit=limit),
            self.search_playlists(query=query, limit=limit),
            self.search_albums(query=query, limit=limit),
            self.search_artists(query=query, limit=limit),
            return_exceptions=True
        )

        clean_songs = songs if isinstance(songs, list) else []
        clean_playlists = playlists if isinstance(playlists, list) else []
        clean_albums = albums if isinstance(albums, list) else []
        clean_artists = artists if isinstance(artists, list) else []

        result = {
            "songs": clean_songs,
            "playlists": clean_playlists,
            "albums": clean_albums,
            "artists": clean_artists,
            "topQuery": clean_songs[:1] if clean_songs else [],
        }

        if any(len(v) > 0 for v in result.values()):
            ttl_cache.set(cache_key, result, ttl=settings.HOME_CACHE_TTL_SECONDS)

        return result

    async def get_song_by_id(self, song_id: str) -> dict[str, Any] | None:
        """
        Retrieves song details by ID, cached for 1 day.
        """
        cache_key = f"yt_song:{song_id}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            # First attempt get_watch_playlist which provides complete track metadata
            try:
                watch = self.yt.get_watch_playlist(videoId=song_id, limit=1)
                tracks = watch.get("tracks", [])
                if tracks:
                    return normalize_yt_song(tracks[0])
            except Exception as e:
                logger.warning(f"get_watch_playlist for {song_id} fallback: {e}")

            # Fallback to get_song
            try:
                song = self.yt.get_song(song_id)
                if song and "videoDetails" in song:
                    vd = song["videoDetails"]
                    return {
                        "id": str(vd.get("videoId", song_id)),
                        "name": vd.get("title", ""),
                        "title": vd.get("title", ""),
                        "type": "song",
                        "image": extract_image_url(vd.get("thumbnail", {}).get("thumbnails", [])),
                        "image_url": extract_image_url(vd.get("thumbnail", {}).get("thumbnails", [])),
                        "subtitle": vd.get("author", ""),
                        "artist": vd.get("author", ""),
                        "duration": int(vd.get("lengthSeconds", 0)) if vd.get("lengthSeconds") else None,
                        "play_count": int(vd.get("viewCount", 0)) if vd.get("viewCount") else None,
                        "url": f"https://music.youtube.com/watch?v={song_id}",
                    }
            except Exception as e:
                logger.error(f"Error fetching song {song_id} from YouTube Music: {e}")
            return None

        song = await asyncio.to_thread(_fetch)
        if song:
            ttl_cache.set(cache_key, song, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return song

    async def get_song_details_with_suggestions(self, song_id: str, limit: int = 10) -> dict[str, Any] | None:
        """
        Retrieves song details along with a list of suggested songs.
        Uses YouTube Music watch playlist recommendations with fallback.
        Cached for 1 day.
        """
        cache_key = f"yt_song_with_suggestions:{song_id}:{limit}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            song_info = None
            suggestions = []

            try:
                watch = self.yt.get_watch_playlist(videoId=song_id, limit=limit + 1)
                tracks = watch.get("tracks", [])
                if tracks:
                    song_info = normalize_yt_song(tracks[0])
                    for t in tracks[1:]:
                        if str(t.get("videoId")) != str(song_id):
                            suggestions.append(normalize_yt_song(t))
                        if len(suggestions) >= limit:
                            break
            except Exception as e:
                logger.warning(f"get_watch_playlist failed for {song_id}: {e}")

            return song_info, suggestions

        song, suggestions = await asyncio.to_thread(_fetch)

        if not song:
            song = await self.get_song_by_id(song_id)
            if not song:
                return None

        if not suggestions:
            artist_name = song.get("artist") or ""
            query_term = f"{artist_name} songs".strip() or "hit songs"
            fallback_items = await self.search_songs(query=query_term, limit=limit + 3)
            suggestions = [s for s in fallback_items if str(s.get("id")) != str(song_id)][:limit]

        result = {
            **song,
            "suggested_songs": suggestions
        }
        ttl_cache.set(cache_key, result, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return result

    async def get_playlist_by_id(self, playlist_id: str, limit: int = 100) -> dict[str, Any] | None:
        """
        Retrieves playlist details and tracks by ID, cached for 1 day.
        """
        cache_key = f"yt_playlist:{playlist_id}:{limit}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            try:
                data = self.yt.get_playlist(playlist_id, limit=limit)
                if not data:
                    return None

                tracks = [normalize_yt_song(t) for t in data.get("tracks", [])]
                image_url = extract_image_url(data.get("thumbnails"))

                author = data.get("author")
                author_name = author.get("name", "") if isinstance(author, dict) else str(author or "")

                return {
                    "id": str(playlist_id),
                    "name": data.get("title", ""),
                    "title": data.get("title", ""),
                    "type": "playlist",
                    "description": data.get("description", ""),
                    "author": author_name,
                    "subtitle": author_name or "Playlist",
                    "year": data.get("year"),
                    "song_count": data.get("trackCount") or len(tracks),
                    "image": image_url,
                    "image_url": image_url,
                    "songs": tracks,
                    "url": f"https://music.youtube.com/playlist?list={playlist_id}",
                }
            except Exception as e:
                logger.error(f"Error fetching playlist {playlist_id}: {e}")
                return None

        playlist = await asyncio.to_thread(_fetch)
        if playlist:
            ttl_cache.set(cache_key, playlist, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return playlist

    async def get_album_by_id(self, album_id: str) -> dict[str, Any] | None:
        """
        Retrieves album details and tracks by ID, cached for 1 day.
        """
        cache_key = f"yt_album:{album_id}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            try:
                data = self.yt.get_album(album_id)
                if not data:
                    return None

                tracks = [normalize_yt_song(t) for t in data.get("tracks", [])]
                image_url = extract_image_url(data.get("thumbnails"))
                artists = data.get("artists", [])
                artist_names = [a.get("name", "") for a in artists if isinstance(a, dict) and a.get("name")]
                subtitle = ", ".join(artist_names) if artist_names else (data.get("year") or "Album")

                return {
                    "id": str(album_id),
                    "name": data.get("title", ""),
                    "title": data.get("title", ""),
                    "type": "album",
                    "description": data.get("description", ""),
                    "artists": artists,
                    "subtitle": subtitle,
                    "year": data.get("year"),
                    "song_count": data.get("trackCount") or len(tracks),
                    "image": image_url,
                    "image_url": image_url,
                    "songs": tracks,
                    "url": f"https://music.youtube.com/browse/{album_id}",
                }
            except Exception as e:
                logger.error(f"Error fetching album {album_id}: {e}")
                return None

        album = await asyncio.to_thread(_fetch)
        if album:
            ttl_cache.set(cache_key, album, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return album

    async def get_artist_by_id(self, artist_id: str, song_count: int = 10, album_count: int = 10) -> dict[str, Any] | None:
        """
        Retrieves artist details, top songs, and albums by ID, cached for 1 day.
        """
        cache_key = f"yt_artist:{artist_id}:{song_count}:{album_count}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            try:
                data = self.yt.get_artist(artist_id)
                if not data:
                    return None

                image_url = extract_image_url(data.get("thumbnails"))

                songs_dict = data.get("songs")
                raw_songs = songs_dict.get("results", []) if isinstance(songs_dict, dict) else []
                top_songs = [normalize_yt_song(s) for s in raw_songs[:song_count]]

                albums_dict = data.get("albums")
                raw_albums = albums_dict.get("results", []) if isinstance(albums_dict, dict) else []
                top_albums = [normalize_yt_album(a) for a in raw_albums[:album_count]]

                return {
                    "id": str(artist_id),
                    "name": data.get("name", ""),
                    "title": data.get("name", ""),
                    "type": "artist",
                    "description": data.get("description", ""),
                    "subscribers": data.get("subscribers"),
                    "subtitle": data.get("subscribers") or "Artist",
                    "image": image_url,
                    "image_url": image_url,
                    "topSongs": top_songs,
                    "top_songs": top_songs,
                    "topAlbums": top_albums,
                    "top_albums": top_albums,
                    "url": f"https://music.youtube.com/channel/{artist_id}",
                }
            except Exception as e:
                logger.error(f"Error fetching artist {artist_id}: {e}")
                return None

        artist = await asyncio.to_thread(_fetch)
        if artist:
            ttl_cache.set(cache_key, artist, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return artist


ytmusic_service = YTMusicService()
# Alias for backwards compatibility
saavn_service = ytmusic_service
