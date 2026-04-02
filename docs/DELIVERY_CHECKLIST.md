# Delivery Checklist

## Backend
- [x] Zorunlu haber kategorileri tek listede standardize edildi.
- [x] Sınıflandırma öncelik sırası tanımlandı.
- [x] Duplicate kontrol: hash + embedding (%90+) aktif.
- [x] Aynı haberde çoklu kaynak birleştirme aktif.
- [x] Geocoding başarısızsa kayıt atlanıyor.
- [x] Scraper altyapısı ortak ve dayanıklı hale getirildi.
- [x] Birim testler eklendi ve geçiyor.

## Frontend
- [x] Google Maps tabanlı harita arayüzü eklendi.
- [x] Haber türü / ilçe / tarih filtreleri dinamik çalışıyor.
- [x] Marker + InfoWindow + Habere Git butonu mevcut.
- [x] Scraping tetikleme butonu eklendi.
- [x] Frontend production build başarılı.

## Configuration
- [x] backend/.env.example mevcut.
- [x] frontend/.env.example eklendi.
- [ ] REACT_APP_GOOGLE_MAPS_API_KEY ve backend GOOGLE_MAPS_API_KEY gerçek değerlerle doldurulacak.

## Rapor ve Sunum
- [ ] docs/latex-rapor altında IEEE formatında LaTeX raporu oluşturulacak.
- [ ] Kullanılan anahtar kelime listeleri rapora eklenecek.
- [ ] Konum çıkarım ve duplicate yöntemleri raporda detaylandırılacak.
- [ ] Sunumda canlı demo senaryosu hazır edilecek.
