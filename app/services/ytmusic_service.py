import asyncio
import logging
import re
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


def normalize_title_for_comparison(title: str) -> str:
    """
    Normalizes a song title to compare whether two tracks represent the same song.
    Strips brackets, punctuation, common suffixes ('official video', 'lyrical', etc.).
    """
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r"\[.*?\]|\(.*?\)", "", t)
    t = re.sub(
        r"\b(official video|video song|lyrical video|full song|audio song|4k video|remix|hd|visualizer|audio)\b",
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"[^a-z0-9]", "", t)
    return t.strip()


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
        Fetches comprehensive home screen sections:
        - Trending Songs
        - New Malayalam Releases
        - Top Charts
        - Featured Playlists
        - Trending Albums
        - Popular / Top Artists
        - Old Is Gold
        - Default Quick Picks

        Supports single or multiple comma-separated languages (defaulting to Malayalam).
        Caches the combined sections for 1 day (settings.HOME_CACHE_TTL_SECONDS = 86400s).
        """
        langs = parse_languages(language)
        if not langs:
            langs = ["malayalam", "english"]
        normalized_langs = ",".join(sorted(langs))
        cache_key = f"yt_home_sections_v4:{normalized_langs}:{limit}"

        cached_sections = ttl_cache.get(cache_key)
        if cached_sections is not None:
            logger.info(f"Serving YouTube Music home sections from cache (key: {cache_key})")
            return cached_sections

        if len(langs) == 1:
            primary_lang = langs[0]
            trending_q = f"{primary_lang} top hit songs"
            new_releases_q = "malayalam new songs latest releases"
            top_charts_q = f"{primary_lang} top 50 viral hits chart"
            playlists_q = f"{primary_lang} top playlists"
            albums_q = f"{primary_lang} top albums"
            artists_q = f"{primary_lang} top artists singers"
            old_gold_q = "malayalam evergreen old golden hits classic songs" if primary_lang == "malayalam" else f"{primary_lang} classic old golden hits songs"
            quick_picks_q = f"{primary_lang} top picks recommended songs"

            (
                trending_songs,
                new_releases,
                top_charts,
                playlists,
                albums,
                artists,
                old_gold,
                default_quick_picks,
            ) = await asyncio.gather(
                self.search_songs(query=trending_q, limit=limit, language=primary_lang),
                self.search_songs(query=new_releases_q, limit=limit, language="malayalam"),
                self.search_songs(query=top_charts_q, limit=limit, language=primary_lang),
                self.search_playlists(query=playlists_q, limit=limit, language=primary_lang),
                self.search_albums(query=albums_q, limit=limit, language=primary_lang),
                self.search_artists(query=artists_q, limit=limit, language=primary_lang),
                self.search_songs(query=old_gold_q, limit=limit, language=primary_lang),
                self.search_songs(query=quick_picks_q, limit=limit, language=primary_lang),
                return_exceptions=True
            )

            sections = {
                "trending_songs": trending_songs if isinstance(trending_songs, list) else [],
                "new_malayalam_releases": new_releases if isinstance(new_releases, list) else [],
                "top_charts": top_charts if isinstance(top_charts, list) else [],
                "featured_playlists": playlists if isinstance(playlists, list) else [],
                "trending_albums": albums if isinstance(albums, list) else [],
                "popular_artists": artists if isinstance(artists, list) else [],
                "top_artists": artists if isinstance(artists, list) else [],
                "old_is_gold": old_gold if isinstance(old_gold, list) else [],
                "quick_picks_default": default_quick_picks if isinstance(default_quick_picks, list) else [],
            }
        else:
            # Multi-language (e.g. default ["malayalam", "english"] or user's selected languages)
            song_tasks = [self.search_songs(query=f"{lang} top hit songs", limit=limit, language=lang) for lang in langs]
            chart_tasks = [self.search_songs(query=f"{lang} top 50 viral hits chart", limit=limit, language=lang) for lang in langs]
            playlist_tasks = [self.search_playlists(query=f"{lang} top playlists", limit=limit, language=lang) for lang in langs]
            album_tasks = [self.search_albums(query=f"{lang} top albums", limit=limit, language=lang) for lang in langs]
            artist_tasks = [self.search_artists(query=f"{lang} top artists singers", limit=limit, language=lang) for lang in langs]
            quick_tasks = [self.search_songs(query=f"{lang} top picks recommended songs", limit=limit, language=lang) for lang in langs]

            all_multi = await asyncio.gather(
                asyncio.gather(*song_tasks, return_exceptions=True),
                asyncio.gather(*chart_tasks, return_exceptions=True),
                asyncio.gather(*playlist_tasks, return_exceptions=True),
                asyncio.gather(*album_tasks, return_exceptions=True),
                asyncio.gather(*artist_tasks, return_exceptions=True),
                asyncio.gather(*quick_tasks, return_exceptions=True),
                self.search_songs(query="malayalam new songs latest releases", limit=limit, language="malayalam"),
                self.search_songs(query="malayalam evergreen old golden hits classic songs", limit=limit, language="malayalam"),
                return_exceptions=True
            )

            songs_by_lang = [r for r in all_multi[0] if isinstance(r, list)]
            charts_by_lang = [r for r in all_multi[1] if isinstance(r, list)]
            playlists_by_lang = [r for r in all_multi[2] if isinstance(r, list)]
            albums_by_lang = [r for r in all_multi[3] if isinstance(r, list)]
            artists_by_lang = [r for r in all_multi[4] if isinstance(r, list)]
            quick_by_lang = [r for r in all_multi[5] if isinstance(r, list)]
            new_releases = all_multi[6] if isinstance(all_multi[6], list) else []
            old_gold = all_multi[7] if isinstance(all_multi[7], list) else []

            sections = {
                "trending_songs": interleave_results(songs_by_lang, total_limit=limit),
                "new_malayalam_releases": new_releases,
                "top_charts": interleave_results(charts_by_lang, total_limit=limit),
                "featured_playlists": interleave_results(playlists_by_lang, total_limit=limit),
                "trending_albums": interleave_results(albums_by_lang, total_limit=limit),
                "popular_artists": interleave_results(artists_by_lang, total_limit=limit),
                "top_artists": interleave_results(artists_by_lang, total_limit=limit),
                "old_is_gold": old_gold,
                "quick_picks_default": interleave_results(quick_by_lang, total_limit=limit),
            }

        if any(len(v) > 0 for v in sections.values()):
            ttl_cache.set(cache_key, sections, ttl=settings.HOME_CACHE_TTL_SECONDS)
            logger.info(f"Cached YouTube Music home sections for 1 day ({settings.HOME_CACHE_TTL_SECONDS}s)")

        return sections

    async def get_personalized_quick_picks(self, recent_plays: list[dict[str, Any]], language: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        """
        Generates personalized song recommendations:
        - If recent plays exist, suggests songs related to the user's latest played song/artist.
        - Fallbacks to top picks for the requested/Malayalam language.
        """
        primary_lang = (parse_languages(language) or ["malayalam"])[0]
        if recent_plays:
            first_song = recent_plays[0]
            first_song_id = str(first_song.get("id") or "")
            if first_song_id:
                try:
                    details = await self.get_song_details_with_suggestions(first_song_id, limit=limit)
                    if details and details.get("suggested_songs"):
                        recent_ids = {str(s.get("id")) for s in recent_plays}
                        filtered = [s for s in details["suggested_songs"] if str(s.get("id")) not in recent_ids]
                        if filtered:
                            return filtered[:limit]
                except Exception as e:
                    logger.warning(f"Error fetching suggestions for recent song {first_song_id}: {e}")

            artist = first_song.get("artist") or first_song.get("subtitle")
            if artist:
                try:
                    artist_songs = await self.search_songs(query=f"{artist} songs", limit=limit)
                    recent_ids = {str(s.get("id")) for s in recent_plays}
                    filtered = [s for s in artist_songs if str(s.get("id")) not in recent_ids]
                    if filtered:
                        return filtered[:limit]
                except Exception as e:
                    logger.warning(f"Error fetching songs for artist {artist}: {e}")

        return await self.search_songs(query=f"{primary_lang} top picks recommended songs", limit=limit, language=primary_lang)

    async def fetch_category_content(self, query: str, limit: int = 20) -> dict[str, list[dict[str, Any]]]:
        """
        Fetches songs and playlists for a specific mood, activity, or genre category.
        Cached for 1 day.
        """
        cache_key = f"yt_category_content:{query}:{limit}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        songs, playlists = await asyncio.gather(
            self.search_songs(query=query, limit=limit),
            self.search_playlists(query=query, limit=max(limit // 2, 5)),
            return_exceptions=True
        )

        result = {
            "songs": songs if isinstance(songs, list) else [],
            "playlists": playlists if isinstance(playlists, list) else []
        }
        if result["songs"] or result["playlists"]:
            ttl_cache.set(cache_key, result, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return result


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

            # Resilient Fallback for Render / Datacenter IPs: YouTube oEmbed endpoint (no auth or cookies required)
            try:
                import requests
                resp = requests.get(
                    f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={song_id}&format=json",
                    timeout=4.0
                )
                if resp.status_code == 200:
                    oe = resp.json()
                    oe_title = oe.get("title") or ""
                    oe_author = (oe.get("author_name") or "").replace(" - Topic", "").strip()
                    thumb = oe.get("thumbnail_url") or f"https://i.ytimg.com/vi/{song_id}/hqdefault.jpg"
                    return {
                        "id": str(song_id),
                        "name": oe_title,
                        "title": oe_title,
                        "type": "song",
                        "image": thumb,
                        "image_url": thumb,
                        "subtitle": oe_author,
                        "artist": oe_author,
                        "duration": None,
                        "play_count": None,
                        "url": f"https://music.youtube.com/watch?v={song_id}",
                    }
            except Exception as oe_err:
                logger.warning(f"oEmbed metadata fallback failed for {song_id}: {oe_err}")

            return None

        song = await asyncio.to_thread(_fetch)
        if song:
            ttl_cache.set(cache_key, song, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return song

    async def get_song_details_with_suggestions(self, song_id: str, limit: int = 10, user_id: str | None = None) -> dict[str, Any] | None:
        """
        Retrieves song details along with a list of suggested songs.
        Ensures suggested songs:
        1. NEVER contain the currently playing song itself (by ID or normalized title).
        2. NEVER contain songs the user has just played (from Firestore recent_plays when user_id is provided).
        3. Do not contain duplicate titles in suggestions.
        Cached for 1 day.
        """
        cache_key = f"yt_song_with_suggestions_v2:{song_id}:{limit}:{user_id or 'anon'}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        # Fetch basic song details
        song = await self.get_song_by_id(song_id)
        if not song:
            return None

        current_title = song.get("name") or song.get("title") or ""
        current_title_clean = normalize_title_for_comparison(current_title)

        # Excluded IDs and normalized titles
        excluded_ids = {str(song_id)}
        excluded_titles = {current_title_clean} if current_title_clean else set()

        # If user_id is provided, exclude recently played songs
        if user_id:
            try:
                from core.firebase import get_recent_plays
                recent_plays = await asyncio.to_thread(get_recent_plays, user_id, 20)
                if recent_plays:
                    for r in recent_plays:
                        r_id = str(r.get("id") or "")
                        if r_id:
                            excluded_ids.add(r_id)
                        r_title = r.get("name") or r.get("title") or ""
                        r_clean = normalize_title_for_comparison(r_title)
                        if r_clean:
                            excluded_titles.add(r_clean)
            except Exception as e:
                logger.warning(f"Failed to fetch recent plays for suggestions exclusion: {e}")

        fetch_pool_limit = max(limit * 3, 20)

        def _fetch_watch():
            raw_items = []
            try:
                watch = self.yt.get_watch_playlist(videoId=song_id, limit=fetch_pool_limit)
                tracks = watch.get("tracks", [])
                for t in tracks:
                    raw_items.append(normalize_yt_song(t))
            except Exception as e:
                logger.warning(f"get_watch_playlist failed for {song_id}: {e}")
            return raw_items

        raw_suggestions = await asyncio.to_thread(_fetch_watch)

        # Filter out current song and recently played songs
        filtered = []
        seen_titles = set(excluded_titles)

        for s in raw_suggestions:
            s_id = str(s.get("id") or "")
            s_name = s.get("name") or s.get("title") or ""
            s_clean = normalize_title_for_comparison(s_name)

            if s_id in excluded_ids:
                continue
            if s_clean and s_clean in seen_titles:
                continue

            if s_clean:
                seen_titles.add(s_clean)
            filtered.append(s)
            if len(filtered) >= limit:
                break

        # If suggestions drop below limit, fetch extra recommendations from artist/genre
        if len(filtered) < limit:
            artist_name = song.get("artist") or ""
            query_term = f"{artist_name} songs".strip() or "top songs"
            fallback_items = await self.search_songs(query=query_term, limit=limit * 2)
            for fb in fallback_items:
                fb_id = str(fb.get("id") or "")
                fb_name = fb.get("name") or fb.get("title") or ""
                fb_clean = normalize_title_for_comparison(fb_name)

                if fb_id in excluded_ids:
                    continue
                if fb_clean and fb_clean in seen_titles:
                    continue

                if fb_clean:
                    seen_titles.add(fb_clean)
                filtered.append(fb)
                if len(filtered) >= limit:
                    break

        result = {
            **song,
            "suggested_songs": filtered[:limit],
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
