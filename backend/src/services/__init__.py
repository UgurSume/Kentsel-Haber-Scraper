"""Services package"""
from .nlp_service import nlp_service

try:
	from .geocoding_service import geocoding_service
except Exception:  # pragma: no cover - optional dependency during unit tests
	geocoding_service = None

try:
	from .similarity_service import similarity_service
except Exception:  # pragma: no cover - optional dependency during unit tests
	similarity_service = None

__all__ = ["nlp_service", "geocoding_service", "similarity_service"]
