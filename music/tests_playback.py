from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.utils import translation
from accounts.models import User, UserProfile
from music.models import Music, Artist, Favorite, RecentlyPlayed

class MusicPlaybackTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='playback_test@example.com', password='password123')
        UserProfile.objects.get_or_create(user=self.user)
        self.client.force_authenticate(user=self.user)
        
        self.artist = Artist.objects.create(name='Original Artist')
        # Simulate modeltranslation fields if they were there, for now we test default
        # If modeltranslation is active, we can use translation.override
        self.music1 = Music.objects.create(title='Song 1', duration=200)
        self.music1.artist.add(self.artist)
        
        self.music2 = Music.objects.create(title='Song 2', duration=250)
        self.music2.artist.add(self.artist)

    def test_playback_response_format(self):
        url = reverse('music-playback', kwargs={'pk': self.music1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        
        self.assertEqual(data['id'], self.music1.id)
        self.assertEqual(data['title'], 'Song 1')
        self.assertEqual(data['duration_seconds'], 200)
        self.assertEqual(data['next_song_id'], self.music2.id)
        # For music1 (first in DB), previous should wrap to last or null depending on logic
        # Current logic wraps to last global if no previous
        self.assertEqual(data['previous_song_id'], self.music2.id) 
        self.assertEqual(len(data['artists']), 1)
        self.assertEqual(data['artists'][0]['name'], 'Original Artist')

    def test_playback_increments_count(self):
        initial_count = self.music1.play_count
        url = reverse('music-playback', kwargs={'pk': self.music1.id})
        self.client.get(url)
        
        self.music1.refresh_from_db()
        self.assertEqual(self.music1.play_count, initial_count + 1)

    def test_playback_tracks_recently_played(self):
        url = reverse('music-playback', kwargs={'pk': self.music2.id})
        self.client.get(url)
        
        self.assertTrue(RecentlyPlayed.objects.filter(user=self.user, music=self.music2).exists())

    def test_playback_is_favorite(self):
        Favorite.objects.create(user=self.user, music=self.music1)
        url = reverse('music-playback', kwargs={'pk': self.music1.id})
        response = self.client.get(url)
        self.assertTrue(response.data['data']['is_favorite'])

    def test_playback_next_song_album_context(self):
        url = reverse('music-playback', kwargs={'pk': self.music1.id})
        # No context - should default to next song in same album
        response = self.client.get(url)
        self.assertEqual(response.data['data']['next_song_id'], self.music2.id)

    def test_playback_next_song_playlist_context(self):
        from music.models import Playlist
        playlist = Playlist.objects.create(name='Test Playlist', user=self.user)
        playlist.music_tracks.add(self.music1)
        # music2 is not in playlist, add music3
        music3 = Music.objects.create(title='Song 3', duration=300)
        playlist.music_tracks.add(music3)
        
        url = reverse('music-playback', kwargs={'pk': self.music1.id})
        response = self.client.get(f"{url}?playlist_id={playlist.id}")
        
        self.assertEqual(response.data['data']['next_song_id'], music3.id)

    def test_playback_localization_prefix(self):
        # Use a more reliable way to test localization if possible
        # For now, just ensure the endpoint works with language prefix
        url = f'/ar/api/v1/music/{self.music1.id}/playback/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
