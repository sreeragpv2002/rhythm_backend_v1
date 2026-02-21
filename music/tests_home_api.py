from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from accounts.models import User
from music.models import Music, Artist, RecentlyPlayed, Favorite

class HomeAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='test@example.com', password='password123')
        self.client.force_authenticate(user=self.user)
        
        # Ensure profile exists (if signal doesn't handle it)
        if not hasattr(self.user, 'profile'):
            from accounts.models import Profile
            Profile.objects.create(user=self.user)

        self.artist = Artist.objects.create(name='Test Artist')
        self.music = Music.objects.create(title='Test Song', audio_url='http://example.com/audio.mp3')
        self.music.artist.add(self.artist)
        
        RecentlyPlayed.objects.create(user=self.user, music=self.music)
        Favorite.objects.create(user=self.user, music=self.music)

    def test_home_feed_normalized(self):
        url = reverse('home-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sections', response.data['data'])
        self.assertIn('music_map', response.data['data'])
        
        # Check normalization
        music_id = str(self.music.id)
        self.assertIn(music_id, response.data['data']['music_map'])
        self.assertEqual(response.data['data']['music_map'][music_id]['titles']['en'], 'Test Song')

    def test_home_section_pagination(self):
        url = reverse('home-section', kwargs={'slug': 'trending'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data['data'])
        self.assertTrue(len(response.data['data']['results']) > 0)
