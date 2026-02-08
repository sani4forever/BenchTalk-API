"""
Pydantic models for Dating App API.
"""
from datetime import datetime
from typing import List

from pydantic import EmailStr
from pydantic import BaseModel, Field
from typing import Optional, Dict



class Error(BaseModel):
    error: str

class UserCreateRequest(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя (уникальный)")  # ДОБАВЛЕНО
    name: str = Field(..., min_length=1, max_length=255)
    gender: str = Field(..., pattern="^(MALE|FEMALE|OTHER)$")
    age: Optional[int] = Field(None, ge=18, le=100)
    bio: Optional[str] = Field(None, max_length=1000)
    looking_for_gender: Optional[str] = Field("both", pattern="^(MALE|FEMALE|OTHER|both)$")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class UserProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    bio: Optional[str] = Field(None, max_length=1000)
    looking_for_gender: Optional[str] = Field(None, pattern="^(MALE|FEMALE|OTHER|both)$")
    min_age: Optional[int] = Field(None, ge=18, le=100)
    max_age: Optional[int] = Field(None, ge=18, le=100)
    max_distance_km: Optional[int] = Field(None, ge=1, le=500)


class LocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class PhotoResponse(BaseModel):
    id: int
    url: str
    order_index: int
    is_primary: bool

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    gender: str
    bio: Optional[str] = None
    age: Optional[int] = None
    photos: Optional[List[PhotoResponse]] = []
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileResponse(UserResponse):
    """Расширенная информация о профиле (для просмотра кандидатов)"""
    distance_km: Optional[float] = None
    looking_for_gender: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None

class PhotoUploadRequest(BaseModel):
    url: str = Field(..., max_length=512)
    order_index: Optional[int] = 0


class SwipeRequest(BaseModel):
    to_user_id: int = Field(..., gt=0)
    type: str = Field(..., pattern="^(like|dislike)$")


class SwipeResponse(BaseModel):
    swipe_id: int
    is_match: bool
    match_id: Optional[int] = None


class MatchUserInfo(BaseModel):
    """Краткая информация о партнере по мэтчу"""
    id: int
    name: str
    age: Optional[int] = None
    primary_photo_url: Optional[str] = None


class MatchResponse(BaseModel):
    id: int
    user: MatchUserInfo
    created_at: datetime
    unread_messages_count: int = 0

    class Config:
        from_attributes = True


class MessageSendRequest(BaseModel):
    match_id: int = Field(..., gt=0)
    text: str = Field(..., min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    message_text: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    match_id: int
    messages: List[MessageResponse]


class CandidateProfileResponse(BaseModel):
    """Профиль для свайпов (discovery feed)"""
    id: int
    name: str
    age: Optional[int] = None
    gender: str
    bio: Optional[str] = None
    photos: Optional[List[PhotoResponse]] = []
    distance_km: Optional[float] = None

    class Config:
        from_attributes = True


class BenchSuggestionResponse(BaseModel):
    """Предложенная скамейка для встречи"""
    osm_id: str = Field(..., description="ID из OpenStreetMap")
    osm_type: str = Field(..., description="Тип объекта (node/way)")
    lat: float = Field(..., description="Широта")
    lon: float = Field(..., description="Долгота")
    distance_user_a_km: float = Field(..., description="Расстояние до первого пользователя (км)")
    distance_user_b_km: float = Field(..., description="Расстояние до второго пользователя (км)")
    total_distance_km: float = Field(..., description="Суммарное расстояние (км)")
    fairness_diff_km: float = Field(..., description="Разница расстояний (км)")
    score: float = Field(..., description="Оценка оптимальности (меньше = лучше)")
    tags: Optional[Dict] = Field(default={}, description="Теги из OSM")

    class Config:
        json_schema_extra = {
            "example": {
                "osm_id": "123456789",
                "osm_type": "node",
                "lat": 55.7529,
                "lon": 37.6186,
                "distance_user_a_km": 0.45,
                "distance_user_b_km": 0.52,
                "total_distance_km": 0.97,
                "fairness_diff_km": 0.07,
                "score": 1.01,
                "tags": {
                    "amenity": "bench",
                    "backrest": "yes",
                    "material": "wood"
                }
            }
        }


class BenchAcceptRequest(BaseModel):
    """Запрос на подтверждение скамейки"""
    bench_id: int = Field(..., description="ID скамейки из БД")