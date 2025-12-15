from pydantic import BaseModel, Field
from typing import Optional, List


class Post(BaseModel):
    id: str
    platform: str
    author: str
    author_id: Optional[str] = None
    text: str
    timestamp: Optional[str] = None
    url: Optional[str] = None


class Comment(BaseModel):
    id: str
    post_id: str
    author: str
    text: str
    timestamp: Optional[str] = None


class UserProfile(BaseModel):
    platform: str
    user_id: str
    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
    location: Optional[str] = None


class AnalyzeRequest(BaseModel):
    posts: List[Post] = Field(default_factory=list)
