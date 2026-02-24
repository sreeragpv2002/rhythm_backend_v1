from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from accounts.models import User
from music.models import Music, Artist, Favorite

class FavoriteToggleTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@favorite@example.com', password='password123')
        self.client.force_authenticate(user=self.user)
        
        # Ensure profile exists (if signal doesn't handle it)
        if not hasattr(self.user, 'profile'):
            from accounts.models import Profile
            Profile.objects.create(user=self.user)

        self.artist = Artist.objects.create(name='Test Artist')
        self.music = Music.objects.create(title='Test Song', audio_url='http://example.com/audio.mp3')
        self.music.artist.add(self.artist)
        
        self.url = reverse('music-favorite', kwargs={'pk': self.music.id})

    def test_favorite_toggle_add(self):
        """Test adding a song to favorites"""
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['action'], 'added')
        self.assertEqual(response.data['is_favorite'], True)
        self.assertTrue(Favorite.objects.filter(user=self.user, music=self.music).exists())

    def test_favorite_toggle_remove(self):
        """Test removing a song from favorites"""
        # First add it
        Favorite.objects.create(user=self.user, music=self.music)
        
        # Then toggle (remove)
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['action'], 'removed')
        self.assertEqual(response.data['is_favorite'], False)
        self.assertFalse(Favorite.objects.filter(user=self.user, music=self.music).exists())

    def test_favorite_non_existent_music(self):
        """Test toggling favorite for non-existent music"""
        url = reverse('music-favorite', kwargs={'pk': 9999})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_favorite_unauthenticated(self):
        """Test toggling favorite without authentication"""
        self.client.logout()
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
