import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Circle,
  GoogleMap,
  InfoWindow,
  useGoogleMap,
  useJsApiLoader,
} from '@react-google-maps/api';
import { MarkerClusterer, SuperClusterAlgorithm } from '@googlemaps/markerclusterer';
import './App.css';

type NewsSource = {
  name: string;
  url: string;
};

type Location = {
  text?: string | null;
  district?: string | null;
  coordinates?: {
    lat: number;
    lng: number;
  } | null;
};

type NewsArticle = {
  _id: string;
  news_type: string;
  title: string;
  publish_date: string;
  location?: Location | null;
  sources: NewsSource[];
};

type NewsMeta = {
  news_types: string[];
  districts: string[];
  sources: string[];
  stadium?: {
    name: string;
    lat: number;
    lng: number;
    default_radius_km: number;
  };
};

type Filters = {
  newsType: string;
  district: string;
  startDate: string;
  endDate: string;
};

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const MAPS_API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY || '';
const GOOGLE_MAP_ID = process.env.REACT_APP_GOOGLE_MAP_ID || '';
const DEFAULT_SCRAPE_DAYS = 3;

const KOCAELI_CENTER = { lat: 40.7654, lng: 29.9408 };

const FALLBACK_NEWS_TYPES = [
  'Trafik Kazası',
  'Yangın',
  'Elektrik Kesintisi',
  'Hırsızlık',
  'Silahlı Saldırı',
  'Kültürel Etkinlikler',
  'Spor',
];

const MARKER_STYLE: Record<string, { color: string; emoji: string }> = {
  'Diğer':               { color: '#0ea5e9', emoji: '✨' },
  'Trafik Kazası':       { color: '#ca3e47', emoji: '🚗' },
  'Yangın':              { color: '#f97316', emoji: '🔥' },
  'Elektrik Kesintisi':  { color: '#eab308', emoji: '⚡' },
  'Hırsızlık':           { color: '#4f46e5', emoji: '👤' },
  'Silahlı Saldırı':     { color: '#7e22ce', emoji: '⚠️' },
  'Kültürel Etkinlikler':{ color: '#0f766e', emoji: '🎵' },
  'Spor':                { color: '#16a34a', emoji: '⚽' },
};

const libraries: ('places' | 'marker')[] = ['marker'];

/**
 * Aynı koordinata düşen işaretçileri birbirinden ayırır.
 * _id'ye göre deterministik, küçük rastgele offset — her render'da sabit kalır,
 * daire deseni oluşturmaz.
 */
