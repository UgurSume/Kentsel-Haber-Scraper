"""
Coğrafi kodlama servisi — konum metinlerini koordinata dönüştürür
"""
import googlemaps
import requests
import time
from typing import Optional, Dict
import logging
from src.config import settings

logger = logging.getLogger(__name__)


class GeocodingService:
    """Coğrafi kodlama servisi: Google Maps ve Nominatim (OpenStreetMap)"""

    def __init__(self):
        self.api_key = settings.GOOGLE_MAPS_API_KEY
        self.client = None
        self.cache = {}  # Tekrarlanan sorguları önlemek için belleğe-alma

        if self.api_key and self.api_key != "your_google_maps_api_key_here":
            try:
                self.client = googlemaps.Client(key=self.api_key)
                logger.info("[SUCCESS] Google Maps client initialized")
            except Exception as e:
                logger.error(f"[ERROR] Failed to initialize Google Maps client: {e}")
        else:
            logger.warning("[WARNING] Google Maps API key not configured")

    def geocode_location(self, location_text: str) -> Optional[Dict]:
        """
        Konum metnini koordinata dönüştürür.
        Önce Google Maps dener, başarısız olursa Nominatim (OpenStreetMap) ile devam eder.
        Döndürür: {"lat": float, "lng": float} veya None
        """
        if not location_text:
            return None

        # Önce önbelleğe bak
        cache_key = location_text.lower().strip()
        if cache_key in self.cache:
            logger.info(f"[ÖNBELLEĞ] Konum: {location_text}")
            return self.cache[cache_key]

        coordinates = None

        # 1. Google Maps'i dene
        if self.client:
            coordinates = self._google_geocode(location_text)

        # 2. Google başarısız olursa Nominatim'e düş
        if coordinates is None:
            coordinates = self._nominatim_geocode(location_text)

        if coordinates:
            self.cache[cache_key] = coordinates

        return coordinates

    def _google_geocode(self, location_text: str) -> Optional[Dict]:
        """Google Maps API ile koordinat bulma."""
        try:
            full_location = f"{location_text}, Kocaeli, Turkey"
            result = self.client.geocode(full_location)
            if result and len(result) > 0:
                loc = result[0]['geometry']['location']
                coordinates = {"lat": loc['lat'], "lng": loc['lng']}
                logger.info(f"[GOOGLE] Geocoded: {location_text} -> {coordinates}")
                return coordinates
            else:
                logger.warning(f"[GOOGLE] No results for: {location_text}")
                return None
        except Exception as e:
            logger.error(f"[GOOGLE] Geocoding failed for {location_text}: {e}")
            return None

    def _nominatim_geocode(self, location_text: str) -> Optional[Dict]:
        """Nominatim (OpenStreetMap) ile koordinat bulma — API anahtarı gerekmez."""
        try:
            full_location = f"{location_text}, Kocaeli, Turkey"
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": full_location,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "tr",
                    "addressdetails": 0,
                },
                headers={"User-Agent": "KentselHaberScraper/1.0 (educational project)"},
                timeout=10,
            )
            data = response.json()
            if data:
                coordinates = {
                    "lat": float(data[0]["lat"]),
                    "lng": float(data[0]["lon"]),
                }
                logger.info(f"[NOMINATIM] Koordinat: {location_text} -> {coordinates}")
                # Nominatim kullanım koşulları: saniyede en fazla 1 istek
                time.sleep(1)
                return coordinates
            else:
                logger.warning(f"[NOMINATIM] No results for: {location_text}")
                return None
        except Exception as e:
            logger.error(f"[NOMINATIM] Geocoding failed for {location_text}: {e}")
            return None

    def reverse_geocode(self, lat: float, lng: float) -> Optional[str]:
        """
        Convert coordinates to address
        Returns: address string or None
        """
        if not self.client:
            return None

        try:
            result = self.client.reverse_geocode((lat, lng))

            if result and len(result) > 0:
                address = result[0]['formatted_address']
                logger.info(f"[SUCCESS] Reverse geocoded: ({lat}, {lng}) -> {address}")
                return address
            else:
                return None

        except Exception as e:
            logger.error(f"[ERROR] Reverse geocoding failed: {e}")
            return None

    def clear_cache(self):
        """Clear the geocoding cache"""
        self.cache.clear()
        logger.info("[INFO] Geocoding cache cleared")


# Global geocoding service instance
geocoding_service = GeocodingService()
