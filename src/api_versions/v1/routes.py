"""
Routes for Dating App API version 1.
"""
import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status
from . import crud, models, version_constants

main_router = APIRouter()

db = crud.DatabaseManager()
logger = logging.getLogger('uvicorn.error')

@main_router.get('', include_in_schema=False)
async def root():
    return {'message': f'Dating API {version_constants.API_VERSION} active'}

@main_router.post('/users', response_model=models.UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: models.UserCreateRequest):
    """
    Регистрация пользователя или возврат существующего

    Если пользователь с таким email уже существует - вернёт его ID
    Если нет - создаст нового
    """
    try:
        new_user = db.create_user(
            email=user_data.email,
            name=user_data.name,
            gender=user_data.gender,
            age=user_data.age,
            bio=user_data.bio,
            looking_for_gender=user_data.looking_for_gender,
            latitude=user_data.latitude,
            longitude=user_data.longitude,
        )
        return models.UserResponse.model_validate(new_user)
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@main_router.get('/users/{user_id}', response_model=models.UserResponse)
async def get_user_profile(user_id: int):
    """Получить профиль пользователя по ID"""
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    response = models.UserResponse.model_validate(user)
    response.age = user.age

    return response


@main_router.get('/users/by-email/{email}', response_model=models.UserResponse)
async def get_user_by_email(email: str):
    """
    Получить профиль пользователя по email

    Полезно для проверки существования пользователя перед регистрацией
    """
    user = db.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return models.UserResponse.model_validate(user)


@main_router.patch('/users/{user_id}', response_model=models.UserResponse)
async def update_user_profile(user_id: int, update_data: models.UserProfileUpdate):
    """Обновить настройки профиля"""
    updated_user = db.update_user_profile(
        user_id=user_id,
        name=update_data.name,
        bio=update_data.bio,
        looking_for_gender=update_data.looking_for_gender,
        min_age=update_data.min_age,
        max_age=update_data.max_age,
        max_distance_km=update_data.max_distance_km,
    )

    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    response = models.UserResponse.model_validate(updated_user)
    if updated_user.age:
        response.age = updated_user.age

    return response


@main_router.post('/users/{user_id}/location', status_code=status.HTTP_204_NO_CONTENT)
async def update_location(user_id: int, location: models.LocationUpdate):
    """Обновить геолокацию пользователя"""
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.update_user_location(user_id, location.latitude, location.longitude)
    return

