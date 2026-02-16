import logging
import math
from typing import List, Optional, Tuple, Dict
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import and_, or_, func

from . import schemas, version_constants

__all__ = ['DatabaseManager']

from .bench_finder import OpenStreetMapService

logger = logging.getLogger(version_constants.API_NAME)


class DatabaseManager:
    def __init__(self):
        self._engine = schemas.get_engine()

    @property
    def engine(self) -> Engine:
        return self._engine

    def create_session(self, engine: Engine = None) -> Session:
        return sessionmaker(
            bind=engine if engine else self.engine,
            autoflush=False,
            expire_on_commit=False
        )()

    def create_user(
            self,
            email: str,
            name: str,
            gender: str,
            age: Optional[int] = None,
            bio: Optional[str] = None,
            looking_for_gender: Optional[str] = "both",
            latitude: Optional[float] = None,
            longitude: Optional[float] = None,
    ) -> schemas.User:
        """
        Создание нового пользователя или возврат существующего по email

        Args:
            email: Email пользователя (уникальный идентификатор)
            name: Имя пользователя
            gender: Пол (MALE, FEMALE, OTHER)
            age: Возраст
            bio: О себе
            looking_for_gender: Кого ищет
            latitude: Широта
            longitude: Долгота

        Returns:
            User объект (существующий или новый)
        """
        with self.create_session() as db:
            existing_user = db.query(schemas.User).filter_by(email=email.lower()).first()

            if existing_user:
                logger.info(f"User with email {email} already exists, returning ID {existing_user.id}")
                return existing_user

            new_user = schemas.User(
                email=email.lower(),
                name=name,
                gender=gender,
                age=age,
                bio=bio,
                looking_for_gender=looking_for_gender,
                latitude=latitude,
                longitude=longitude,
            )

            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            logger.info(f"Created new user: {new_user.email} (ID: {new_user.id})")
            return new_user

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Вычисление расстояния между двумя точками по формуле Haversine (в км)

        Args:
            lat1: Широта первой точки
            lon1: Долгота первой точки
            lat2: Широта второй точки
            lon2: Долгота второй точки

        Returns:
            Расстояние в километрах
        """
        R = 6371

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        return R * c

    def get_user(self, user_id: int) -> Optional[schemas.User]:
        """Получить пользователя по ID"""
        with self.create_session() as db:
            return db.query(schemas.User).filter_by(id=user_id).first()

    def get_user_by_email(self, email: str) -> Optional[schemas.User]:
        """
        Получить пользователя по email

        Args:
            email: Email пользователя

        Returns:
            User объект или None
        """
        with self.create_session() as db:
            return db.query(schemas.User).filter_by(email=email.lower()).first()

    def update_user_location(self, user_id: int, latitude: float, longitude: float):
        """Обновить геолокацию пользователя"""
        with self.create_session() as db:
            user = db.query(schemas.User).filter_by(id=user_id).first()
            if user:
                user.latitude = latitude
                user.longitude = longitude
                user.last_active_at = func.now()
                db.commit()

    def update_user_profile(
            self,
            user_id: int,
            name: Optional[str] = None,
            bio: Optional[str] = None,
            looking_for_gender: Optional[str] = None,
            min_age: Optional[int] = None,
            max_age: Optional[int] = None,
            max_distance_km: Optional[int] = None,
    ):
        """Обновить профиль пользователя"""
        with self.create_session() as db:
            user = db.query(schemas.User).filter_by(id=user_id).first()
            if not user:
                return None

            if name is not None:
                user.name = name
            if bio is not None:
                user.bio = bio
            if looking_for_gender is not None:
                user.looking_for_gender = looking_for_gender
            if min_age is not None:
                user.min_age = min_age
            if max_age is not None:
                user.max_age = max_age
            if max_distance_km is not None:
                user.max_distance_km = max_distance_km

            db.commit()
            db.refresh(user)
            return user


    def add_photo(self, user_id: int, url: str, order_index: int = 0) -> schemas.Photo:
        """Добавить фото пользователю"""
        with self.create_session() as db:
            existing_photos = db.query(schemas.Photo).filter_by(user_id=user_id).count()

            new_photo = schemas.Photo(
                user_id=user_id,
                url=url,
                order_index=order_index,
                is_primary=(existing_photos == 0)
            )
            db.add(new_photo)
            db.commit()
            db.refresh(new_photo)
            return new_photo

    def get_user_photos(self, user_id: int) -> List[schemas.Photo]:
        """Получить все фото пользователя"""
        with self.create_session() as db:
            return db.query(schemas.Photo) \
                .filter_by(user_id=user_id) \
                .order_by(schemas.Photo.order_index) \
                .all()

    def delete_photo(self, photo_id: int, user_id: int) -> bool:
        """Удалить фото"""
        with self.create_session() as db:
            photo = db.query(schemas.Photo) \
                .filter_by(id=photo_id, user_id=user_id) \
                .first()
            if photo:
                db.delete(photo)
                db.commit()
                return True
            return False

    def set_primary_photo(self, photo_id: int, user_id: int):
        """Установить главное фото"""
        with self.create_session() as db:
            db.query(schemas.Photo) \
                .filter_by(user_id=user_id) \
                .update({"is_primary": False})

            photo = db.query(schemas.Photo) \
                .filter_by(id=photo_id, user_id=user_id) \
                .first()
            if photo:
                photo.is_primary = True
                db.commit()



    def create_swipe(self, from_user_id: int, to_user_id: int, swipe_type: str) -> Tuple[
        schemas.Swipe, Optional[schemas.Match]]:
        with self.create_session() as db:
            existing = db.query(schemas.Swipe).filter_by(
                from_user_id=from_user_id,
                to_user_id=to_user_id
            ).first()

            if existing:
                if existing.type == swipe_type:
                    return existing, None

                existing.type = swipe_type
                db.commit()
                new_swipe = existing
            else:
                new_swipe = schemas.Swipe(
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    type=swipe_type
                )
                db.add(new_swipe)
                db.commit()

            match_obj = None
            if swipe_type == 'like':
                reverse_swipe = db.query(schemas.Swipe).filter_by(
                    from_user_id=to_user_id,
                    to_user_id=from_user_id,
                    type='like'
                ).first()

                if reverse_swipe:
                    match_obj = self.get_match_between_users(from_user_id, to_user_id)
                    if not match_obj:
                        user_one, user_two = min(from_user_id, to_user_id), max(from_user_id, to_user_id)
                        match_obj = schemas.Match(user_one_id=user_one, user_two_id=user_two)
                        db.add(match_obj)
                        db.commit()
                        db.refresh(match_obj)

            elif swipe_type == 'dislike':
                match_obj = self.get_match_between_users(from_user_id, to_user_id)
                if match_obj:
                    match_obj.is_active = False
                    db.commit()
                    match_obj = None

            return new_swipe, match_obj

    def get_user_matches(self, user_id: int, is_active: bool = True) -> List[schemas.Match]:
        """Получить все мэтчи пользователя"""
        with self.create_session() as db:
            matches = db.query(schemas.Match) \
                .filter(
                or_(
                    schemas.Match.user_one_id == user_id,
                    schemas.Match.user_two_id == user_id
                ),
                schemas.Match.is_active == is_active
            ) \
                .order_by(schemas.Match.created_at.desc()) \
                .all()
            return matches

    def get_match_between_users(self, user_id: int, match_id: int):
        with self.create_session() as db:
            return db.query(schemas.Match).filter(
                schemas.Match.id == match_id,
                schemas.Match.is_active == True,
                or_(
                    schemas.Match.user_one_id == user_id,
                    schemas.Match.user_two_id == user_id
                )
            ).first()

    def unmatch(self, user_id: int, other_user_id: int) -> bool:
        """Размэтчиться (деактивировать мэтч)"""
        with self.create_session() as db:
            user_min = min(user_id, other_user_id)
            user_max = max(user_id, other_user_id)

            match = db.query(schemas.Match) \
                .filter_by(user_one_id=user_min, user_two_id=user_max) \
                .first()

            if match:
                match.is_active = False
                db.commit()
                return True
            return False


    def get_candidate_profiles(self, user_id: int, limit: int = 50) -> List[schemas.User]:
        with self.create_session() as db:
            current_user = db.query(schemas.User).filter_by(id=user_id).first()
            if not current_user:
                return []

            already_swiped_ids = db.query(schemas.Swipe.to_user_id).filter_by(from_user_id=user_id).subquery()

            query = db.query(schemas.User).filter(
                schemas.User.id != user_id,
                schemas.User.is_active == True,
                schemas.User.id.notin_(already_swiped_ids)
            )

            if current_user.min_age and current_user.max_age:
                query = query.filter(
                    and_(
                        schemas.User.age >= current_user.min_age,
                        schemas.User.age <= current_user.max_age
                    )
                )

            return query.limit(limit).all()

    def send_message(
            self,
            match_id: int,
            sender_id: int,
            receiver_id: int,
            message_text: str
    ) -> Optional[schemas.Message]:
        """Отправить сообщение в чате мэтча"""
        with self.create_session() as db:
            match = db.query(schemas.Match) \
                .filter_by(id=match_id, is_active=True) \
                .first()

            if not match:
                return None

            if sender_id not in [match.user_one_id, match.user_two_id]:
                return None
            if receiver_id not in [match.user_one_id, match.user_two_id]:
                return None

            new_message = schemas.Message(
                match_id=match_id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                message_text=message_text
            )
            db.add(new_message)
            db.commit()
            db.refresh(new_message)
            return new_message

    def get_match_messages(
            self,
            match_id: int,
            limit: int = 100
    ) -> List[schemas.Message]:
        """Получить историю сообщений мэтча"""
        with self.create_session() as db:
            messages = db.query(schemas.Message) \
                .filter_by(match_id=match_id) \
                .order_by(schemas.Message.created_at.asc()) \
                .limit(limit) \
                .all()
            return messages

    def mark_messages_as_read(self, match_id: int, user_id: int):
        """Пометить сообщения как прочитанные"""
        with self.create_session() as db:
            db.query(schemas.Message) \
                .filter_by(match_id=match_id, receiver_id=user_id, is_read=False) \
                .update({"is_read": True})
            db.commit()

    def suggest_benches_for_match(
            self,
            match_id: int,
            lat1: float,
            lon1: float,
            lat2: float,
            lon2: float,
            limit: int = 10
    ) -> List[Dict]:
        """
        Предложить скамейки для мэтча

        Args:
            match_id: ID мэтча
            lat1, lon1: Координаты первого пользователя
            lat2, lon2: Координаты второго пользователя
            limit: Количество скамеек

        Returns:
            Список скамеек с расстояниями
        """
        with self.create_session() as db:
            match = db.query(schemas.Match).filter_by(id=match_id).first()
            if not match:
                logger.error(f"Match {match_id} not found")
                return []

            benches = OpenStreetMapService.find_benches_for_match(
                lat1=lat1,
                lon1=lon1,
                lat2=lat2,
                lon2=lon2,
                limit=limit
            )

            if not benches:
                logger.warning("No benches found from OSM")
                return []

            logger.info(f"Found {len(benches)} benches for match {match_id}")

            for bench in benches:
                existing = db.query(schemas.MeetingBench).filter_by(
                    match_id=match_id,
                    osm_id=str(bench['osm_id'])
                ).first()

                if not existing:
                    new_bench = schemas.MeetingBench(
                        match_id=match_id,
                        osm_id=str(bench['osm_id']),
                        osm_type=bench['osm_type'],
                        latitude=bench['lat'],
                        longitude=bench['lon'],
                        distance_user_a_km=bench['distance_user_a_km'],
                        distance_user_b_km=bench['distance_user_b_km'],
                        total_distance_km=bench['total_distance_km'],
                        fairness_diff_km=bench['fairness_diff_km'],
                        score=bench['score'],
                        osm_tags=bench.get('tags', {})
                    )
                    db.add(new_bench)

            db.commit()

            return benches

    def get_suggested_benches(self, match_id: int) -> List[schemas.MeetingBench]:
        """
        Получить сохранённые предложенные скамейки для мэтча

        Args:
            match_id: ID мэтча

        Returns:
            Список объектов MeetingBench из БД
        """
        with self.create_session() as db:
            return db.query(schemas.MeetingBench) \
                .filter_by(match_id=match_id) \
                .order_by(schemas.MeetingBench.score) \
                .all()

    def accept_bench(self, match_id: int, bench_id: int) -> bool:
        """
        Пометить скамейку как принятую пользователями

        Args:
            match_id: ID мэтча
            bench_id: ID скамейки из таблицы meeting_benches

        Returns:
            True если успешно, False если не найдено
        """
        with self.create_session() as db:
            bench = db.query(schemas.MeetingBench).filter_by(
                id=bench_id,
                match_id=match_id
            ).first()

            if bench:
                bench.is_accepted = True
                bench.accepted_at = func.now()
                db.commit()
                return True

            return False

    def get_accepted_bench(self, match_id: int) -> Optional[schemas.MeetingBench]:
        """
        Получить принятую скамейку для мэтча

        Args:
            match_id: ID мэтча

        Returns:
            MeetingBench объект или None
        """
        with self.create_session() as db:
            return db.query(schemas.MeetingBench) \
                .filter_by(match_id=match_id, is_accepted=True) \
                .first()

    def suggest_benches_for_match_auto(
            self,
            match_id: int,
            limit: int = 10
    ) -> List[Dict]:
        """
        Автоматический поиск скамеек для мэтча

        Берёт координаты пользователей из БД (user.latitude, user.longitude)
        и ищет скамейки между ними.

        Args:
            match_id: ID мэтча
            limit: Количество скамеек

        Returns:
            Список скамеек с расстояниями
        """
        with self.create_session() as db:
            match = db.query(schemas.Match).filter_by(id=match_id, is_active=True).first()
            if not match:
                logger.error(f"Match {match_id} not found or inactive")
                return []

            user_a = db.query(schemas.User).filter_by(id=match.user_one_id).first()
            user_b = db.query(schemas.User).filter_by(id=match.user_two_id).first()

            if not (user_a and user_b):
                logger.error(f"Users not found for match {match_id}")
                return []

            if not all([user_a.latitude, user_a.longitude, user_b.latitude, user_b.longitude]):
                logger.warning(
                    f"Missing coordinates for match {match_id}: "
                    f"User {user_a.id}: ({user_a.latitude}, {user_a.longitude}), "
                    f"User {user_b.id}: ({user_b.latitude}, {user_b.longitude})"
                )
                return []

            logger.info(
                f"Searching benches for match {match_id}: "
                f"User {user_a.id} at ({user_a.latitude}, {user_a.longitude}), "
                f"User {user_b.id} at ({user_b.latitude}, {user_b.longitude})"
            )

            benches = OpenStreetMapService.find_benches_for_match(
                lat1=user_a.latitude,
                lon1=user_a.longitude,
                lat2=user_b.latitude,
                lon2=user_b.longitude,
                limit=limit
            )

            if not benches:
                logger.warning(f"No benches found from OSM for match {match_id}")
                return []

            logger.info(f"Found {len(benches)} benches for match {match_id}")

            for bench in benches:
                existing = db.query(schemas.MeetingBench).filter_by(
                    match_id=match_id,
                    osm_id=str(bench['osm_id'])
                ).first()

                if not existing:
                    new_bench = schemas.MeetingBench(
                        match_id=match_id,
                        osm_id=str(bench['osm_id']),
                        osm_type=bench['osm_type'],
                        latitude=bench['lat'],
                        longitude=bench['lon'],
                        distance_user_a_km=bench['distance_user_a_km'],
                        distance_user_b_km=bench['distance_user_b_km'],
                        total_distance_km=bench['total_distance_km'],
                        fairness_diff_km=bench['fairness_diff_km'],
                        score=bench['score'],
                        osm_tags=bench.get('tags', {})
                    )
                    db.add(new_bench)

            db.commit()

            return benches