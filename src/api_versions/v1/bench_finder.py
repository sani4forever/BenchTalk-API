"""
Поиск скамеек через OpenStreetMap для мэтчей
"""

import requests
import math
import logging
from typing import List, Dict, Tuple

from . import version_constants

logger = logging.getLogger(version_constants.API_NAME)


class OpenStreetMapService:
    """Сервис для работы с OpenStreetMap Overpass API"""

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    TIMEOUT = 30

    @classmethod
    def find_benches_for_match(
            cls,
            lat1: float, lon1: float,
            lat2: float, lon2: float,
            limit: int = 10
    ) -> List[Dict]:
        """
        Найти скамейки для встречи двух пользователей (метод CIRCLE)

        Args:
            lat1, lon1: Координаты первого пользователя
            lat2, lon2: Координаты второго пользователя
            limit: Максимум результатов

        Returns:
            Список скамеек с координатами и расстояниями
        """
        try:
            center_lat, center_lon, radius_m = cls._calculate_search_zone(
                lat1, lon1, lat2, lon2
            )

            logger.info(
                f"Searching benches: center=({center_lat:.4f}, {center_lon:.4f}), "
                f"radius={radius_m}m"
            )

            benches = cls._query_overpass(center_lat, center_lon, radius_m)

            if not benches:
                logger.warning("No benches found in OSM")
                return []

            logger.info(f"Found {len(benches)} benches from OSM")

            ranked = cls._rank_benches(benches, lat1, lon1, lat2, lon2)

            return ranked[:limit]

        except Exception as e:
            logger.error(f"Error finding benches: {e}", exc_info=True)
            return []

    @classmethod
    def _calculate_search_zone(
            cls,
            lat1: float, lon1: float,
            lat2: float, lon2: float
    ) -> Tuple[float, float, int]:
        """
        Вычислить центр и радиус окружности для поиска

        Returns:
            (center_lat, center_lon, radius_meters)
        """
        center_lat = (lat1 + lat2) / 2
        center_lon = (lon1 + lon2) / 2

        distance_km = cls._haversine(lat1, lon1, lat2, lon2)

        radius_km = distance_km / 2 + 1.0
        radius_meters = int(radius_km * 1000)

        max_radius_m = 5000
        radius_meters = min(radius_meters, max_radius_m)

        return center_lat, center_lon, radius_meters

    @classmethod
    def _query_overpass(
            cls,
            center_lat: float,
            center_lon: float,
            radius_meters: int
    ) -> List[Dict]:
        """
        Выполнить запрос к Overpass API

        Returns:
            Список элементов из OSM
        """
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="bench"](around:{radius_meters},{center_lat},{center_lon});
          way["amenity"="bench"](around:{radius_meters},{center_lat},{center_lon});
        );
        out center;
        """

        try:
            response = requests.get(
                cls.OVERPASS_URL,
                params={'data': query},
                timeout=cls.TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            elements = data.get('elements', [])

            return elements

        except requests.exceptions.Timeout:
            logger.error("Overpass API timeout")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Overpass API request error: {e}")
            return []
        except ValueError as e:
            logger.error(f"Invalid JSON response from Overpass: {e}")
            return []

    @classmethod
    def _rank_benches(
            cls,
            benches: List[Dict],
            lat1: float, lon1: float,
            lat2: float, lon2: float
    ) -> List[Dict]:
        """
        Ранжировать скамейки по оптимальности

        Критерии:
        1. Минимальное суммарное расстояние
        2. Справедливость (минимальная разница расстояний)
        """
        ranked = []

        for bench in benches:
            b_lat = bench.get('lat') or bench.get('center', {}).get('lat')
            b_lon = bench.get('lon') or bench.get('center', {}).get('lon')

            if not (b_lat and b_lon):
                continue

            d1 = cls._haversine(b_lat, b_lon, lat1, lon1)
            d2 = cls._haversine(b_lat, b_lon, lat2, lon2)

            total_distance = d1 + d2
            distance_diff = abs(d1 - d2)

            score = total_distance + distance_diff * 0.5

            ranked.append({
                'osm_id': str(bench.get('id')),
                'osm_type': bench.get('type'),
                'lat': round(b_lat, 6),
                'lon': round(b_lon, 6),
                'distance_user_a_km': round(d1, 3),
                'distance_user_b_km': round(d2, 3),
                'total_distance_km': round(total_distance, 3),
                'fairness_diff_km': round(distance_diff, 3),
                'score': round(score, 3),
                'tags': bench.get('tags', {})
            })

        ranked.sort(key=lambda x: x['score'])

        return ranked

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Вычислить расстояние между двумя точками (км)

        Формула Haversine для сферы
        """
        R = 6371

        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))

        return R * c