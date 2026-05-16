# 🗺️ Kentsel Haber Scraper

Web Scraping Tabanlı Kentsel Haber İzleme ve Harita Üzerinde Görselleştirme Sistemi

## 📋 Proje Hakkında

Kocaeli yerel haber sitelerinden belirlenen haber türlerine ait haberlerin web ortamından otomatik olarak toplanması, işlenmesi ve Google Maps üzerinde görselleştirilmesi.

### Haber Türleri
- 🚗 Trafik Kazası
- 🔥 Yangın
- ⚡ Elektrik Kesintisi
- 🚨 Hırsızlık
- 🎭 Kültürel Etkinlikler
- ⚽ Spor (Kocaelispor odaklı)

### Haber Kaynakları
- Çağdaş Kocaeli (cagdaskocaeli.com.tr)
- Özgür Kocaeli (ozgurkocaeli.com.tr)
- Ses Kocaeli (seskocaeli.com)
- Yeni Kocaeli (yenikocaeli.com)
- Bizim Yaka (bizimyaka.com)

## 🚀 Teknoloji Stack

### Backend
- **Framework**: FastAPI
- **Scraping**: BeautifulSoup4, Requests
- **NLP**: spaCy, sentence-transformers
- **Database**: MongoDB
- **Geocoding**: Google Maps API

### Frontend
- **Framework**: React + TypeScript
- **Harita**: Google Maps JavaScript API
- **HTTP Client**: Axios
- **UI**: TailwindCSS / Bootstrap

## 📦 Kurulum

### Backend Kurulumu

1. **Virtual environment oluştur ve aktif et:**
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

2. **Kütüphaneleri yükle:**
```bash
pip install -r requirements.txt
```

3. **spaCy Türkçe modeli yükle:**
```bash
python -m spacy download tr_core_news_lg
```

4. **Environment değişkenlerini ayarla:**
```bash
cp .env.example .env
# .env dosyasını düzenle:
# - MONGODB_URI: MongoDB bağlantı adresi
# - GOOGLE_MAPS_API_KEY: Google Maps API anahtarı
```

5. **Sunucuyu başlat:**
```bash
python main.py
```

Backend: http://localhost:8000

Alternatif (Windows, tek komut):
```powershell
./run.ps1
```

### Frontend Kurulumu

1. **Paketleri yükle:**
```bash
cd frontend
npm install
```

2. **Environment değişkenlerini ayarla:**
```bash
# .env.local dosyası oluştur
REACT_APP_API_URL=http://localhost:8000
REACT_APP_GOOGLE_MAPS_API_KEY=your_api_key_here
```

3. **Uygulamayı başlat:**
```bash
npm start
```

Frontend: http://localhost:3000

## 🗄️ MongoDB

### MongoDB Atlas (Cloud) - Önerilen
1. https://www.mongodb.com/cloud/atlas adresine git
2. Ücretsiz cluster oluştur
3. Connection string'i kopyala
4. `.env` dosyasına ekle

### MongoDB Local
```bash
# Windows - MongoDB'yi servise ekle ve başlat
# Linux/Mac
brew install mongodb-community
brew services start mongodb-community
```

## 🔑 Google Maps API Key Alma

1. https://console.cloud.google.com/ adresine git
2. Yeni proje oluştur
3. "APIs & Services" > "Credentials" > "Create Credentials" > "API Key"
4. Geocoding API ve Maps JavaScript API'yi etkinleştir
5. API key'i `.env` dosyalarına ekle

## 📚 API Endpoints

### Health Check
```
GET /health
```

### Haberleri Listele
```
GET /api/news?news_type=Trafik Kazası&district=Gebze&start_date=2024-01-01
```

### Stadyum Çevresi Spor Haberleri
```
GET /api/news?news_type=Spor&around_stadium=true&radius_km=3
```

### Scraping Tetikle
```
POST /api/scrape?days=3
```

Not: `days` parametresi opsiyoneldir. Varsayılan değer 3'tür, 1-30 aralığında farklı bir değer gönderilebilir.

### Haber Detayı
```
GET /api/news/{news_id}
```

### İstatistikler
```
GET /api/stats
```

## 🧪 Test

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

## 📖 Proje Yapısı

```
kentsel-haber-scraper/
├── backend/
│   ├── src/
│   │   ├── scrapers/        # Web scraper'lar
│   │   ├── models/          # Veri modelleri
│   │   ├── services/        # İş mantığı
│   │   ├── routes/          # API endpoint'leri
│   │   ├── utils/           # Yardımcı fonksiyonlar
│   │   └── config/          # Ayarlar
│   ├── tests/               # Testler
│   ├── main.py              # Ana uygulama
│   └── requirements.txt     # Python bağımlılıkları
├── frontend/
│   ├── src/
│   │   ├── components/      # React bileşenleri
│   │   ├── services/        # API servisleri
│   │   └── App.tsx          # Ana uygulama
│   └── package.json         # Node bağımlılıkları
└── docs/
    └── latex-rapor/         # LaTeX proje raporu
```

## 🎯 Özellikler

✅ 5 farklı haber kaynağından otomatik scraping
✅ Haber türü sınıflandırma (anahtar kelime tabanlı)
✅ Konum bilgisi çıkarımı (NER)
✅ Duplicate kontrol (metin benzerliği %90+)
✅ Google Maps üzerinde görselleştirme
✅ Haber türüne göre farklı marker'lar
✅ Filtreleme (tür, ilçe, tarih)
✅ Kocaelispor stadyumu çevresinde dairesel filtreleme
✅ MongoDB ile veri saklama
✅ REST API

## ⚙️ Stadyum Ayarları (.env)

Backend `.env` dosyasından stadyum merkezi yönetilebilir:

```env
STADIUM_NAME=Kocaeli Stadyumu
STADIUM_LAT=40.7820
STADIUM_LNG=30.0120
STADIUM_DISTRICT=İzmit
DEFAULT_STADIUM_RADIUS_KM=3.0
```

Bu değerler frontend filtre paneline `/api/news/meta` üzerinden otomatik taşınır.

## 👥 Geliştirici

[Adını buraya ekle]

## 📅 Teslim Tarihi

03.04.2026

## 📄 Lisans

Bu proje Kocaeli Üniversitesi Bilgisayar Programlama Lab Projesi kapsamında geliştirilmiştir.
