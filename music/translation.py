from modeltranslation.translator import translator, TranslationOptions
from .models import Artist, Album, Tag, Music, Playlist


class ArtistTranslationOptions(TranslationOptions):
    fields = ('name', 'bio')


class AlbumTranslationOptions(TranslationOptions):
    fields = ('title', 'description')


class TagTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


class MusicTranslationOptions(TranslationOptions):
    fields = ('title',)


class PlaylistTranslationOptions(TranslationOptions):
    fields = ('name',)


translator.register(Artist, ArtistTranslationOptions)
translator.register(Album, AlbumTranslationOptions)
translator.register(Tag, TagTranslationOptions)
translator.register(Music, MusicTranslationOptions)
translator.register(Playlist, PlaylistTranslationOptions)
