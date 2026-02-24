from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import Music, Artist, Album
from accounts.models import User

class SearchAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpassword123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create an artist with English and Arabic names
        self.artist = Artist.objects.create(
            name='Michael Jackson',
            name_en='Michael Jackson',
            name_ar='مايكل جاكسون'
        )
        
        # Create an album with English and Arabic titles
        self.album = Album.objects.create(
            title='Dangerous',
            title_en='Dangerous',
            title_ar='خطير'
        )
        self.album.artist.add(self.artist)
        
        # Create music with English and Arabic titles
        self.music = Music.objects.create(
            title='Jam',
            title_en='Jam',
            title_ar='مربى',
            album=self.album,
            duration=359,
            language='ENGLISH'
        )
        self.music.artist.add(self.artist)

    def test_english_search(self):
        """Test search with English query"""
        url = reverse('music-search')
        response = self.client.get(url, {'q': 'Jam'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if Jam is in the result (it should be)
        results = response.data['data']
        self.assertTrue(any(item['id'] == self.music.id for item in results))

    def test_arabic_search(self):
        """Test search with Arabic query"""
        url = reverse('music-search')
        # Search for "مربى" (Jam in Arabic)
        response = self.client.get(url, {'q': 'مربى'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']
        self.assertTrue(any(item['id'] == self.music.id for item in results), "Arabic search failed to find the music by Arabic title")

    def test_artist_arabic_search(self):
        """Test search with Arabic artist name"""
        url = reverse('music-search')
        # Search for "مايكل جاكسون" (Michael Jackson in Arabic)
        response = self.client.get(url, {'q': 'مايكل جاكسون'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']
        self.assertTrue(any(item['id'] == self.music.id for item in results), "Arabic search failed to find the music by Arabic artist name")

    def test_album_arabic_search(self):
        """Test search with Arabic album title"""
        url = reverse('music-search')
        # Search for "خطير" (Dangerous in Arabic)
        response = self.client.get(url, {'q': 'خطير'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']
        self.assertTrue(any(item['id'] == self.music.id for item in results), "Arabic search failed to find the music by Arabic album title")
