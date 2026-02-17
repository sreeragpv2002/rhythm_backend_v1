from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.translation import gettext_lazy as _


def validate_audio_file_size(file):
    """Validate audio file size"""
    max_size = settings.MAX_AUDIO_FILE_SIZE
    if file.size > max_size:
        raise ValidationError(
            _('Audio file size cannot exceed %(max_size)s MB'),
            params={'max_size': max_size // (1024 * 1024)},
        )


def validate_image_file_size(file):
    """Validate image file size"""
    max_size = settings.MAX_IMAGE_FILE_SIZE
    if file.size > max_size:
        raise ValidationError(
            _('Image file size cannot exceed %(max_size)s MB'),
            params={'max_size': max_size // (1024 * 1024)},
        )
