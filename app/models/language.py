
from pydantic import BaseModel, Field, field_validator

ALLOWED_LANGUAGES = [
    "malayalam",
    "tamil",
    "hindi",
    "kannada",
    "telugu",
    "english",
]

LANGUAGE_METADATA = {
    "malayalam": {
        "id": "malayalam",
        "name": "Malayalam",
        "title": "Malayalam",
        "image": "https://c.saavncdn.com/editorial/charts_Malayalam2000s_160867_20240408063713_500x500.jpg",
        "image_url": "https://c.saavncdn.com/editorial/charts_Malayalam2000s_160867_20240408063713_500x500.jpg",
        "type": "language",
        "subtitle": "Language",
        "language": "malayalam",
    },
    "tamil": {
        "id": "tamil",
        "name": "Tamil",
        "title": "Tamil",
        "image": "https://c.saavncdn.com/editorial/charts_Tamil1990s_190250_20240408062124_500x500.jpg",
        "image_url": "https://c.saavncdn.com/editorial/charts_Tamil1990s_190250_20240408062124_500x500.jpg",
        "type": "language",
        "subtitle": "Language",
        "language": "tamil",
    },
    "hindi": {
        "id": "hindi",
        "name": "Hindi",
        "title": "Hindi",
        "image": "https://c.saavncdn.com/editorial/charts_Hindi1990s_136920_20240408061858_500x500.jpg",
        "image_url": "https://c.saavncdn.com/editorial/charts_Hindi1990s_136920_20240408061858_500x500.jpg",
        "type": "language",
        "subtitle": "Language",
        "language": "hindi",
    },
    "kannada": {
        "id": "kannada",
        "name": "Kannada",
        "title": "Kannada",
        "image": "https://c.saavncdn.com/editorial/charts_Kannada1980s_168899_20240408062140_500x500.jpg",
        "image_url": "https://c.saavncdn.com/editorial/charts_Kannada1980s_168899_20240408062140_500x500.jpg",
        "type": "language",
        "subtitle": "Language",
        "language": "kannada",
    },
    "telugu": {
        "id": "telugu",
        "name": "Telugu",
        "title": "Telugu",
        "image": "https://c.saavncdn.com/editorial/charts_Telugu2000s_119381_20240408063159_500x500.jpg",
        "image_url": "https://c.saavncdn.com/editorial/charts_Telugu2000s_119381_20240408063159_500x500.jpg",
        "type": "language",
        "subtitle": "Language",
        "language": "telugu",
    },
    "english": {
        "id": "english",
        "name": "English",
        "title": "English",
        "image": "https://c.saavncdn.com/editorial/charts_English2010s_178363_20240408065247_500x500.jpg",
        "image_url": "https://c.saavncdn.com/editorial/charts_English2010s_178363_20240408065247_500x500.jpg",
        "type": "language",
        "subtitle": "Language",
        "language": "english",
    },
}


class UserLanguagesRequest(BaseModel):
    user_id: str = Field(..., description="Firebase User ID", example="user_12345")
    languages: list[str] = Field(
        ...,
        description=f"List of selected languages. Allowed languages: {', '.join(ALLOWED_LANGUAGES)}",
        example=["malayalam", "tamil", "english"]
    )

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one language must be selected.")

        normalized = []
        invalid = []
        for lang in v:
            clean = lang.strip().lower()
            if clean in ALLOWED_LANGUAGES:
                if clean not in normalized:
                    normalized.append(clean)
            else:
                invalid.append(lang)

        if invalid:
            raise ValueError(
                f"Invalid language(s): {invalid}. Only the following languages are permitted: {ALLOWED_LANGUAGES}"
            )

        return normalized


class UserLanguagesData(BaseModel):
    user_id: str
    languages: list[str]
    updated_at: str | None = None


class UserLanguagesResponse(BaseModel):
    success: bool = True
    message: str = "User languages updated successfully"
    data: UserLanguagesData


class AvailableLanguagesResponse(BaseModel):
    success: bool = True
    data: list[str] = Field(default_factory=lambda: list(ALLOWED_LANGUAGES))
