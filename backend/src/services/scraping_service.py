"""
Scraping Service for coordinating all news scrapers
"""
from typing import List, Dict
import asyncio
import logging
from datetime import datetime, timedelta
import re
from src.scrapers import (
    CagdasKocaeliScraper,
    OzgurKocaeliScraper,
    SesKocaeliScraper,
    YeniKocaeliScraper,
    BizimYakaScraper
)
from src.services.nlp_service import nlp_service
from src.services.geocoding_service import geocoding_service
from src.services.similarity_service import similarity_service
from src.utils.database import db
from src.models import NewsArticle, NewsSource, Location
from src.config import REQUIRED_NEWS_TYPES, KOCAELISPOR_STADIUM, IZMIT_FALLBACK_CENTER, DEFAULT_SCRAPE_DAYS

try:
    import numpy as np
except ImportError:
    np = None

logger = logging.getLogger(__name__)


class ScrapingService:
    """Service for managing news scraping operations"""

    def __init__(self):
        self.scrapers = [
            CagdasKocaeliScraper(),
            OzgurKocaeliScraper(),
            SesKocaeliScraper(),
            YeniKocaeliScraper(),
            BizimYakaScraper(),
        ]
        self.embedding_candidate_limit = 150
        self.embedding_days_window = 7

    async def scrape_all_sources(self, days: int = DEFAULT_SCRAPE_DAYS) -> Dict:
        """
        Tüm kaynaklardan haber kazır.
        Döndürür: Kazanılan haberlerle ilgili istatistikler.
        """
        logger.info(f"[START] Scraping from {len(self.scrapers)} sources...")

        total_scraped = 0
        total_saved = 0
        total_duplicates = 0
        total_skipped_unclassified = 0
        total_skipped_geocoding = 0
        total_skipped_nonlocal = 0
        errors = []

        for scraper in self.scrapers:
            try:
                logger.info(f"[SCRAPING] {scraper.source_name}...")

                # Selenium kullanan kazıyıcılar engelleme yapar; event loop'u dondurmamak
                # için thread pool'da çalıştırılıyor
                loop = asyncio.get_event_loop()
                articles = await loop.run_in_executor(None, lambda s=scraper: s.scrape(days=days))
                total_scraped += len(articles)

                logger.info(f"[INFO] Found {len(articles)} articles from {scraper.source_name}")

                # Her makaleyi işle ve veritabanına kaydet
                for article_data in articles:
                    try:
                        status = await self.process_and_save_article(article_data, scraper.source_name)
                        if status == "saved":
                            total_saved += 1
                        elif status == "duplicate":
                            total_duplicates += 1
                        elif status == "skipped_unclassified":
                            total_skipped_unclassified += 1
                        elif status == "skipped_geocoding":
                            total_skipped_geocoding += 1
                        elif status == "skipped_nonlocal":
                            total_skipped_nonlocal += 1
                    except Exception as e:
                        logger.error(f"[ERROR] Failed to process article: {e}")
                        errors.append(str(e))

            except Exception as e:
                logger.error(f"[ERROR] Scraper {scraper.source_name} failed: {e}")
                errors.append(f"{scraper.source_name}: {str(e)}")

        logger.info(f"[COMPLETE] Scraping complete: {total_saved} saved, {total_duplicates} duplicates")

        return {
            "total_scraped": total_scraped,
            "total_saved": total_saved,
            "total_duplicates": total_duplicates,
            "total_skipped_unclassified": total_skipped_unclassified,
            "total_skipped_geocoding": total_skipped_geocoding,
            "total_skipped_nonlocal": total_skipped_nonlocal,
            "errors": errors,
            "timestamp": datetime.utcnow()
        }

    async def process_and_save_article(self, article_data: Dict, source_name: str) -> str:
        """
        Tek bir makaleyi işleyip veritabanına kaydeder.
        Döndürür: saved | duplicate | skipped_unclassified | skipped_geocoding
        """
        try:
            # İçeriği temizle (HTML etiketlerini çıkar)
            cleaned_content = nlp_service.clean_content(article_data['content'])

            # Haber türünü sınıflandır
            news_type, keywords = nlp_service.classify_news(
                article_data['title'],
                cleaned_content
            )

            if news_type not in REQUIRED_NEWS_TYPES:
                logger.info(f"[SKIP] Unclassified or unsupported category: {article_data['title'][:50]}...")
                return "skipped_unclassified"

            # Extract location
            full_text = f"{article_data['title']} {cleaned_content}"
            full_text_lower = full_text.lower()
            location_text = nlp_service.extract_location(
                full_text
            )

            is_kocaelispor_news = bool(re.search(r"kocaeli\s*spor", full_text_lower))
            used_stadium_fallback = False
            used_izmit_fallback = False

            # Spor haberleri için konum politikası:
            # - Spor haberi ise doğrudan stadyum merkezi
            # - Spor dışı haberde konum yoksa/generik "Kocaeli" ise İzmit merkez fallback
            if news_type == "Spor":
                location_text = KOCAELISPOR_STADIUM["name"]
                used_stadium_fallback = True
            else:
                generic_city_location = isinstance(location_text, str) and location_text.strip().lower() == "kocaeli"
                if location_text is None or generic_city_location:
                    location_text = IZMIT_FALLBACK_CENTER["name"]
                    used_izmit_fallback = True

            # Kocaeli ile ilgisi olmayan ulusal haberleri filtrele:
            # konum bulunamadıysa ve metinde hiçbir ilçe adı / "Kocaeli" geçmiyorsa atla
            if location_text is None:
                from src.config import KOCAELI_DISTRICTS
                import re as _re
                has_kocaeli = bool(_re.search(r'(?<![a-zA-ZçğışöüÇĞİÖŞÜ])kocaeli', full_text, _re.IGNORECASE))
                has_district = any(
                    bool(_re.search(rf'(?<![a-zA-ZçğışöüÇĞİÖŞÜ]){_re.escape(d)}', full_text, _re.IGNORECASE))
                    for d in KOCAELI_DISTRICTS
                )
                if not has_kocaeli and not has_district:
                    logger.info(f"[SKIP] No Kocaeli location reference: {article_data['title'][:50]}...")
                    return "skipped_nonlocal"

            # Geocode location if found
            coordinates = None
            district = None

            if location_text:
                coordinates = geocoding_service.geocode_location(location_text)

                # Proje kuralı: Geocoding başarısız olursa kayıt işlenmez
                if coordinates is None:
                    if news_type == "Spor" and used_stadium_fallback:
                        coordinates = {
                            "lat": KOCAELISPOR_STADIUM["lat"],
                            "lng": KOCAELISPOR_STADIUM["lng"],
                        }
                        district = KOCAELISPOR_STADIUM["district"]
                    elif news_type != "Spor":
                        # Spor dışı haberde koordinat üretilemediyse dağınık nokta yerine
                        # her zaman İzmit merkez fallback kullan.
                        coordinates = {
                            "lat": IZMIT_FALLBACK_CENTER["lat"],
                            "lng": IZMIT_FALLBACK_CENTER["lng"],
                        }
                        district = IZMIT_FALLBACK_CENTER["district"]
                        location_text = IZMIT_FALLBACK_CENTER["name"]
                        used_izmit_fallback = True
                    else:
                        logger.info(f"[SKIP] Geocoding failed: {article_data['title'][:50]}...")
                        return "skipped_geocoding"

                if coordinates is None:
                    logger.info(f"[SKIP] Geocoding failed: {article_data['title'][:50]}...")
                    return "skipped_geocoding"

                # Check if location is a district
                from src.config import KOCAELI_DISTRICTS
                import re as _re
                for dist in KOCAELI_DISTRICTS:
                    if dist.lower() in location_text.lower():
                        district = dist
                        break

                # If location is a street/mahalle, also search full text for district
                if not district:
                    full_text = f"{article_data['title']} {cleaned_content}"
                    for dist in KOCAELI_DISTRICTS:
                        pattern = rf'(?<![a-zA-ZçğışöüÇĞİÖŞÜ]){_re.escape(dist)}'
                        if _re.search(pattern, full_text, _re.IGNORECASE):
                            district = dist
                            break

                if not district and used_izmit_fallback:
                    district = IZMIT_FALLBACK_CENTER["district"]

            # Generate hash for duplicate detection
            similarity_hash = similarity_service.generate_hash(
                article_data['title'],
                cleaned_content
            )

            # Check for duplicates by hash
            database = db.get_db()
            existing = await database.news.find_one({"similarity_hash": similarity_hash})

            if existing:
                await self._merge_source_if_needed(existing, source_name, article_data['url'])

                return "duplicate"

            # Generate embedding for similarity check
            embedding = similarity_service.get_embedding(
                f"{article_data['title']} {cleaned_content}"
            )

            # Embedding tabanlı duplicate kontrolü (>= %90)
            if embedding is not None:
                duplicate_candidate = await self._find_embedding_duplicate(
                    news_type=news_type,
                    publish_date=article_data['publish_date'],
                    new_embedding=embedding
                )

                if duplicate_candidate is not None:
                    await self._merge_source_if_needed(duplicate_candidate, source_name, article_data['url'])
                    return "duplicate"

            # Create news article document
            location_obj = None
            if location_text or coordinates:
                location_obj = Location(
                    text=location_text,
                    coordinates=coordinates,
                    district=district
                )

            news_article = NewsArticle(
                news_type=news_type,
                title=article_data['title'],
                content=article_data['content'],
                cleaned_content=cleaned_content,
                location=location_obj,
                publish_date=article_data['publish_date'],
                sources=[NewsSource(name=source_name, url=article_data['url'])],
                keywords=keywords,
                similarity_hash=similarity_hash,
                embedding=embedding.tolist() if embedding is not None else None
            )

            # Convert to dict for MongoDB
            article_dict = news_article.model_dump(by_alias=True, exclude={'id'})

            # Insert into database
            result = await database.news.insert_one(article_dict)

            logger.info(f"[SUCCESS] Saved article: {article_data['title'][:50]}...")

            return "saved"

        except Exception as e:
            logger.error(f"[ERROR] Failed to process article: {e}")
            raise

    async def _merge_source_if_needed(self, existing_article: Dict, source_name: str, source_url: str) -> None:
        """Append source info to an existing merged article if URL is new."""
        database = db.get_db()
        existing_sources = existing_article.get('sources', [])
        source_urls = [s.get('url') for s in existing_sources]

        if source_url in source_urls:
            return

        existing_sources.append({
            "name": source_name,
            "url": source_url
        })

        await database.news.update_one(
            {"_id": existing_article['_id']},
            {
                "$set": {
                    "sources": existing_sources,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        logger.info("[UPDATE] Added new source to existing article")

    async def _find_embedding_duplicate(self, news_type: str, publish_date: datetime, new_embedding: np.ndarray):
        """
        Find duplicate using embedding similarity with a narrowed candidate window.
        """
        database = db.get_db()

        window_start = publish_date - timedelta(days=self.embedding_days_window)
        window_end = publish_date + timedelta(days=self.embedding_days_window)

        query = {
            "news_type": news_type,
            "embedding": {"$ne": None},
            "publish_date": {
                "$gte": window_start,
                "$lte": window_end
            }
        }

        candidates = await database.news.find(query).sort("publish_date", -1).limit(self.embedding_candidate_limit).to_list(length=self.embedding_candidate_limit)

        best_candidate = None
        best_score = 0.0

        for candidate in candidates:
            candidate_embedding = candidate.get("embedding")
            if not candidate_embedding:
                continue

            similarity = similarity_service.calculate_embedding_similarity(
                new_embedding,
                np.array(candidate_embedding)
            )

            if similarity >= similarity_service.threshold and similarity > best_score:
                best_score = similarity
                best_candidate = candidate

        if best_candidate is not None:
            logger.info(
                f"[DUPLICATE] Merged by embedding similarity: {best_score:.2%}"
            )

        return best_candidate


# Global scraping service instance
scraping_service = ScrapingService()
