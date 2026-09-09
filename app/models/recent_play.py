from typing import Any

from pydantic import BaseModel, Field


class RecentPlayRequest(BaseModel):
    user_id: str = Field(..., description="Firebase User ID", example="user_12345")
    song_id: str = Field(..., description="Saavn Song ID", example="UPJYO3v0")


class RecentPlayResponse(BaseModel):
    success: bool = True
    message: str = "Recent play recorded successfully"
    data: dict[str, Any]


class RecentPlaysListResponse(BaseModel):
    success: bool = True
    data: list[dict[str, Any]]
