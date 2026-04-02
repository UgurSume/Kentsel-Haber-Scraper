"""
MongoDB models for news articles
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class NewsSource(BaseModel):
    """News source model"""
    name: str
    url: str


class Location(BaseModel):
    """Location model"""
    text: Optional[str] = None
    coordinates: Optional[dict] = None  # {"lat": float, "lng": float}
    district: Optional[str] = None


class NewsArticle(BaseModel):
    """News article model"""
    news_type: str
    title: str
    content: str
    cleaned_content: Optional[str] = None
    location: Optional[Location] = None
    publish_date: datetime
    sources: List[NewsSource]
    keywords: List[str] = []
    similarity_hash: Optional[str] = None
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class NewsCreateRequest(BaseModel):
    """Request model for creating news"""
    news_type: str
    title: str
    content: str
    location_text: Optional[str] = None
    publish_date: datetime
    source_name: str
    source_url: str


class NewsFilterRequest(BaseModel):
    """Request model for filtering news"""
    news_type: Optional[str] = None
    district: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0
