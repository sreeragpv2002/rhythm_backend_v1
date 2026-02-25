from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.cache import cache
from accounts.models import User, UserProfile
from music.models import Music, Artist, Favorite, RecentlyPlayed

class CacheInvalidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='cache_test@example.com', password='password123')
        UserProfile.objects.get_or_create(user=self.user)
        self.client.force_authenticate(user=self.user)
        
        self.artist = Artist.objects.create(name='Original Artist')
        self.music = Music.objects.create(title='Original Song', audio_url='http://example.com/audio.mp3')
        self.music.artist.add(self.artist)
        
        self.home_url = reverse('home-list')
        cache.clear()

    def test_user_specific_cache_invalidation_favorite(self):
        """Test that favoriting a song invalidates the home feed cache for that user"""
        # Initial request to populate cache
        response1 = self.client.get(self.home_url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Verify it's cached (check cache directly for simplicity in tests)
        home_version = cache.get("home_feed_version", 1)
        cache_key = f"home_feed_{self.user.id}_en_{home_version}"
        self.assertIsNotNone(cache.get(cache_key))
        
        # Action: Favorite the song
        Favorite.objects.create(user=self.user, music=self.music)
        
        # Verify cache is cleared for this user
        self.assertIsNone(cache.get(cache_key))
        
        # Request again and check new data (sections should now include favorites)
        response2 = self.client.get(self.home_url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        sections = [s['slug'] for s in response2.data['data']['sections']]
        self.assertIn('favorites', sections)

    def test_global_cache_invalidation_music_update(self):
        """Test that updating a song title invalidates all home feed caches via versioning"""
        # Initial request
        self.client.get(self.home_url)
        
        initial_version = cache.get("home_feed_version", 1)
        
        # Action: Update song title
        self.music.title = "Updated Song Title"
        self.music.save()
        
        # Verify version incremented
        new_version = cache.get("home_feed_version")
        self.assertEqual(new_version, initial_version + 1)
        
        # Verify next request reflects change
        response = self.client.get(self.home_url)
        music_id = str(self.music.id)
        self.assertEqual(response.data['data']['music_map'][music_id]['titles']['en'], "Updated Song Title")

    def test_global_cache_invalidation_artist_delete(self):
        """Test that deleting an artist invalidates caches"""
        self.client.get(self.home_url)
        initial_version = cache.get("home_feed_version", 1)
        
        self.artist.delete()
        
        new_version = cache.get("home_feed_version")
        self.assertEqual(new_version, initial_version + 1)
