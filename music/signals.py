from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

def clear_user_home_cache(user_id):
    """Clear home feed cache for a specific user"""
    languages = ['en', 'ar']
    for lang in languages:
        # We need to clear all possible versions or just clear the current one.
        # However, since versioning is global, clearing the specific user key is enough.
        # But we don't know the version here easily without another cache look up.
        # For simplicity, if we clear the user key, we should also consider the version.
        version = cache.get("home_feed_version", 1)
        cache_key = f"home_feed_{user_id}_{lang}_{version}"
        cache.delete(cache_key)

def clear_all_home_caches():
    """Increment global version to invalidate all home feeds"""
    version = cache.get("home_feed_version", 1)
    # Using incr if it exists, but set is safer across all backends
    cache.set("home_feed_version", version + 1)

@receiver(post_save, sender='music.Favorite')
@receiver(post_delete, sender='music.Favorite')
def invalidate_favorite_cache(sender, instance, **kwargs):
    clear_user_home_cache(instance.user_id)

@receiver(post_save, sender='music.RecentlyPlayed')
@receiver(post_delete, sender='music.RecentlyPlayed')
def invalidate_recently_played_cache(sender, instance, **kwargs):
    clear_user_home_cache(instance.user_id)

@receiver(post_save, sender='music.Music')
@receiver(post_delete, sender='music.Music')
@receiver(post_save, sender='music.Artist')
@receiver(post_delete, sender='music.Artist')
@receiver(post_save, sender='music.Album')
@receiver(post_delete, sender='music.Album')
@receiver(post_save, sender='music.Tag')
@receiver(post_delete, sender='music.Tag')
def invalidate_global_music_cache(sender, instance, **kwargs):
    clear_all_home_caches()