@main_router.post('/users/{user_id}/photos', response_model=models.PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_photo(user_id: int, photo_data: models.PhotoUploadRequest):
    """Добавить фото профиля"""
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    photo = db.add_photo(user_id, photo_data.url, photo_data.order_index)
    return models.PhotoResponse.model_validate(photo)


@main_router.get('/users/{user_id}/photos', response_model=List[models.PhotoResponse])
async def get_user_photos(user_id: int):
    """Получить все фото пользователя"""
    photos = db.get_user_photos(user_id)
    return [models.PhotoResponse.model_validate(p) for p in photos]


@main_router.delete('/users/{user_id}/photos/{photo_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_photo(user_id: int, photo_id: int):
    """Удалить фото"""
    success = db.delete_photo(photo_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Photo not found")
    return


@main_router.post('/users/{user_id}/photos/{photo_id}/set-primary', status_code=status.HTTP_204_NO_CONTENT)
async def set_primary_photo(user_id: int, photo_id: int):
    """Установить главное фото профиля"""
    db.set_primary_photo(photo_id, user_id)
    return

@main_router.get('/users/{user_id}/discover', response_model=List[models.CandidateProfileResponse])
async def discover_profiles(user_id: int, limit: int = 50):
    """
    Получить профили для свайпов
    Фильтруется по полу, возрасту, геолокации, исключая уже просвайпаных
    """
    current_user = db.get_user(user_id)
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    candidates = db.get_candidate_profiles(user_id, limit)

    result = []
    for candidate in candidates:
        candidate_data = models.CandidateProfileResponse.model_validate(candidate)

        if candidate.age:
            candidate_data.age = candidate.age

        if (current_user.latitude and current_user.longitude and
            candidate.latitude and candidate.longitude):
            distance = db.calculate_distance(
                current_user.latitude, current_user.longitude,
                candidate.latitude, candidate.longitude
            )
            candidate_data.distance_km = round(distance, 1)

        result.append(candidate_data)

    return result

@main_router.post('/users/{user_id}/swipe', response_model=models.SwipeResponse)
async def swipe_user(user_id: int, swipe_data: models.SwipeRequest):
    """
    Свайп (лайк или дизлайк)
    Автоматически создает мэтч при взаимном лайке
    """
    current_user = db.get_user(user_id)
    target_user = db.get_user(swipe_data.to_user_id)

    if not current_user:
        raise HTTPException(status_code=404, detail="Current user not found")
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    if user_id == swipe_data.to_user_id:
        raise HTTPException(status_code=400, detail="Cannot swipe yourself")

    try:
        swipe, match = db.create_swipe(
            from_user_id=user_id,
            to_user_id=swipe_data.to_user_id,
            swipe_type=swipe_data.type
        )

        return models.SwipeResponse(
            swipe_id=swipe.id,
            is_match=match is not None,
            match_id=match.id if match else None
        )

    except Exception as e:
        logger.error(f"Swipe error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@main_router.get('/users/{user_id}/matches', response_model=List[models.MatchResponse])
async def get_user_matches(user_id: int):
    """Получить список всех мэтчей пользователя"""
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    matches = db.get_user_matches(user_id)

    result = []
    for match in matches:
        partner_id = match.user_two_id if match.user_one_id == user_id else match.user_one_id
        partner = db.get_user(partner_id)

        if not partner:
            continue

        photos = db.get_user_photos(partner_id)
        primary_photo = next((p.url for p in photos if p.is_primary), None)
        if not primary_photo and photos:
            primary_photo = photos[0].url

        messages = db.get_match_messages(match.id)
        unread_count = sum(1 for m in messages if m.receiver_id == user_id and not m.is_read)

        match_response = models.MatchResponse(
            id=match.id,
            user=models.MatchUserInfo(
                id=partner.id,
                name=partner.name,
                age=partner.age,
                primary_photo_url=primary_photo
            ),
            created_at=match.created_at,
            unread_messages_count=unread_count
        )
        result.append(match_response)

    return result


@main_router.delete('/users/{user_id}/matches/{other_user_id}', status_code=status.HTTP_204_NO_CONTENT)
async def unmatch_user(user_id: int, other_user_id: int):
    """Размэтчиться с пользователем"""
    success = db.unmatch(user_id, other_user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Match not found")
    return

@main_router.post('/messages', response_model=models.MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(message_data: models.MessageSendRequest, sender_id: int):
    """
    Отправить сообщение в чате мэтча
    sender_id обычно берется из JWT-токена аутентификации
    """
    match = db.get_match_between_users(sender_id, message_data.match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found or inactive")

    receiver_id = match.user_two_id if match.user_one_id == sender_id else match.user_one_id

    message = db.send_message(
        match_id=message_data.match_id,
        sender_id=sender_id,
        receiver_id=receiver_id,
        message_text=message_data.text
    )

    if not message:
        raise HTTPException(status_code=403, detail="Cannot send message in this match")

    return models.MessageResponse.model_validate(message)


@main_router.get('/matches/{match_id}/messages', response_model=models.ChatHistoryResponse)
async def get_match_messages(match_id: int, user_id: int, limit: int = 100):
    """
    Получить историю сообщений мэтча
    user_id для проверки прав доступа (обычно из JWT)
    """
    match = db.get_match_between_users(user_id, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    messages = db.get_match_messages(match_id, limit)

    db.mark_messages_as_read(match_id, user_id)

    return models.ChatHistoryResponse(
        match_id=match_id,
        messages=[models.MessageResponse.model_validate(m) for m in messages]
    )


@main_router.get('/health')
async def health_check():
    """Проверка работоспособности API"""
    return {
        "status": "healthy",
        "version": version_constants.API_VERSION,
        "timestamp": datetime.now().isoformat()
    }


@main_router.post('/matches/{match_id}/suggest-benches', response_model=List[models.BenchSuggestionResponse])
async def suggest_meeting_benches(match_id: int, user_id: int, limit: int = 10):
    """
    Предложить скамейки для встречи (мэтч)

    Использует OpenStreetMap для поиска реальных скамеек между пользователями

    Args:
        match_id: ID мэтча
        user_id: ID пользователя (для проверки прав)
        limit: Максимум результатов (default: 10)

    Returns:
        Список скамеек с координатами и расстояниями
    """
    match = db.get_match_between_users(user_id, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found or access denied")

    try:
        benches = db.suggest_benches_for_match(match_id, limit)

        if not benches:
            raise HTTPException(
                status_code=404,
                detail="No benches found. Make sure both users have location set."
            )

        return [models.BenchSuggestionResponse(**bench) for bench in benches]

    except Exception as e:
        logger.error(f"Error suggesting benches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to find benches")


@main_router.get('/matches/{match_id}/benches', response_model=List[models.BenchSuggestionResponse])
async def get_suggested_benches(match_id: int, user_id: int):
    """
    Получить ранее предложенные скамейки для мэтча
    """
    match = db.get_match_between_users(user_id, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    benches = db.get_suggested_benches(match_id)

    return [
        models.BenchSuggestionResponse(
            osm_id=b.osm_id,
            osm_type=b.osm_type,
            lat=b.latitude,
            lon=b.longitude,
            distance_user_a_km=b.distance_user_a_km,
            distance_user_b_km=b.distance_user_b_km,
            total_distance_km=b.total_distance_km,
            fairness_diff_km=b.fairness_diff_km,
            score=b.score,
            tags=b.osm_tags
        )
        for b in benches
    ]


@main_router.post('/matches/{match_id}/benches/{bench_id}/accept', status_code=status.HTTP_204_NO_CONTENT)
async def accept_meeting_bench(match_id: int, bench_id: int, user_id: int):
    """
    Подтвердить выбор скамейки для встречи
    """
    match = db.get_match_between_users(user_id, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    success = db.accept_bench(match_id, bench_id)

    if not success:
        raise HTTPException(status_code=404, detail="Bench not found")

    return

@main_router.get('/benches/search', response_model=List[models.BenchSuggestionResponse])
async def search_benches_between_locations(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
        limit: int = 10
):
    """
    Поиск скамеек между двумя произвольными координатами

    Полезно для тестирования или поиска без создания мэтча

    Example:
        GET /benches/search?lat1=55.7558&lon1=37.6173&lat2=55.7500&lon2=37.6200&limit=5
    """
    from .bench_finder import OpenStreetMapService

    try:
        benches = OpenStreetMapService.find_benches_for_match(
            lat1, lon1, lat2, lon2, limit
        )

        if not benches:
            raise HTTPException(status_code=404, detail="No benches found in this area")

        return [models.BenchSuggestionResponse(**bench) for bench in benches]

    except Exception as e:
        logger.error(f"Bench search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Bench search failed")


@main_router.post('/matches/{match_id}/suggest-benches', response_model=List[models.BenchSuggestionResponse])
async def suggest_meeting_benches(match_id: int, user_id: int, limit: int = 10):
    """
    Предложить скамейки для встречи (мэтч)

    Использует OpenStreetMap для поиска реальных скамеек между пользователями

    Args:
        match_id: ID мэтча
        user_id: ID пользователя (для проверки прав)
        limit: Максимум результатов (default: 10)

    Returns:
        Список скамеек с координатами и расстояниями
    """
    match = db.get_match_between_users(user_id, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found or access denied")

    try:
        benches = db.suggest_benches_for_match(match_id, limit)

        if not benches:
            raise HTTPException(
                status_code=404,
                detail="No benches found. Make sure both users have location set."
            )

        return [models.BenchSuggestionResponse(**bench) for bench in benches]

    except Exception as e:
        logger.error(f"Error suggesting benches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to find benches")


@main_router.get('/matches/{match_id}/benches', response_model=List[models.BenchSuggestionResponse])
async def get_suggested_benches(match_id: int, user_id: int):
    """
    Получить ранее предложенные скамейки для мэтча
    """
    match = db.get_match_between_users(user_id, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    benches = db.get_suggested_benches(match_id)

    return [
        models.BenchSuggestionResponse(
            osm_id=b.osm_id,
            osm_type=b.osm_type,
            lat=b.latitude,
            lon=b.longitude,
            distance_user_a_km=b.distance_user_a_km,
            distance_user_b_km=b.distance_user_b_km,
            total_distance_km=b.total_distance_km,
            fairness_diff_km=b.fairness_diff_km,
            score=b.score,
            tags=b.osm_tags
        )
        for b in benches
    ]


@main_router.post('/matches/{match_id}/benches/{bench_id}/accept', status_code=status.HTTP_204_NO_CONTENT)
async def accept_meeting_bench(match_id: int, bench_id: int, user_id: int):
    """
    Подтвердить выбор скамейки для встречи
    """
    match = db.get_match_between_users(user_id, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    success = db.accept_bench(match_id, bench_id)

    if not success:
        raise HTTPException(status_code=404, detail="Bench not found")

    return

@main_router.get('/benches/search', response_model=List[models.BenchSuggestionResponse])
async def search_benches_between_locations(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
        limit: int = 10
):
    """
    Поиск скамеек между двумя произвольными координатами

    Полезно для тестирования или поиска без создания мэтча

    Example:
        GET /benches/search?lat1=55.7558&lon1=37.6173&lat2=55.7500&lon2=37.6200&limit=5
    """
    from .bench_finder import OpenStreetMapService

    try:
        benches = OpenStreetMapService.find_benches_for_match(
            lat1, lon1, lat2, lon2, limit
        )

        if not benches:
            raise HTTPException(status_code=404, detail="No benches found in this area")

        return [models.BenchSuggestionResponse(**bench) for bench in benches]

    except Exception as e:
        logger.error(f"Bench search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Bench search failed")