function jitterPositions(articles: NewsArticle[]): Map<string, { lat: number; lng: number }> {
  const groups = new Map<string, NewsArticle[]>();
  for (const a of articles) {
    const { lat, lng } = a.location!.coordinates!;
    // Aynı fiziksel noktadaki haberleri gruplamak için daha hassas anahtar kullan.
    const key = `${lat.toFixed(6)},${lng.toFixed(6)}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(a);
  }

  // _id string'inden deterministik sayı üretir (0–1 arası)
  function seededRand(id: string, salt: number): number {
    let h = salt;
    for (let i = 0; i < id.length; i++) {
      h = Math.imul(h ^ id.charCodeAt(i), 0x9e3779b9);
      h ^= h >>> 16;
    }
    return ((h >>> 0) / 0xffffffff);
  }

  const result = new Map<string, { lat: number; lng: number }>();
  for (const group of Array.from(groups.values())) {
    const { lat: bLat, lng: bLng } = group[0].location!.coordinates!;
    if (group.length === 1) {
      result.set(group[0]._id, { lat: bLat, lng: bLng });
    } else {
      // Grubun büyüklüğüne göre yayılımı artır: stadyumda yığılmayı belirgin azaltır.
      const r = Math.min(0.0005 + group.length * 0.00006, 0.0022);
      group.forEach((a: NewsArticle) => {
        const angle = seededRand(a._id, 1) * 2 * Math.PI;
        const dist  = r * (0.35 + seededRand(a._id, 2) * 0.65); // yarıçap içinde rastgele mesafe
        result.set(a._id, {
          lat: bLat + dist * Math.cos(angle),
          lng: bLng + dist * Math.sin(angle),
        });
      });
    }
  }
  return result;
}

// ── Harita işaretçileri + kümeleme bileşeni (<GoogleMap> içinde kullanılmalı) ──────
function MapMarkers({
  articles,
  onSelect,
}: {
  articles: NewsArticle[];
  onSelect: (a: NewsArticle) => void;
}) {
  const map = useGoogleMap();
  // Callback değiştiğinde effect'in yeniden çalışmasını önlemek için ref kullanıyoruz
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;
  const clustererRef = useRef<InstanceType<typeof MarkerClusterer> | null>(null);

  useEffect(() => {
    if (!map) return;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const gmaps = (window as any).google.maps;
    const useAdvancedMarkers = Boolean(GOOGLE_MAP_ID) && Boolean(gmaps.marker?.AdvancedMarkerElement);

    // Aynı koordinattaki işaretçileri daire üzerine yay
    const positions = jitterPositions(articles);

    const markers = articles.map((article) => {
      const style = MARKER_STYLE[article.news_type] ?? { color: '#0f172a', emoji: '?' };

      // Emoji bazlı özel marker elementi
      const el = document.createElement('div');
      el.style.cssText = [
        `background:${style.color}`,
        'border:2px solid rgba(255,255,255,0.9)',
        'border-radius:50%',
        'width:36px',
        'height:36px',
        'display:flex',
        'align-items:center',
        'justify-content:center',
        'font-size:18px',
        'cursor:pointer',
        'box-shadow:0 2px 6px rgba(0,0,0,0.4)',
        'transition:transform 0.15s',
      ].join(';');
      el.textContent = style.emoji;
      el.title = article.title;

      // Geçerli Map ID varsa AdvancedMarker, yoksa klasik Marker kullan.
      if (useAdvancedMarkers) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const marker: any = new gmaps.marker.AdvancedMarkerElement({
          position: positions.get(article._id) ?? article.location!.coordinates!,
          content: el,
          title: article.title,
        });
        marker.addListener('gmp-click', () => onSelectRef.current(article));
        return marker;
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const marker: any = new gmaps.Marker({
        position: positions.get(article._id) ?? article.location!.coordinates!,
        title: article.title,
        icon: {
          path: gmaps.SymbolPath.CIRCLE,
          scale: 12,
          fillColor: style.color,
          fillOpacity: 1,
          strokeColor: '#ffffff',
          strokeWeight: 2,
        },
        label: {
          text: style.emoji,
          color: '#ffffff',
          fontSize: '14px',
          fontWeight: '700',
        },
      });
      marker.addListener('click', () => onSelectRef.current(article));
      return marker;
    });

    // maxZoom: zoom >= 15'te cluster her zaman dağılır
    clustererRef.current = new MarkerClusterer({
      map,
      markers,
      algorithm: new SuperClusterAlgorithm({ maxZoom: 12, radius: 55 }),
    });

    // Bileşen kaldırıldığında işaretçileri ve kümeleryöneticiyi temizle
    return () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      markers.forEach((m: any) => {
        if (typeof m.setMap === 'function') {
          m.setMap(null);
        } else {
          m.map = null;
        }
      });
      clustererRef.current?.clearMarkers();
      clustererRef.current = null;
    };
  }, [map, articles]);

  return null;
}
// ────────────────────────────────────────────────────────────────────────────

// Ana uygulama bileşeni — sol panel + Google Haritalar
function App() {
  const [meta, setMeta] = useState<NewsMeta>({
    news_types: FALLBACK_NEWS_TYPES,
    districts: [],
    sources: [],
    stadium: {
      name: 'Kocaeli Stadyumu',
      lat: 40.782,
      lng: 30.012,
      default_radius_km: 1,
    },
  });
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<NewsArticle | null>(null);
  const [filters, setFilters] = useState<Filters>({
    newsType: '',
    district: '',
    startDate: '',
    endDate: '',
  });
  const [statusText, setStatusText] = useState<string>('Yükleniyor...');
  const [loading, setLoading] = useState<boolean>(false);
  const [scrapeLoading, setScrapeLoading] = useState<boolean>(false);
  const [scrapeDays, setScrapeDays] = useState<number>(DEFAULT_SCRAPE_DAYS);

  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: MAPS_API_KEY,
    libraries,
  });

  const markerNews = useMemo(
    () => news.filter((item) => item.location?.coordinates?.lat && item.location?.coordinates?.lng),
    [news]
  );

  const fetchMeta = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/news/meta`);
      if (!response.ok) {
        throw new Error('meta endpoint unavailable');
      }

      const data: NewsMeta = await response.json();
      setMeta({
        news_types: data.news_types?.length ? data.news_types : FALLBACK_NEWS_TYPES,
        districts: data.districts || [],
        sources: data.sources || [],
        stadium: data.stadium || {
          name: 'Kocaeli Stadyumu',
          lat: 40.782,
          lng: 30.012,
          default_radius_km: 1,
        },
      });
    } catch (_error) {
      setMeta((prev) => ({ ...prev, news_types: FALLBACK_NEWS_TYPES }));
    }
  }, []);

  const fetchNews = useCallback(async () => {
    setLoading(true);
    setStatusText('Haberler getiriliyor...');

    try {
      const params = new URLSearchParams();
      if (filters.newsType) params.set('news_type', filters.newsType);
      if (filters.district) params.set('district', filters.district);
      if (filters.startDate) params.set('start_date', filters.startDate);
      if (filters.endDate) params.set('end_date', filters.endDate);
      if (filters.newsType === 'Spor') {
        params.set('around_stadium', 'true');
        params.set('radius_km', '1');
      }
      params.set('limit', '300');

      const response = await fetch(`${API_URL}/api/news/?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Haberler alınamadı');
      }

      const data: NewsArticle[] = await response.json();
      setNews(data);
      setSelectedArticle(null);
      setStatusText(`${data.length} haber listelendi, ${data.filter((a) => a.location?.coordinates).length} tanesi haritada.`);
    } catch (_error) {
      setStatusText('Haberler çekilirken hata oluştu. Backend çalışıyor mu kontrol et.');
      setNews([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const triggerScrape = useCallback(async () => {
    setScrapeLoading(true);
    setStatusText('Scraping başlatıldı, bekleniyor...');
    const sanitizedDays = Math.min(30, Math.max(1, Math.floor(scrapeDays || DEFAULT_SCRAPE_DAYS)));

    try {
      const response = await fetch(`${API_URL}/api/scrape/?days=${sanitizedDays}`, { method: 'POST' });
      if (!response.ok) {
        throw new Error('Scraping tetiklenemedi');
      }

      const result = await response.json();
      setStatusText(
        `${sanitizedDays} gün için scraping tamamlandı. Kaydedilen: ${result.total_saved ?? 0}, Duplicate: ${result.total_duplicates ?? 0}, Atlanan geocoding: ${result.total_skipped_geocoding ?? 0}`
      );
      await fetchNews();
    } catch (_error) {
      setStatusText('Scraping tetiklenirken hata oluştu.');
    } finally {
      setScrapeLoading(false);
    }
  }, [fetchNews, scrapeDays]);

  React.useEffect(() => {
    void fetchMeta();
  }, [fetchMeta]);

  React.useEffect(() => {
    void fetchNews();
  }, [fetchNews]);

  const onFilterChange = (name: keyof Filters, value: string) => {
    setFilters((prev) => ({ ...prev, [name]: value } as Filters));
  };

  const clearFilters = () => {
    setFilters({
      newsType: '',
      district: '',
      startDate: '',
      endDate: '',
    });
  };

  const stadiumCenter = useMemo(
    () => ({ lat: meta.stadium?.lat ?? 40.782, lng: meta.stadium?.lng ?? 30.012 }),
    [meta.stadium?.lat, meta.stadium?.lng]
  );

  const mapCenter = selectedArticle?.location?.coordinates || (filters.newsType === 'Spor' ? stadiumCenter : KOCAELI_CENTER);

  return (
    <div className="app-shell">
      <aside className="control-panel">
        <h1>Kentsel Haber İzleme</h1>
        <p className="subtitle">Kocaeli yerel olay haritası</p>

        <div className="filters-grid">
          <label>
            Haber Türü
            <select
              value={filters.newsType}
              onChange={(event) => onFilterChange('newsType', event.target.value)}
            >
              <option value="">Tümü</option>
              {meta.news_types.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </label>

          <label>
            İlçe
            <select
              value={filters.district}
              onChange={(event) => onFilterChange('district', event.target.value)}
            >
              <option value="">Tümü</option>
              {meta.districts.map((district) => (
                <option key={district} value={district}>
                  {district}
                </option>
              ))}
            </select>
          </label>

          <label>
            Başlangıç Tarihi
            <input
              type="date"
              value={filters.startDate}
              onChange={(event) => onFilterChange('startDate', event.target.value)}
            />
          </label>

          <label>
            Bitiş Tarihi
            <input
              type="date"
              value={filters.endDate}
              onChange={(event) => onFilterChange('endDate', event.target.value)}
            />
          </label>

          <label>
            Scrape Gün Aralığı
            <input
              type="number"
              min={1}
              max={30}
              step={1}
              value={scrapeDays}
              onChange={(event) => setScrapeDays(Number(event.target.value) || DEFAULT_SCRAPE_DAYS)}
            />
          </label>

        </div>

        <div className="button-row">
          <button type="button" onClick={() => void fetchNews()} disabled={loading}>
            {loading ? 'Yükleniyor...' : 'Filtreyi Uygula'}
          </button>
          <button type="button" className="ghost" onClick={clearFilters}>
            Temizle
          </button>
          <button type="button" className="accent" onClick={() => void triggerScrape()} disabled={scrapeLoading}>
            {scrapeLoading ? 'Scraping...' : 'Haberleri Güncelle'}
          </button>
        </div>

        <p className="status">{statusText}</p>

        <section className="legend">
          {meta.news_types.map((type) => {
            const style = MARKER_STYLE[type] || { color: '#0f172a', emoji: '•' };
            return (
              <div key={type} className="legend-item">
                <span
                  className="legend-emoji"
                  style={{ backgroundColor: style.color }}
                >
                  {style.emoji}
                </span>
                {type}
              </div>
            );
          })}
        </section>

        {/* Son Haberler listesi */}
        {news.length > 0 && (
          <section className="recent-news">
            <h2>Son Haberler</h2>
            <ul className="news-list">
              {news.map((article) => {
                const style = MARKER_STYLE[article.news_type] || { color: '#0f172a', emoji: '•' };
                const locParts = [
                  article.location?.text && article.location.text !== (article.location?.district ?? '') ? article.location.text : null,
                  article.location?.district,
                ].filter(Boolean);
                return (
                  <li
                    key={article._id}
                    className={`news-list-item${selectedArticle?._id === article._id ? ' active' : ''}${article.location?.coordinates ? '' : ' no-coords'}`}
                    onClick={() => {
                      if (article.location?.coordinates) {
                        setSelectedArticle(article);
                      }
                    }}
                  >
                    <span
                      className="news-list-dot"
                      style={{ backgroundColor: style.color }}
                    >
                      {style.emoji}
                    </span>
                    <div className="news-list-text">
                      <span className="news-list-type">{article.news_type}</span>
                      <span className="news-list-title">{article.title}</span>
                      <span className="news-list-meta">
                        {locParts.length > 0 ? locParts.join(' · ') + ' · ' : ''}
                        {new Date(article.publish_date).toLocaleDateString('tr-TR')}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
        )}
      </aside>

      <main className="map-area">
        {!MAPS_API_KEY && (
          <div className="map-fallback">REACT_APP_GOOGLE_MAPS_API_KEY tanımlı değil.</div>
        )}

        {MAPS_API_KEY && loadError && (
          <div className="map-fallback">
            Google Maps yüklenemedi. API anahtarı/referrer kısıtlarını kontrol et.
            <br />
            {loadError.message}
          </div>
        )}

        {MAPS_API_KEY && !isLoaded && !loadError && (
          <div className="map-fallback">Harita yükleniyor...</div>
        )}

        {MAPS_API_KEY && isLoaded && (
          <GoogleMap
            mapContainerClassName="map-canvas"
            center={mapCenter}
            zoom={11}
            options={{
              mapTypeControl: false,
              streetViewControl: false,
              fullscreenControl: false,
              ...(GOOGLE_MAP_ID ? { mapId: GOOGLE_MAP_ID } : {}),
            }}
          >
            <MapMarkers articles={markerNews} onSelect={setSelectedArticle} />

            {filters.newsType === 'Spor' && (
              <Circle
                center={stadiumCenter}
                radius={1000}
                options={{
                  fillColor: '#16a34a',
                  fillOpacity: 0.08,
                  strokeColor: '#16a34a',
                  strokeOpacity: 0.85,
                  strokeWeight: 2,
                }}
              />
            )}

            {selectedArticle?.location?.coordinates && (
              <InfoWindow
                position={selectedArticle.location.coordinates}
                onCloseClick={() => setSelectedArticle(null)}
              >
                <article className="info-card">
                  <h3>{selectedArticle.title}</h3>
                  <p>
                    <strong>Tarih:</strong>{' '}
                    {new Date(selectedArticle.publish_date).toLocaleDateString('tr-TR')}
                  </p>
                  <p>
                    <strong>Konum:</strong> {selectedArticle.location.text || 'Belirtilmedi'}
                  </p>
                  <div className="info-sources">
                    <strong>Kaynaklar:</strong>
                    {selectedArticle.sources.map((source) => (
                      <a
                        key={source.url}
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        className="info-source-link"
                      >
                        {source.name} — Habere Git →
                      </a>
                    ))}
                  </div>
                </article>
              </InfoWindow>
            )}
          </GoogleMap>
        )}
      </main>
    </div>
  );
}

export default App;
