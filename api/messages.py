from django.utils.translation import gettext_lazy as _


# Authentication messages
AUTH_INVALID_CREDENTIALS = _("Invalid credentials")
AUTH_TOKEN_EXPIRED = _("Token has expired")
AUTH_EMAIL_NOT_VERIFIED = _("Email not verified")
AUTH_USER_INACTIVE = _("User account is inactive")
AUTH_REGISTRATION_SUCCESS = _("User registered successfully. Please verify your email.")
AUTH_LOGIN_SUCCESS = _("Login successful")
AUTH_LOGOUT_SUCCESS = _("Logout successful")

# Validation messages
VALIDATION_REQUIRED_FIELD = _("This field is required")
VALIDATION_INVALID_FORMAT = _("Invalid file format")
VALIDATION_FILE_TOO_LARGE = _("File size too large")
VALIDATION_INVALID_EMAIL = _("Invalid email address")
VALIDATION_PASSWORD_MISMATCH = _("Passwords do not match")

# Permission messages
PERMISSION_DENIED = _("You do not have permission to perform this action")
PERMISSION_BROADCASTER_REQUIRED = _("Broadcaster verification required")
PERMISSION_ADMIN_REQUIRED = _("Admin access required")

# Not found messages
NOT_FOUND_MUSIC = _("Music not found")
NOT_FOUND_ARTIST = _("Artist not found")
NOT_FOUND_ALBUM = _("Album not found")
NOT_FOUND_PLAYLIST = _("Playlist not found")
NOT_FOUND_USER = _("User not found")

# Business logic messages
BUSINESS_PLAYLIST_DELETE_ERROR = _("Cannot delete playlist with tracks")
BUSINESS_UPLOAD_LIMIT_EXCEEDED = _("Upload limit exceeded")
BUSINESS_ALREADY_FAVORITED = _("Music already in favorites")
BUSINESS_NOT_FAVORITED = _("Music not in favorites")

# Success messages
SUCCESS_CREATED = _("Created successfully")
SUCCESS_UPDATED = _("Updated successfully")
SUCCESS_DELETED = _("Deleted successfully")
SUCCESS_ADDED = _("Added successfully")
SUCCESS_REMOVED = _("Removed successfully")
SUCCESS_MUSIC_UPLOADED = _("Music uploaded successfully")

