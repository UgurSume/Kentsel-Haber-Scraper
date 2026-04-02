# GOOGLE MAPS API KEY ALMA REHBERİ

## Adım 1: Google Cloud Console
1. https://console.cloud.google.com/ adresine git
2. Google hesabınla giriş yap

## Adım 2: Yeni Proje Oluştur
1. Üstteki "Select a project" dropdown'a tıkla
2. "New Project" butonuna tıkla
3. Proje adı: "Kentsel Haber Scraper"
4. "Create" butonuna tıkla
5. Proje oluşturulurken 1-2 dakika bekle

## Adım 3: API'leri Etkinleştir
1. Sol menüden "APIs & Services" > "Library"
2. Ara: "Geocoding API"
   - Tıkla ve "Enable" butonuna bas
3. Tekrar ara: "Maps JavaScript API"
   - Tıkla ve "Enable" butonuna bas

## Adım 4: API Key Oluştur
1. Sol menüden "APIs & Services" > "Credentials"
2. Üstte "Create Credentials" butonuna tıkla
3. "API Key" seç
4. API Key oluşturuldu! Kopyala ve kaydet

## Adım 5: API Key'i Güvenli Hale Getir (Opsiyonel ama Önerilen)
1. Oluşturulan key'in yanındaki kalem ikonuna tıkla
2. "Application restrictions" bölümünde:
   - Geliştirme için: "None" seçili kalabilir
   - Canlıya çıkarken: "HTTP referrers" veya "IP addresses" ekle
3. "API restrictions" bölümünde:
   - "Restrict key" seç
   - "Geocoding API" ve "Maps JavaScript API" seç
4. "Save" butonuna tıkla

## Adım 6: Billing Ekle (ZORUNLU - Ama Ücretsiz!)
Google Maps API kullanmak için billing hesabı gerekli ama:
- ✅ İlk $200 her ay ücretsiz
- ✅ Bu proje için yeterli (aylık ~1000 istek)
- ✅ Kredi kartı gerekli ama otomatik ücret yok

1. Sol menüden "Billing" > "Link a billing account"
2. Yeni billing account oluştur
3. Kredi kartı bilgilerini gir (ücretsiz kredi için)
4. "Enable billing" tıkla

## ⚠️ ÖNEMLİ NOTLAR:
- API key'i kimseyle paylaşma
- GitHub'a pushlama (zaten .gitignore'da var)
- Günlük quota limitlerini aşma

## 💰 Maliyet Tahmini (Bu Proje İçin):
- Geocoding API: $5 / 1000 istek
- Bu projede: ~50-100 istek (tek seferlik)
- Toplam maliyet: $0 (Ücretsiz quota içinde)

---

API Key'inizi aldıktan sonra:
```bash
# Backend klasöründe .env dosyasını düzenle
GOOGLE_MAPS_API_KEY=AIza...buraya_yapistir
```
