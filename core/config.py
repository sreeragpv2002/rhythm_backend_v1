import os
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    PROJECT_NAME: str = "Rhythm Backend"
    API_V1_STR: str = "/api/v1"

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
