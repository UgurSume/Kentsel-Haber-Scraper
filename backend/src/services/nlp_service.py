"""
NLP Service for text classification and location extraction
"""
import re
from typing import List, Dict, Optional, Tuple
import logging
from src.config import NEWS_TYPES, KOCAELI_DISTRICTS, NEWS_TYPE_PRIORITY

logger = logging.getLogger(__name__)


class NLPService:
    """NLP service for text processing"""

    def __init__(self):
        self.news_types = NEWS_TYPES
        self.districts = KOCAELI_DISTRICTS
        self.spacy_model = None
        self.load_spacy_model()

    def load_spacy_model(self):
        """Load spaCy Turkish model"""
        try:
            import spacy
            self.spacy_model = spacy.load("tr_core_news_lg")
            logger.info("[SUCCESS] spaCy Turkish model loaded")
        except Exception as e:
            logger.warning(f"[WARNING] Could not load spaCy model: {e}")
            logger.warning("Location extraction will use regex fallback")

    def classify_news(self, title: str, content: str) -> Tuple[str, List[str]]:
        """
        Classify news based on keywords
        Returns: (news_type, matched_keywords)
        """
        text = f"{title} {content}".lower()

        scores = {}
        matched_keywords = {}

        for news_type, keywords in self.news_types.items():
            score = 0
            matches = []

            for keyword in keywords:
                keyword_lower = keyword.lower()
                # Count occurrences
                count = text.count(keyword_lower)
                if count > 0:
                    score += count
                    matches.append(keyword)

            scores[news_type] = score
            matched_keywords[news_type] = matches

        # Find the type with highest score
        if not scores or max(scores.values()) == 0:
            return "Diğer", []

        max_score = max(scores.values())
        top_types = [news_type for news_type, score in scores.items() if score == max_score]

        # Deterministic tie-break based on predefined priority order
        for preferred_type in NEWS_TYPE_PRIORITY:
            if preferred_type in top_types:
                return preferred_type, matched_keywords[preferred_type]

        # Fallback (should not be reached with current configuration)
        best_type = top_types[0]
        return best_type, matched_keywords[best_type]

    def extract_location(self, text: str) -> Optional[str]:
        """
        Metinden konum bilgisi çıkarır.
        Öncelik sırası:
        1. Sokak / cadde / bulvar (en spesifik)
        2. Mahalle / köy / site
        3. İlçe adları
        4. spaCy ile adlı varlık tanıma (NER)
        5. İl düzeyi geri dönüş: Kocaeli
        """
        if not text:
            return None

        text = text.strip()

        _STOP = {'bir', 'bu', 'şu', 'o', 've', 'ile', 'da', 'de', 'ta', 'te', 'ki', 'mi'}

        def _clean(s: str):
            s = s.strip()
            return None if (len(s) < 3 or s.lower() in _STOP) else s

        # Yöntem 1: Sokak / cadde / bulvar (en spesifik adres)
        sokak_patterns = [
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:Sokağı|Sokak|Sk\.)',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:Caddesi|Cadde|Cd\.)',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:Bulvarı|Bulvar|Blv\.)',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:adresinde|mevkisinde|mevkiinde)',
        ]
        for pattern in sokak_patterns:
            match = re.search(pattern, text)
            if match and _clean(match.group(1)):
                return match.group(0).strip()

        # Yöntem 2: Mahalle / köy / site
        mahalle_patterns = [
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:Mahallesi|Mahalle|Mah\.|mahallesi|mahallesinde|mahallesinden|mahalleleri|mahallelerinde|mahallelerinden)',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:Köyü|Köy|köyünde|köyünden)',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:Sitesi|Site)',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:semtinde|bölgesinde)',
        ]
        for pattern in mahalle_patterns:
            match = re.search(pattern, text)
            if match and _clean(match.group(1)):
                return match.group(0).strip()

        # Yöntem 3: İlçe adlarını ara (Türkçe eklerle — "Gebzede", "İzmit'te")
        for district in self.districts:
            pattern = rf'(?<![a-zA-ZçğışöüÇĞİÖŞÜ]){re.escape(district)}'
            if re.search(pattern, text, re.IGNORECASE):
                return district

        # Yöntem 3b: Hal eki kalıpları ("Gebze'de", "Körfez'de")
        hal_patterns = [
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ]+)\'(?:de|da|te|ta|nde|nda|nin|nın|nun|nün)\b',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ]+)\s+ilçes',
        ]
        for pattern in hal_patterns:
            matches = re.findall(pattern, text)
            if matches:
                location = matches[0].strip()
                for district in self.districts:
                    if district.lower() in location.lower():
                        return district

        # Yöntem 4: spaCy varsa adlı varlık tanıma (NER) kullan
        if self.spacy_model:
            try:
                doc = self.spacy_model(text[:1000])
                for ent in doc.ents:
                    if ent.label_ in ['LOC', 'GPE']:
                        for district in self.districts:
                            if district.lower() in ent.text.lower():
                                return district
                        return ent.text
            except Exception as e:
                logger.error(f"İsimli varlık tanıma hatası: {e}")

        # Yöntem 5: İl düzeyi geri dönüş — metinde "Kocaeli" geçiyorsa
        if re.search(r'(?<![a-zA-ZçğışöüÇĞİÖŞÜ])Kocaeli', text, re.IGNORECASE):
            return "Kocaeli"

        return None

    def clean_content(self, html_content: str) -> str:
        """
        Clean and normalize content
        - Remove HTML tags
        - Remove extra whitespace
        - Remove special chars
        - Normalize text
        """
        if not html_content:
            return ""

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)

        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters (keep Turkish chars and punctuation)
        text = re.sub(r'[^\w\s.,!?:;()\-\'\"]+', '', text)

        # Remove common ad patterns
        ad_patterns = [
            r'reklam.*?goster',
            r'sitemize abone ol',
            r'haber bulteni',
            r'whatsapp.*?takip',
            r'facebook.*?begen',
            r'twitter.*?takip',
            r'instagram.*?takip',
            r'google news',
        ]

        for pattern in ad_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text.strip()


# Global NLP service instance
nlp_service = NLPService()
