"""
NLP Service for text classification and location extraction
"""
import re
from typing import List, Dict, Optional, Tuple
import logging
from src.config import NEWS_TYPES, KOCAELI_DISTRICTS, NEWS_TYPE_PRIORITY
from src.services.similarity_service import similarity_service

logger = logging.getLogger(__name__)


class NLPService:
    """NLP service for text processing"""

    @staticmethod
    def _normalize_tr(text: str) -> str:
        """Türkçe karakterleri normalize ederek karşılaştırmayı dayanıklı hale getirir."""
        if not text:
            return ""
        table = str.maketrans({
            "ç": "c", "Ç": "c",
            "ğ": "g", "Ğ": "g",
            "ı": "i", "İ": "i",
            "ö": "o", "Ö": "o",
            "ş": "s", "Ş": "s",
            "ü": "u", "Ü": "u",
        })
        return text.translate(table).lower()

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

    @staticmethod
    def _count_keyword_occurrences(text: str, keyword: str) -> int:
        """Keyword sayımını kelime sınırına göre yapar, substring false-positive azaltır."""
        if not text or not keyword:
            return 0

        escaped = re.escape(keyword.strip())
        escaped = escaped.replace(r"\ ", r"\s+")
        pattern = rf"(?<!\w){escaped}(?!\w)"
        return len(re.findall(pattern, text, flags=re.IGNORECASE))

    def _semantic_sport_signal(self, title: str, content: str) -> bool:
        """Keyword dışına çıkan spor haberleri için semantik güvenlik ağı."""
        if not similarity_service.model:
            return False

        text = f"{title} {content}"[:1000]
        norm_text = self._normalize_tr(text)
        has_local_context = (
            "kocaeli" in norm_text
            or any(self._normalize_tr(district) in norm_text for district in self.districts)
        )

        if not has_local_context:
            return False

        sport_prototypes = [
            "Kocaeli'de spor haberi, maç sonucu, teknik direktör açıklaması",
            "futbol kulübü, antrenör, hakem, UEFA organizasyonu, spor müsabakası",
            "kocaelispor, taraftar, transfer, lig karşılaşması"
        ]
        non_sport_prototypes = [
            "ekonomi ve zam haberi, akaryakıt fiyatı",
            "asayiş olayı, operasyon ve suç haberi",
            "siyaset ve kurum ziyareti haberi"
        ]

        text_emb = similarity_service.get_embedding(text)
        if text_emb is None:
            return False

        sport_scores = []
        for prototype in sport_prototypes:
            proto_emb = similarity_service.get_embedding(prototype)
            if proto_emb is not None:
                sport_scores.append(similarity_service.calculate_embedding_similarity(text_emb, proto_emb))

        non_sport_scores = []
        for prototype in non_sport_prototypes:
            proto_emb = similarity_service.get_embedding(prototype)
            if proto_emb is not None:
                non_sport_scores.append(similarity_service.calculate_embedding_similarity(text_emb, proto_emb))

        if not sport_scores:
            return False

        best_sport = max(sport_scores)
        best_non_sport = max(non_sport_scores) if non_sport_scores else 0.0

        return best_sport >= 0.47 and (best_sport - best_non_sport) >= 0.08

    def classify_news(self, title: str, content: str) -> Tuple[str, List[str]]:
        """
        Classify news based on keywords
        Returns: (news_type, matched_keywords)
        """
        raw_title = (title or "").lower()
        content_head = (content or "")[:700]
        raw_text = f"{title} {content_head}".lower()
        normalized_title = self._normalize_tr(title or "")
        normalized_text = self._normalize_tr(f"{title} {content_head}")

        scores = {}
        matched_keywords = {}

        for news_type, keywords in self.news_types.items():
            score = 0
            matches = []

            for keyword in keywords:
                keyword_lower = keyword.lower()
                keyword_normalized = self._normalize_tr(keyword)
                # Count occurrences
                title_count = max(
                    self._count_keyword_occurrences(raw_title, keyword_lower),
                    self._count_keyword_occurrences(normalized_title, keyword_normalized)
                )
                body_count = max(
                    self._count_keyword_occurrences(raw_text, keyword_lower),
                    self._count_keyword_occurrences(normalized_text, keyword_normalized)
                )

                if news_type == "Spor":
                    # Spor sınıfında başlık daha yüksek ağırlık alır.
                    count = (title_count * 4) + body_count
                else:
                    count = (title_count * 3) + body_count

                # Ağır kategorilerde yalnız içerikten gelen tekil sinyali zayıflat.
                if news_type in {"Yangın", "Hırsızlık", "Silahlı Saldırı"} and title_count == 0 and body_count < 2:
                    count = 0

                if count > 0:
                    score += count
                    matches.append(keyword)

            scores[news_type] = score
            matched_keywords[news_type] = matches

        # Spor sınıfını yanlış pozitiflerden koru:
        # 1) Güçlü sinyal: "kocaelispor" veya "kocaeli spor"
        # 2) Alternatif: en az 1 spor anahtar kelimesi + yerel bağlam (Kocaeli/ilçe/stadyum)
        spor_matches = matched_keywords.get("Spor", [])
        if spor_matches:
            spor_match_set = {m.lower() for m in spor_matches}
            strong_sport_signal = any(k in spor_match_set for k in {"kocaelispor", "kocaeli spor"})
            weak_only_tokens = {"spor"}
            specific_sport_matches = [
                m for m in spor_matches if self._normalize_tr(m) not in weak_only_tokens
            ]
            has_specific_sport_in_title = any(
                self._normalize_tr(keyword) in normalized_title or keyword.lower() in raw_title
                for keyword in specific_sport_matches
            )
            has_local_context = (
                "kocaeli" in normalized_text
                or "stadyum" in normalized_text
                or any(self._normalize_tr(district) in normalized_text for district in self.districts)
            )
            generic_portal_title = any(
                token in normalized_title
                for token in ["son dakika haberleri", "gundemi", "guncel haber", "haberleri"]
            )
            if not strong_sport_signal and not (has_specific_sport_in_title and has_local_context):
                scores["Spor"] = 0
                matched_keywords["Spor"] = []
            if generic_portal_title:
                scores["Spor"] = 0
                matched_keywords["Spor"] = []

        # Takım adı + maç bağlamı heuristiği (anahtar kelime kaçırsa bile spor haberini yakalar).
        has_team_token = bool(re.search(r"\b[a-z0-9çğıöşü]+spor\b", normalized_text))
        has_match_context = any(
            token in normalized_text
            for token in [
                "deplasman", "super lig", "süper lig", "lig", "hafta",
                "mac", "maç", "skor", "hakem", "uefa", "fifa",
                "teknik direktor", "antrenor", "taraftar", "transfer"
            ]
        )
        if scores.get("Spor", 0) == 0 and has_team_token and has_match_context:
            scores["Spor"] = 1
            matched_keywords["Spor"] = ["__team_match_context__"]

        # Spor kelimesi bariz geçmeyen ama semantik olarak spor olan haberleri yakala.
        if scores.get("Spor", 0) == 0 and self._semantic_sport_signal(title, content):
            scores["Spor"] = 1
            matched_keywords["Spor"] = ["__semantic_sport__"]

        # Fuhuş operasyonu gibi asayiş haberlerini "Silahlı Saldırı"ya düşürme.
        if scores.get("Silahlı Saldırı", 0) > 0:
            weapon_context = any(
                token in normalized_text
                for token in ["silah", "tabanca", "tufek", "pompal", "ates acti", "kursun", "vuruldu"]
            )
            vice_context = any(token in normalized_text for token in ["fuhus", "uyusturucu", "narkotik"])
            if vice_context and not weapon_context:
                scores["Silahlı Saldırı"] = 0
                matched_keywords["Silahlı Saldırı"] = []

        # Ekonomi/zam haberlerinin "Hırsızlık"a düşmesini engelle.
        if scores.get("Hırsızlık", 0) > 0:
            theft_title_context = any(
                token in normalized_title
                for token in ["hirsiz", "hirsizlik", "soygun", "gasp", "kapkac", "yankesici", "calindi"]
            )
            economic_context = any(
                token in normalized_text
                for token in ["zam", "fiyat", "akaryakit", "lpg", "enflasyon", "tarife"]
            )
            if economic_context and not theft_title_context:
                scores["Hırsızlık"] = 0
                matched_keywords["Hırsızlık"] = []

        # Yangın için ekonomi/zam bağlamındaki mecazi kullanımları ele.
        yangin_matches = matched_keywords.get("Yangın", [])
        if yangin_matches:
            normalized_yangin_matches = {self._normalize_tr(m) for m in yangin_matches}
            weak_fire_tokens = {
                "yandi", "yanarak", "alevler", "alevlere teslim", "kul oldu"
            }
            has_only_weak_fire_signal = normalized_yangin_matches.issubset(weak_fire_tokens)
            economic_context_tokens = [
                "zam", "fiyat", "fiyatlar", "akaryakit", "lpg", "benzin", "motorin",
                "indirim", "pahali", "enflasyon", "piyasa", "tarife"
            ]
            has_economic_context = any(token in normalized_text for token in economic_context_tokens)

            if has_only_weak_fire_signal and has_economic_context:
                scores["Yangın"] = 0
                matched_keywords["Yangın"] = []

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

        # Yöntem 3a: Türkçe karakter normalize ederek ilçe adlarını ara (ör. Izmit -> İzmit)
        normalized_text = self._normalize_tr(text)
        for district in self.districts:
            if self._normalize_tr(district) in normalized_text:
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
