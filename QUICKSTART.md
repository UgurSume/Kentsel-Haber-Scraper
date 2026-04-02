# 🚀 Hızlı Başlangıç Kılavuzu

## Adım 1: MongoDB Kurulumu

### Opsiyon A: MongoDB Atlas (Kolay - Önerilen)
1. https://www.mongodb.com/cloud/atlas adresine git
2. "Try Free" butonuna tıkla
3. Ücretsiz hesap oluştur
4. "Build a Database" > "M0 FREE" seç
5. Cloud Provider: AWS, Region: Frankfurt (en yakın)
6. "Create" butonuna tıkla
7. Security Quickstart:
   - Username ve password oluştur (kaydet!)
   - "Add My Current IP Address" tıkla
8. "Connect" butonuna tıkla
9. "Drivers" seç
10. Connection string'i kopyala (mongodb+srv://...)
11. `backend/.env` dosyasında MONGODB_URI olarak kullan

### Opsiyon B: MongoDB Lokal

**Windows:**
```bash
# MongoDB'yi indir ve kur: https://www.mongodb.com/try/download/community
# Kurulum sonrası MongoDB Compass da kurulacak (GUI arayüz)

# Servis başlat (PowerShell - Admin olarak)
net start MongoDB
```

**Mac:**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

**Linux:**
```bash
sudo apt-get install -y mongodb-org
sudo systemctl start mongod
```

## Adım 2: Google Maps API Key

1. https://console.cloud.google.com/ adresine git
2. Yeni proje oluştur: "Kentsel Haber Scraper"
3. Sol menüden "APIs & Services" > "Library"
4. Ara ve etkinleştir:
   - **Geocoding API**
   - **Maps JavaScript API**
5. Sol menüden "Credentials" > "Create Credentials" > "API Key"
6. API Key'i kopyala
7. `backend/.env` dosyasında GOOGLE_MAPS_API_KEY olarak kaydet

## Adım 3: Backend Kurulumu

```bash
# Proje dizinine git
cd kentsel-haber-scraper/backend

# Virtual environment oluştur
python -m venv venv

# Aktif et (Windows)
venv\Scripts\activate

# Aktif et (Mac/Linux)
source venv/bin/activate

# Kütüphaneleri yükle
pip install -r requirements.txt

# spaCy Türkçe modelini yükle
python -m spacy download tr_core_news_lg

# .env dosyasını düzenle
# MongoDB URI ve Google Maps API Key ekle

# MongoDB bağlantı testini çalıştır
cd tests
python test_mongodb.py

# Scraper testini çalıştır
python test_scraper.py

# Sunucuyu başlat
cd ..
python main.py
```

Backend şimdi http://localhost:8000 adresinde çalışıyor!

Test et: http://localhost:8000/health

## Adım 4: Frontend Kurulumu

```bash
# Yeni terminal/cmd aç
cd kentsel-haber-scraper/frontend

# Node modüllerini yükle
npm install

# .env.local dosyası oluştur
echo "REACT_APP_API_URL=http://localhost:8000" > .env.local
echo "REACT_APP_GOOGLE_MAPS_API_KEY=your_key_here" >> .env.local

# NOT: your_key_here yerine Google Maps API Key'inizi yazın

# Uygulamayı başlat
npm start
```

Frontend şimdi http://localhost:3000 adresinde çalışıyor!

## Adım 5: İlk Scraping

1. Backend terminalinde:
```bash
# Backend ana dizininde (venv aktif)
python -c "from src.scrapers import CagdasKocaeliScraper; s = CagdasKocaeliScraper(); print(len(s.scrape()))"
```

2. Veya Postman/cURL ile:
```bash
curl -X POST http://localhost:8000/api/scrape
```

3. Veya Frontend arayüzünden "Haberleri Güncelle" butonuna tıkla

## ✅ Kontrol Listesi

- [ ] MongoDB bağlantısı çalışıyor
- [ ] Google Maps API key alındı
- [ ] Backend başarıyla başladı (port 8000)
- [ ] Frontend başarıyla başladı (port 3000)
- [ ] İlk scraping işlemi çalıştı
- [ ] Harita üzerinde haberler görüntüleniyor

## 🐛 Yaygın Sorunlar

### MongoDB bağlantı hatası
```
pymongo.errors.ServerSelectionTimeoutError
```
**Çözüm**:
- MongoDB servisi çalışıyor mu kontrol et
- MongoDB Atlas kullanıyorsan IP whitelist'e ekle
- Connection string doğru mu kontrol et

### Google Maps API hatası
```
Unable to load map
```
**Çözüm**:
- API key doğru mu kontrol et
- Geocoding API ve Maps JavaScript API etkin mi kontrol et
- API key'e billing ekle (kredi kartı gerektirmez ama aktivasyon için gerekli)

### Port zaten kullanımda
```
Address already in use
```
**Çözüm**:
- Backend: `PORT=8001 python main.py`
- Frontend: PORT=3001 npm start

### spaCy model yüklenemedi
```
Can't find model 'tr_core_news_lg'
```
**Çözüm**:
```bash
python -m spacy download tr_core_news_lg
```

## 📞 Yardım

Sorun yaşıyorsan:
1. README.md dosyasını oku
2. .env dosyalarını kontrol et
3. Tüm servislerin çalıştığından emin ol
4. Log dosyalarına bak

## 🎉 Başarılı!

Backend ve Frontend çalışıyorsa artık:
- Haberler otomatik toplanıyor
- MongoDB'de saklanıyor
- Harita üzerinde görüntüleniyor

Şimdi diğer scraper'ları ekle ve projeyi geliştirebilirsin!
