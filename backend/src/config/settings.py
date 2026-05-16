"""
Configuration settings for the application
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List

# Always resolve .env relative to this file's directory (backend/src/config/ -> backend/)
_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings"""

    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "kentsel_haber_db"

    # Google Maps API
    GOOGLE_MAPS_API_KEY: str = ""

    # Scraping
    SCRAPING_SCHEDULE_HOURS: int = 24
    DEFAULT_SCRAPE_DAYS: int = 3
    SCRAPING_RUN_ON_STARTUP: bool = False
    SIMILARITY_THRESHOLD: float = 0.90

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Stadium (Kocaelispor)
    STADIUM_NAME: str = "Kocaeli Stadyumu"
    STADIUM_LAT: float = 40.7750844
    STADIUM_LNG: float = 30.017023
    STADIUM_DISTRICT: str = "İzmit"
    DEFAULT_STADIUM_RADIUS_KM: float = 1.0

    class Config:
        env_file = str(_ENV_FILE)
        case_sensitive = True

    @property
    def origins_list(self) -> List[str]:
        """Convert comma-separated origins to list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]


# Global settings instance
settings = Settings()


# Haber türleri ve anahtar kelimeleri
# Çok genel kelimeler çıkarıldı: "kaza", "araç", "ateş", "alev", "elektrik" (tek başına), "enerji" (tek başına)
NEWS_TYPES = {
    "Trafik Kazası": [
        "trafik kazası", "kazaya karıştı", "feci kaza", "ölümlü kaza",
        "trafik kazasında", "trafik kazasına", "zincirleme kaza",
        "kaza yaptı", "kaza geçirdi",
        "çarpışma", "çarpıştı", "araçlar çarpıştı",
        "araç devrildi", "kamyon devrildi", "motosiklet kazası",
        "sürücü hayatını kaybetti", "alkollü sürücü", "hız ihlali"
    ],
    "Yangın": [
        "yangın", "yandı", "alevler", "itfaiye", "küle döndü",
        "yanan bina", "yanan ev", "yanarak", "yanan araç",
        "tutuştu", "yangın çıktı", "yangın söndürme",
        "alevlere teslim", "yangında hayatını", "dumanlar", "kül oldu",
        "kundaklama"
    ],
    "Elektrik Kesintisi": [
        "elektrik kesintisi", "elektrik kesildi", "elektriksiz",
        "elektrik arızası", "elektrik verilmedi", "elektrik gitti",
        "enerji kesintisi", "karanlıkta kaldı",
        "trafo arızası", "şebeke arızası"
    ],
    "Hırsızlık": [
        "hırsız", "hırsızlık", "çalındı", "hırsızlık olayı",
        "gasp", "soygun", "kapkaç", "soygunu",
        "soydu", "dolandırıcılık", "yankesici", "hırsızlar"
    ],
    "Silahlı Saldırı": [
        "silahlı saldırı", "silahlı kavga", "kanlı saldırı",
        "silahlı", "ateş açtı", "tabanca",
        "kurşuna dizildi", "kurşun sıktı", "kurşunla vuruldu",
        "bıçaklı", "bıçaklandı", "öldürüldü", "katledildi",
        "cinayet", "pompalı", "infaz", "silahla vuruldu"
    ],
    "Kültürel Etkinlikler": [
        "konser", "festival", "tiyatro", "sergi", "müze",
        "etkinlik", "sanat", "fuar", "şenlik",
        "galeri", "seminer", "konferans", "kültür merkezi"
    ],
    "Spor": [
        "kocaelispor", "kocaeli spor", "stadyum", "stad",
        "maç", "karşılaşma", "müsabaka", "tribün", "taraftar",
        "gol", "transfer", "teknik direktör", "puan durumu",
        "skor", "hakem", "uefa", "fifa", "lig", "u21",
        "spor", "antrenör", "antrenor", "kulübü", "kulubu",
        "yüzme", "yuzme", "turnuva", "şampiyona", "sampiyona",
        "milli sporcu", "milli antrenör", "milli antrenor",
        "kickbox", "kick boks", "boks", "güreş", "gures",
        "basketbol", "voleybol", "futbol"
    ]
}

# Zorunlu haber türleri (proje isterlerine uygun tek kaynak)
REQUIRED_NEWS_TYPES = list(NEWS_TYPES.keys()) + ["Diğer"]

# Birden fazla kategori eşleştiğinde uygulanacak öncelik
NEWS_TYPE_PRIORITY = [
    "Yangın",
    "Silahlı Saldırı",
    "Trafik Kazası",
    "Elektrik Kesintisi",
    "Hırsızlık",
    "Kültürel Etkinlikler",
    "Spor"
]

# Kocaelispor stadyumu (Yıldız Entegre Kocaeli Stadyumu) çevresi için varsayılan merkez
KOCAELISPOR_STADIUM = {
    "name": settings.STADIUM_NAME,
    "lat": settings.STADIUM_LAT,
    "lng": settings.STADIUM_LNG,
    "district": settings.STADIUM_DISTRICT
}

DEFAULT_STADIUM_RADIUS_KM = settings.DEFAULT_STADIUM_RADIUS_KM
DEFAULT_SCRAPE_DAYS = settings.DEFAULT_SCRAPE_DAYS

# Spor dışı, konumu belirsiz yerel haberler için varsayılan fallback (İzmit merkez)
IZMIT_FALLBACK_CENTER = {
    "name": "İzmit Merkez",
    "lat": 40.7654,
    "lng": 29.9408,
    "district": "İzmit"
}

# Haber kaynakları
NEWS_SOURCES = [
    {
        "name": "Çağdaş Kocaeli",
        "url": "https://www.cagdaskocaeli.com.tr/",
        "base_url": "https://www.cagdaskocaeli.com.tr"
    },
    {
        "name": "Özgür Kocaeli",
        "url": "https://www.ozgurkocaeli.com.tr/",
        "base_url": "https://www.ozgurkocaeli.com.tr"
    },
    {
        "name": "Ses Kocaeli",
        "url": "https://www.seskocaeli.com/",
        "base_url": "https://www.seskocaeli.com"
    },
    {
        "name": "Yeni Kocaeli",
        "url": "https://yenikocaeli.com",
        "base_url": "https://yenikocaeli.com"
    },
    {
        "name": "Bizim Yaka",
        "url": "https://bizimyaka.com",
        "base_url": "https://bizimyaka.com"
    }
]

# Kocaeli ilçeleri
KOCAELI_DISTRICTS = [
    "Başiskele", "Çayırova", "Darıca", "Derince", "Dilovası",
    "Gebze", "Gölcük", "İzmit", "Kandıra", "Karamürsel",
    "Kartepe", "Körfez"
]
