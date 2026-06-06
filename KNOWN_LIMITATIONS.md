# Bilinen Sınırlamalar (KNOWN_LIMITATIONS.md)

Bu belge, proje kapsamında bilinçli olarak dışarıda bırakılan senaryoları ve gelecekte ele alınabilecek iyileştirme alanlarını açıklar.

---

## 1. Retrieval

### 1.1 Semantik Eş Anlamlı Desteği Yok
Alias olmayan semantik eş anlamlılar yakalanamaz. Örneğin `aliases` alanında "el ile tarama cihazı" yoksa bu ifade barkod okuyucuya eşleşmez. LLM modunda model soruyu standart terime dönüştürür; fallback modda alias eklenmesi gerekir.

**Çözüm yolu:** `pgvector` + embedding indexi.

### 1.2 Türkçe Morfoloji Desteği Yok
"okuyucu" ile "okuyucular" veya "okuyu­cu­nun" eşleştirilmiyor. Kısmi çözüm: alias listesine çekimli formlar eklenebilir.

**Çözüm yolu:** PostgreSQL `pg_trgm` + Türkçe stemmer veya embedding.

### 1.3 Çok Dilli Sorgu Desteği Yok
Sistem yalnızca Türkçe sorguları verimli işler. İngilizce terimler ancak ürün adı/açıklamasında geçiyorsa bulunur.

---

## 2. Fallback Modu

### 2.1 Bileşik İstekler
"Şu ürünü kaldır, yerine bunu ekle, toplamı söyle" gibi çok adımlı bileşik istekler fallback modda tek geçişte tam yorumlanamayabilir. Sistem kısmi intent'i (ürün arama veya politika) ele alır; mutasyon için LLM modu önerilir.

### 2.2 Bağlam Takibi Yok
Fallback modu önceki mesajları bağlam olarak kullanmaz. Her mesaj bağımsız değerlendirilir. LLM modu tüm oturum geçmişini taşır.

### 2.3 Belirsiz İntentte Boş Yanıt
Mesaj ne politika ne de ürün kelimeleri içermiyorsa (örn. "merhaba") fallback "Sorunuzu anlayamadım" yanıtı döner. LLM modunda model selamlama yanıtı üretebilir.

---

## 3. Fiyat ve İndirim Kuralları

### 3.1 price_rules Tablosu Pasif
`PriceRule` modeli ve seed yükleyicisi hazır; ancak `add_to_quote` ve `search_products` bu kuralları henüz otomatik uygulamıyor. İş ortağı indirimini hesaplamak için `discount_pct` manuel set edilmeli.

**Çözüm yolu:** `add_to_quote` içinde segment + miktar bazlı kural motoru ekle.

### 3.2 Dinamik Fiyatlama Yok
Ürün fiyatları seed verisiyle sabit. Gerçek zamanlı fiyat güncellemesi için harici fiyat servisi entegrasyonu gerekir.

---

## 4. Kimlik Doğrulama ve Yetkilendirme

Sistemde kullanıcı kimlik doğrulaması yoktur. Tüm API endpoint'leri herkese açıktır. Production ortamı için JWT veya API key tabanlı auth katmanı eklenmesi zorunludur.

---

## 5. Web ve Mobil Arayüz

Bu repo yalnızca **backend**'i kapsar. Web admin paneli ve mobil uygulama ayrı repo/proje olarak geliştirilmelidir. Backend CORS'u açık (`allow_origins=["*"]`) bırakmıştır; production'da kısıtlanmalıdır.

---

## 6. Tool-Call Log Temizleme

`tool_call_logs` tablosunda otomatik temizleme (TTL/vacuum) mekanizması yoktur. Uzun süre çalışan sistemlerde tablo büyüyebilir. Partition veya periyodik temizleme job'ı eklenmelidir.

---

## 7. Streaming Hata Yönetimi

OpenAI API rate limit veya ağ hatası durumunda SSE akışı `error` event ile sonlanır; ancak kısmi tool çağrıları geri alınmaz. İstemci `idempotency_key` ile yeniden denemeli ve `get_quote` ile tutarsızlık kontrolü yapmalıdır.

---

## 8. Ölçekleme

Mevcut mimaride `AsyncSession` per-request kullanılır; bu yeterli ancak yüksek eş zamanlı yükte connection pool ayarlanmalıdır. `engine` parametrelerinde `pool_size` ve `max_overflow` değerleri `.env` ile yapılandırılabilir hale getirilmelidir.

---

## Özet Tablo

| Kapsam Dışı Senaryo | Etki | Öncelik |
|---------------------|------|---------|
| Semantik eş anlamlı arama | Fallback modda bazı sorgular boş dönebilir | Orta |
| Türkçe morfoloji | Çekimli formlar alias olmadan eşleşmez | Düşük |
| price_rules uygulaması | Otomatik indirim hesaplanmıyor | Yüksek |
| Auth/yetkilendirme | API herkese açık | Kritik (production) |
| Bileşik fallback istekleri | Tek geçişte çözülemiyor | Orta |
| SSE kısmi hata geri alma | Manuel idempotency gerekli | Orta |
