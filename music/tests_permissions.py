from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from music.models import Music, Artist

User = get_user_model()

class MusicPermissionTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='test@example.com', password='password123', first_name='Test', last_name='User')
        self.artist = Artist.objects.create(name='Test Artist')
        self.music = Music.objects.create(
            title='Test Song',
            uploaded_by=self.user
        )
        self.music.artist.set([self.artist])

    def test_list_music_unauthenticated(self):
        """Test that anyone can see the music list"""
        url = reverse('music-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_music_unauthenticated(self):
        """Test that retrieving music by ID requires authentication"""
        url = reverse('music-detail', kwargs={'pk': self.music.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_music_authenticated(self):
        """Test that authenticated users can retrieve music by ID"""
        self.client.force_authenticate(user=self.user)
        url = reverse('music-detail', kwargs={'pk': self.music.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_trending_music_unauthenticated(self):
        """Test that anyone can see trending music"""
        url = reverse('music-trending')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_music_unauthenticated(self):
        """Test that anyone can search music"""
        url = reverse('music-search')
        response = self.client.get(url, {'q': 'Test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
