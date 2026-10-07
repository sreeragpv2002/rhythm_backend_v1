import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    PROJECT_NAME: str = "Rhythm Backend"
    API_V1_STR: str = "/api/v1"

    # Server Port & Environment (Render injects PORT and sets RENDER=true)
    PORT: int = int(os.getenv("PORT", "8000"))
    IS_RENDER: bool = os.getenv("RENDER", "").lower() in ("true", "1")

    # yt-dlp behavior: enabled on localhost, disabled on cloud datacenter servers unless explicitly overridden
    ENABLE_YTDLP: bool = os.getenv("ENABLE_YTDLP", "true").lower() not in ("false", "0", "no")
    ENABLE_SERVER_YTDLP: bool = os.getenv(
        "ENABLE_SERVER_YTDLP",
        "false" if os.getenv("RENDER", "").lower() in ("true", "1") else "true"
    ).lower() in ("true", "1")

    # JioSaavn API Configuration
    SAAVN_BASE_URL: str = os.getenv("SAAVN_BASE_URL", "https://saavn.sumit.co")

    # Cache Configuration (1 day = 86400 seconds)
    HOME_CACHE_TTL_SECONDS: int = int(os.getenv("HOME_CACHE_TTL_SECONDS", "86400"))

    # Firebase Configuration
    FIREBASE_CREDENTIALS_PATH: str = os.getenv(
        "FIREBASE_CREDENTIALS_PATH",
        str(BASE_DIR / "credentials" / "firebase-service-account.json")
    )

# Ensure native resolver for gRPC before any gRPC/Firebase imports
os.environ.setdefault("GRPC_DNS_RESOLVER", "native")

settings = Settings()

