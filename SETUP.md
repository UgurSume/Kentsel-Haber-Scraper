# Projeyi Kurma ve Çalıştırma Rehberi

Kocaeli yerel haber izleme sistemini kendi bilgisayarında çalıştırmak için aşağıdaki adımları sırayla uygula.

---

## Gereksinimler

Aşağıdaki araçlar bilgisayarında kurulu olmalı:

| Araç | Sürüm | İndirme |
|------|-------|---------|
| Python | 3.10 veya üzeri | https://www.python.org/downloads/ |
| Node.js | 18 veya üzeri | https://nodejs.org/ |
| MongoDB Community | 6 veya üzeri | https://www.mongodb.com/try/download/community |
| Google Chrome | Güncel | https://www.google.com/chrome/ |
| Git | Herhangi | https://git-scm.com/ |

> **Not:** Chrome, backend'deki Selenium ile sayfa kazıma için gerekli.

---

## 1. Projeyi Klonla

```bash
git clone <repo-url>
cd kentsel-haber-scraper
```

---

## 2. MongoDB Kurulumu ve Başlatma

### Windows
MongoDB kurulduktan sonra servis genellikle otomatik başlar.  
Başlamıyorsa:

```powershell
# Servisi başlat
net start MongoDB
```

Veya MongoDB Compass uygulamasını aç — bağlanırken servis otomatik başlar.

Bağlantı adresi: `mongodb://localhost:27017`  
Herhangi bir veritabanı veya koleksiyon oluşturmana **gerek yok**, backend ilk çalışmada otomatik oluşturur.

---

## 3. Backend Kurulumu

```bash
# Proje kökünde sanal ortam oluştur
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

```bash
# Bağımlılıkları yükle
pip install -r backend/requirements.txt
```

```bash
# spaCy Türkçe dil modelini indir (~500 MB)
python -m spacy download tr_core_news_lg
```

### .env Dosyası Oluştur

```bash
cp backend/.env.example backend/.env
```

`backend/.env` dosyasını aç ve şu satırları düzenle:

```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=kentsel_haber_db

# Google Maps API anahtarın (aşağıya bak)
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

SCRAPING_SCHEDULE_HOURS=24
SIMILARITY_THRESHOLD=0.90
HOST=0.0.0.0
PORT=8000
DEBUG=True
ALLOWED_ORIGINS=http://localhost:3000
```

### Backend'i Başlat

```bash
cd backend
python main.py
```

API hazır olduğunda terminalde şunu görürsün:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Swagger arayüzü: http://localhost:8000/docs

---

## 4. Frontend Kurulumu

Yeni bir terminal aç (backend çalışmaya devam etsin):

```bash
cd frontend
npm install
```

### .env Dosyası Oluştur

```bash
cp .env.example .env
```

`frontend/.env` dosyasını aç:

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
```

### Frontend'i Başlat

```bash
npm start
```

Uygulama http://localhost:3000 adresinde açılır.

---

## 5. Google Maps API Anahtarı

Haritanın çalışması için bir API anahtarı gerekir.

1. https://console.cloud.google.com/ adresine git
2. Yeni proje oluştur (veya mevcut bir projeyi seç)
3. **APIs & Services → Enable APIs** kısmından şunları etkinleştir:
   - Maps JavaScript API
   - Geocoding API
4. **APIs & Services → Credentials → Create Credentials → API Key** ile anahtar oluştur
5. Oluşan anahtarı hem `backend/.env` hem de `frontend/.env` dosyalarına yapıştır

> Aylık 200$ ücretsiz kredi var, geliştirme aşamasında ücret çıkmaz.  
> Geocoding için Google kullanmak istemiyorsan anahtarı boş bırakabilirsin — sistem Nominatim (OpenStreetMap) ile otomatik devam eder.

---

## 6. İlk Veriyi Çek

Uygulama açıkken sol paneldeki **"Haberleri Güncelle"** butonuna tıkla veya:

```bash
curl -X POST http://localhost:8000/api/scrape/?days=3
```

Scraping tamamlandıktan sonra haberler haritada görünür.

---

## Özet: Çalışma Sırası

Her seferinde şu sırayla başlat:

1. MongoDB servisinin çalıştığından emin ol
2. Terminal 1 → sanal ortamı aktif et → `cd backend && python main.py`
3. Terminal 2 → `cd frontend && npm start`
4. Tarayıcıda http://localhost:3000 aç

---

## Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| `ModuleNotFoundError` | Sanal ortamın aktif olduğundan emin ol: `.venv\Scripts\activate` |
| `MongoDB connection refused` | MongoDB servisini başlat: `net start MongoDB` |
| Harita görünmüyor | `frontend/.env` dosyasındaki `REACT_APP_GOOGLE_MAPS_API_KEY` değerini kontrol et |
| `tr_core_news_lg` bulunamadı | `python -m spacy download tr_core_news_lg` komutunu tekrar çalıştır |
| Chrome sürücü hatası | Chrome'u güncelle, `undetected-chromedriver` versiyonu ile uyumlu olmasına dikkat et |
| CORS hatası | `backend/.env` içindeki `ALLOWED_ORIGINS` değerinin `http://localhost:3000` içerdiğinden emin ol |
