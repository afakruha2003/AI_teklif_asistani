# AI Kullanım Notları (AI_USAGE.md)

## Genel Yaklaşım

Bu projede **Claude (Anthropic, claude-sonnet-4-6)** asistan olarak kullanıldı. Aşağıdaki bileşenler AI destekli üretildi:

---

## AI ile Üretilen Bileşenler

### Backend Kod İskeleti
- SQLAlchemy ORM modelleri (`models.py`)
- Pydantic şemaları (`schemas.py`)
- 6 zorunlu tool-call implementasyonu (`tool_implementations.py`)
- SSE streaming chat service — LLM ve fallback orkestratör (`chat_service.py`)
- FastAPI endpoint'leri (chat, products, knowledge, quotes, sessions)
- Seed service (`seed_service.py`)
- Docker Compose ve Dockerfile

### Test Altyapısı
- `conftest.py` — SQLite in-memory fixtures
- `tests/test_tools.py` — 24 test, tüm rubrik kategorilerini karşılayacak şekilde

### Dokümantasyon
- `README.md`, `AI_USAGE.md`, `KNOWN_LIMITATIONS.md`

---

## İnsan Katkısı ve Doğrulama Gerektiren Alanlar

AI çıktıları aşağıdaki alanlarda üretildi; production'a çıkmadan **insan gözden geçirmesi** önerilir:

| Alan | Risk | Öneri |
|------|------|-------|
| İş kuralları (fiyat limiti, stok) | Kural bypass edilebilir | Her kural için manuel test |
| Idempotency mantığı | Race condition edge case'leri | Yük testi ile doğrula |
| SSE streaming hata yönetimi | Bağlantı kopması senaryoları | End-to-end test |
| Seed service veri dönüşümü | JSON alan adı uyumsuzluğu | Seed verisiyle çalıştırıp doğrula |

---

## AI Kullanılmayan Alanlar

- `seed_data/` JSON dosyaları (proje tarafından sağlandı)
- İş gereksinimleri ve rubrik analizi (proje dökümanından okundu)
- Veritabanı şeması tasarım kararları (gereksinimlerden türetildi, AI onayladı)

---

## Kullanılan Promptlama Stratejisi

1. Proje PDF'i okunup tüm gereksinimler çıkarıldı.
2. Her bileşen tek seferde üretildi; ardından test hatalarına göre iteratif düzeltme yapıldı.
3. Testler gerçek veritabanı (SQLite in-memory) ile çalıştırıldı — mock kullanılmadı.

---

## Bağımlılık Lisansları

Kullanılan tüm kütüphaneler (FastAPI, SQLAlchemy, OpenAI SDK vb.) MIT veya Apache 2.0 lisanslıdır. Ticari kullanıma uygundur.
