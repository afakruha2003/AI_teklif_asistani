from __future__ import annotations

import time
import uuid
import logging
import re
from typing import Optional, List, Dict, Any

from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Product, KnowledgeEntry, Quote, QuoteItem, ToolCallLog, Customer, PriceRule,
    QuoteItemStatus, ToolCallStatus,
)
from app.schemas import (
    SearchProductsInput, GetKnowledgeInput, GetQuoteInput,
    AddToQuoteInput, UpdateQuoteItemInput, ReplaceWithAlternativeInput,
)

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "var", "mı", "mi", "mu", "mü", "mı?", "mi?", "mu?", "mü?",
    "ekler", "misin", "misin?", "ekleyebilir", "ekleyebilir?",
    "nedir", "nedir?", "nasıl", "nasıl?", "kaç", "ne", "bir",
    "için", "ile", "ve", "veya", "ya", "da", "de", "bu", "şu",
    "altı", "üstü", "altında", "üstünde", "aşağı", "yukarı",
    "öner", "önerir", "önerin", "tavsiye", "istiyorum", "istiyorum.",
    "lütfen", "acaba", "bana", "benim",
    "tl", "try", "lira", "₺", "fiyat", "fiyatlı", "fiyatı",
    "ürün", "ürünler", "ürününü", "ürünü",
    "üzerinde", "üstünde",
    "ucuz", "ekonomik", "uygun", "uygun fiyatlı",
    "hizmetleri", "hizmeti", "hizmet", "nelerdir", "neler",
}

_NUMBER_RE = re.compile(r"^\d+([.,]\d+)?$")

CATEGORY_KEYWORDS = {
    "pos_terminal": [
        "el terminali", "el terminal", "elterminali", "terminal", 
        "pos", "el terminalleri", "hand terminal", "mobil terminal"
    ],
    "barcode_scanner": [
        "barkod okuyucu", "barkod", "okuyucu", "scanner", 
        "barkod_okuyucu", "kablosuz okuyucu", "qr okuyucu"
    ],
    "label_printer": [
        "etiket yazıcı", "etiket", "label printer", "etiket_yazici",
        "barkod etiket", "etiket yazici"
    ],
    "receipt_printer": [
        "fiş yazıcı", "fis yazici", "receipt printer", "termal yazıcı"
    ],
    "software": [
        "yazılım", "yazilim", "lisans", "software", "modül", "modul",
        "stok yazılımı", "depo yazılımı"
    ],
    "accessory": [
        "aksesuar", "şarj", "kılıf", "kilif", "batarya", "adaptör",
        "usb-c", "sarj"
    ],
    "service": [
        "kurulum", "servis", "hizmet", "service", "destek"
    ],
    "bundle": [
        "kit", "paket", "bundle", "set", "demo"
    ],
}

# ============= GENİŞLETİLMİŞ KELİME DAĞARCIĞI =============

SPECIAL_PHRASES = {
    # El terminalleri
    "el terminali": "elterminali",
    "el terminal": "elterminali",
    "el terminalleri": "elterminali",
    "hand terminal": "elterminali",
    "mobil terminal": "elterminali",
    "pos cihazı": "elterminali",
    "pos cihazi": "elterminali",
    "satış terminali": "elterminali",
    "satis terminali": "elterminali",
    
    # Barkod okuyucular
    "barkod okuyucu": "barkodokuyucu",
    "barkod okuyucular": "barkodokuyucu",
    "barcode scanner": "barkodokuyucu",
    "kablosuz okuyucu": "barkodokuyucu",
    "qr okuyucu": "barkodokuyucu",
    "scanner": "barkodokuyucu",
    
    # Yazıcılar
    "etiket yazıcı": "etiketyazici",
    "etiket yazici": "etiketyazici",
    "label printer": "etiketyazici",
    "fiş yazıcı": "fisyazici",
    "fis yazici": "fisyazici",
    "receipt printer": "fisyazici",
    "termal yazıcı": "fisyazici",
    "termal yazici": "fisyazici",
    
    # Yazılım
    "yazılım lisansı": "yazilim",
    "yazilim lisansi": "yazilim",
    "stok yazılımı": "yazilim",
    "stok yazilimi": "yazilim",
    "depo yazılımı": "yazilim",
    "depo yazilimi": "yazilim",
    "software license": "yazilim",
    
    # Aksesuarlar
    "şarj adaptörü": "sarj",
    "sarj adaptoru": "sarj",
    "usb c şarj": "usbcsarj",
    "silikon kılıf": "kilif",
    "silikon kilif": "kilif",
    "koruyucu kılıf": "kilif",
    "koruyucu kilif": "kilif",
    "yedek batarya": "batarya",
    
    # Hizmetler
    "kurulum hizmeti": "kurulum",
    "yerinde kurulum": "kurulum",
    "acil kurulum": "acilkurulum",
    "installation service": "kurulum",
}

CATEGORY_KEYWORDS = {
    "pos_terminal": [
        "el terminali", "el terminal", "elterminali", "terminal", 
        "pos", "el terminalleri", "hand terminal", "mobil terminal",
        "pos cihazı", "pos cihazi", "satış terminali", "satis terminali",
        "android terminal", "wifi terminal", "4g terminal", "dokunmatik terminal"
    ],
    "barcode_scanner": [
        "barkod okuyucu", "barkod", "okuyucu", "scanner", 
        "barkod_okuyucu", "kablosuz okuyucu", "qr okuyucu",
        "barcode scanner", "1d scanner", "2d scanner", "kablolu okuyucu",
        "endüstriyel okuyucu", "endustriyel okuyucu", "rugged scanner"
    ],
    "label_printer": [
        "etiket yazıcı", "etiket", "label printer", "etiket_yazici",
        "barkod etiket", "etiket yazici", "etiket makinesi"
    ],
    "receipt_printer": [
        "fiş yazıcı", "fis yazici", "receipt printer", "termal yazıcı",
        "termal yazici", "fiş makinesi", "fis makinesi"
    ],
    "software": [
        "yazılım", "yazilim", "lisans", "software", "modül", "modul",
        "stok yazılımı", "depo yazılımı", "lisans anahtarı",
        "stok programı", "depo programı"
    ],
    "accessory": [
        "aksesuar", "şarj", "kılıf", "kilif", "batarya", "adaptör",
        "usb-c", "sarj", "koruyucu", "yedek", "şarj aleti", "sarj aleti"
    ],
    "service": [
        "kurulum", "servis", "hizmet", "service", "destek",
        "teknik destek", "kurulum hizmeti", "yerinde kurulum"
    ],
    "bundle": [
        "kit", "paket", "bundle", "set", "demo", "başlangıç seti",
        "depo kiti", "saha kiti"
    ],
}


# ============= KELİME EŞLEŞME SCORING =============

def _tokenize(text: str) -> list[str]:
    """Tokenize search query with advanced phrase protection."""
    text = text.lower()
    
    # Özel phrase'leri koru (öncelikli)
    for phrase, replacement in SPECIAL_PHRASES.items():
        if phrase in text:
            text = text.replace(phrase, replacement)
    
    # Türkçe karakter normalizasyonu
    turkish_map = str.maketrans("ğüşıöç", "gusioc")
    text = text.translate(turkish_map)
    
    # Noktalama işaretlerini temizle
    for punc in "?.!,;:()\"'":
        text = text.replace(punc, " ")
    
    # Underscore'ları boşluğa çevir
    text = text.replace("_", " ")
    
    # Fazla boşlukları temizle
    text = " ".join(text.split())
    
    tokens = text.split()
    result = []
    
    for t in tokens:
        if len(t) < 2:
            continue
        if t in _STOPWORDS:
            continue
        if _NUMBER_RE.match(t):
            continue
        result.append(t)
    
    # Eğer token yoksa, anlamlı kelimeleri dene
    if not result:
        meaningful = [w for w in text.split() if len(w) > 2 and w not in _STOPWORDS]
        result = meaningful[:5]
    
    return result


def _score_product(p: Product, tokens: list[str]) -> int:
    
    if not tokens:
        return 1
    
    name_lower = p.name.lower()
    desc_lower = (p.description or "").lower()
    category_lower = p.category.lower()
    
    # Handle aliases (dict or list)
    aliases = p.aliases
    if isinstance(aliases, dict):
        tr_aliases = [a.lower() for a in aliases.get('tr', [])]
    elif isinstance(aliases, list):
        tr_aliases = [a.lower() for a in aliases]
    else:
        tr_aliases = []
    
    tags_lower = [t.lower() for t in (p.tags or [])]
    sku_lower = (p.sku or "").lower()
    
    def normalize(text: str) -> str:
        """Normalize text by removing spaces and Turkish chars."""
        text = text.translate(str.maketrans("ğüşıöç", "gusioc"))
        return text.replace(" ", "")
    
    name_norm = normalize(name_lower)
    category_norm = normalize(category_lower)
    
    score = 0
    
    for token in tokens:
        token_norm = normalize(token)
        token_original = token
        
        for cat, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                keyword_norm = normalize(keyword)
                if token_norm == keyword_norm:
                    if cat == category_norm:
                        score += 50  # Exact category match
                    else:
                        score += 10  # Category keyword but different category
                    break
        
        if token_original in name_lower:
            score += 30
        elif token_norm in name_norm:
            score += 20
        
        token_parts = token_original.split()
        name_parts = name_lower.split()
        
        for part in token_parts:
            if part in name_parts:
                score += 10
            else:
                # Check if part is contained in any name part
                for name_part in name_parts:
                    if part in name_part or name_part in part:
                        score += 5
                        break
        
        if len(token_parts) > 1:
            all_parts_found = all(
                any(part in name_part or name_part in part for name_part in name_parts)
                for part in token_parts
            )
            if all_parts_found:
                score += 15
        
        if token_original in desc_lower:
            score += 5
        elif token_norm in normalize(desc_lower):
            score += 3
        
        for alias in tr_aliases:
            alias_norm = normalize(alias)
            if token_original in alias:
                score += 10
                break
            elif token_norm in alias_norm:
                score += 7
                break
        
        for tag in tags_lower:
            tag_norm = normalize(tag)
            if token_original in tag:
                score += 5
                break
            elif token_norm in tag_norm:
                score += 3
                break
        
        if token_original in sku_lower:
            score += 8
        
        token_normalized = token_original.translate(str.maketrans("ğüşıöç", "gusioc"))
        name_normalized = name_lower.translate(str.maketrans("ğüşıöç", "gusioc"))
        if token_normalized in name_normalized:
            score += 2
    
    return score


def detect_category_from_query(query: str) -> Optional[str]:
    """
    Detect product category from query string with advanced matching.
    Returns the most likely category or None.
    """
    query_lower = query.lower()
    query_normalized = query_lower.translate(str.maketrans("ğüşıöç", "gusioc"))
    
    category_scores = {cat: 0 for cat in CATEGORY_KEYWORDS.keys()}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            keyword_normalized = keyword.translate(str.maketrans("ğüşıöç", "gusioc"))
            if keyword_normalized in query_normalized:
                category_scores[category] += 10
            elif keyword in query_lower:
                category_scores[category] += 5
    
    # Find category with highest score
    best_category = max(category_scores.items(), key=lambda x: x[1])
    
    if best_category[1] > 0:
        return best_category[0]
    
    return None


def extract_price_limit_from_query(query: str) -> Optional[float]:
    
    query_lower = query.lower()
    
    
    patterns = [
        r'(\d+(?:[.,]\d+)?)\s*(?:tl|try|lira|₺)\s*(?:altında|altı|alti)',
        r'(?:altında|altı|alti)\s*(\d+(?:[.,]\d+)?)\s*(?:tl|try|lira|₺)',
        r'max\s*(\d+(?:[.,]\d+)?)\s*(?:tl|try|lira|₺)',
        r'maksimum\s*(\d+(?:[.,]\d+)?)\s*(?:tl|try|lira|₺)',
        r'(\d+(?:[.,]\d+)?)\s*(?:tl|try|lira|₺)\s*(?:ve altı|ve alti)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            price_str = match.group(1).replace(",", "").replace(".", "")
            try:
                return float(price_str)
            except ValueError:
                pass
    
    
    turkish_numbers = {
        "yüz": 100, "ikiyüz": 200, "üçyüz": 300, "dörtyüz": 400, "beşyüz": 500,
        "altıyüz": 600, "yediyüz": 700, "sekizyüz": 800, "dokuzyüz": 900,
        "bin": 1000, "ikibin": 2000, "üçbin": 3000, "dörtbin": 4000, "beşbin": 5000,
        "onbin": 10000
    }
    
    for word, value in turkish_numbers.items():
        if word in query_lower and ("tl" in query_lower or "lira" in query_lower):
            return float(value)
    
    return None



def detect_category_from_query(query: str) -> Optional[str]:
    """Detect product category from query string."""
    query_lower = query.lower()
    query_normalized = query_lower.replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ı", "i").replace("ö", "o").replace("ç", "c")
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            keyword_norm = keyword.replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ı", "i").replace("ö", "o").replace("ç", "c")
            if keyword_norm in query_normalized:
                return category
    return None


def _tokenize(text: str) -> list[str]:
    """Tokenize search query for matching with phrase protection."""
    text = text.lower()
    
    # Özel phrase'leri koru ve normalize et
    for phrase, replacement in SPECIAL_PHRASES.items():
        if phrase in text:
            text = text.replace(phrase, replacement)
    
    # Türkçe karakter normalizasyonu
    text = text.replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ı", "i").replace("ö", "o").replace("ç", "c")
    
    # Underscore'ları boşluğa çevir
    text = text.replace("_", " ")
    
    tokens = text.split()
    result = []
    for t in tokens:
        clean = t.strip("?.!,;:()")
        if not clean:
            continue
        if clean in _STOPWORDS:
            continue
        if _NUMBER_RE.match(clean):
            continue
        result.append(clean)
    
    # Eğer token yoksa, orijinal query'nin kelimelerini dene
    if not result:
        result = [w for w in text.split() if len(w) > 2]
    
    return result


def _score_product(p: Product, tokens: list[str]) -> int:
    """Score product based on token matching with category priority."""
    if not tokens:
        return 1
    
    name_lower = p.name.lower()
    desc_lower = (p.description or "").lower()
    category_lower = p.category.lower()
    
    # Handle aliases
    aliases = p.aliases
    if isinstance(aliases, dict):
        tr_aliases = [a.lower() for a in aliases.get('tr', [])]
    elif isinstance(aliases, list):
        tr_aliases = [a.lower() for a in aliases]
    else:
        tr_aliases = []
    
    tags_lower = [t.lower() for t in (p.tags or [])]
    
    def normalize(text: str) -> str:
        """Normalize text for matching (remove spaces and Turkish chars)."""
        text = text.replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ı", "i").replace("ö", "o").replace("ç", "c")
        return text.replace(" ", "")
    
    name_norm = normalize(name_lower)
    category_norm = normalize(category_lower)
    
    # Token'ları normalize et
    normalized_tokens = []
    for token in tokens:
        token_norm = normalize(token)
        normalized_tokens.append((token, token_norm))
    
    score = 0
    
    for token, token_norm in normalized_tokens:
        # Category matching (highest priority)
        for cat, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                keyword_norm = normalize(keyword)
                if token_norm == keyword_norm and cat == category_norm:
                    score += 50
                    break
        
        # Direct name matching (original)
        if token in name_lower:
            score += 10
        elif token_norm in name_norm:
            score += 8
        
        # Partial word matching (for "el terminali" vs "El Terminali")
        token_parts = token.replace("_", " ").split()
        name_parts = name_lower.split()
        for part in token_parts:
            if part in name_parts:
                score += 5
            # Check if part is contained in any name part
            for name_part in name_parts:
                if part in name_part or name_part in part:
                    score += 3
        
        # Check if all token parts appear in name (phrase match)
        if len(token_parts) > 1:
            all_parts_found = all(any(part in name_part or name_part in part for name_part in name_parts) for part in token_parts)
            if all_parts_found:
                score += 15
        
        # Description matching
        if token in desc_lower:
            score += 3
        elif token_norm in normalize(desc_lower):
            score += 2
        
        # Alias matching
        for alias in tr_aliases:
            alias_norm = normalize(alias)
            if token in alias:
                score += 8
                break
            elif token_norm in alias_norm:
                score += 5
                break
        
        # Tag matching
        for tag in tags_lower:
            tag_norm = normalize(tag)
            if token in tag:
                score += 5
                break
            elif token_norm in tag_norm:
                score += 3
                break
    
    return score


def _clean_query(query: str) -> str:
    """Clean query string from common question patterns."""
    for token in ("var mı?", "var mi?", "ekler misin?", "ekler misin",
                  "ekleyebilir misin?", "ekleyebilir misin", "?", "."):
        query = query.replace(token, "")
    return " ".join(query.split()).strip()




def _score_knowledge(e: KnowledgeEntry, tokens: list[str]) -> int:
    """Score knowledge entry based on token matching."""
    if not tokens:
        return 1
    title_lower = e.title.lower()
    raw_body = getattr(e, "content", None) or getattr(e, "body", None) or ""
    content_lower = raw_body.lower()
    tags_lower = [t.lower() for t in (e.tags or [])]
    
    def normalize(text: str) -> str:
        return text.replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ı", "i").replace("ö", "o").replace("ç", "c")
    
    score = 0
    for token in tokens:
        token_norm = normalize(token)
        if token_norm in normalize(title_lower):
            score += 10
        if token_norm in normalize(content_lower):
            score += 5
        if any(token_norm in normalize(t) for t in tags_lower):
            score += 7
    return score


def _serialize_product(p: Product) -> dict:
    """Serialize product with all fields."""
    aliases = p.aliases
    if isinstance(aliases, dict):
        tr_aliases = aliases.get('tr', [])
    elif isinstance(aliases, list):
        tr_aliases = aliases
    else:
        tr_aliases = []
    
    return {
        "id": p.id,
        "name": p.name,
        "name_tr": p.name,
        "description": p.description,
        "category": p.category,
        "price_try": float(p.price_try),
        "stock": p.stock,
        "sku": p.sku,
        "aliases": tr_aliases,
        "tags": p.tags or [],
        "is_active": p.is_active,
        "alternative_product_id": p.alternative_product_id,
        "substitute_product_ids": getattr(p, 'substitute_product_ids', []),
        "min_order_qty": getattr(p, 'min_order_qty', 1),
        "delivery_days": getattr(p, 'delivery_days', 3),
        "warranty_months": getattr(p, 'warranty_months', 24),
    }


def _serialize_knowledge(e: KnowledgeEntry) -> dict:
    """Serialize knowledge entry with all fields."""
    body = getattr(e, "content", None) or getattr(e, "body", None) or ""
    return {
        "knowledge_id": e.id,
        "topic": getattr(e, 'topic', e.category),
        "title": e.title,
        "content": body,
        "category": e.category,
        "tags": e.tags or [],
        "applies_to": getattr(e, 'applies_to', []),
        "source": getattr(e, 'source', None),
    }


def _serialize_quote_item(item: QuoteItem, product_name: Optional[str]) -> dict:
    """Serialize quote item."""
    qty = item.quantity
    unit = float(item.unit_price_try)
    disc = float(item.discount_pct)
    return {
        "id": item.id,
        "item_id": item.id,
        "product_id": item.product_id,
        "product_name": product_name,
        "sku": getattr(item, "sku", None),
        "quantity": qty,
        "unit_price_try": unit,
        "discount_pct": disc,
        "line_total_try": round(qty * unit * (1 - disc / 100), 2),
        "status": item.status.value if hasattr(item.status, "value") else item.status,
        "is_backorder": item.is_backorder,
    }


def _serialize_quote(quote: Quote, product_names: Dict[str, str]) -> dict:
    """Serialize quote with all items."""
    serialized_items = [
        _serialize_quote_item(item, product_names.get(item.product_id))
        for item in quote.items
    ]
    active_items = [i for i in serialized_items if i["status"] == "active"]
    total_amount = sum(i["line_total_try"] for i in active_items)
    return {
        "id": quote.id,
        "quote_id": quote.id,
        "customer_id": quote.customer_id,
        "status": quote.status,
        "items": serialized_items,
        "active_items_count": len(active_items),
        "total_try": round(total_amount, 2),
    }


async def _log_tool_call(
    db: AsyncSession,
    session_id: str,
    tool_name: str,
    input_data: dict,
    output_data: dict,
    status: ToolCallStatus,
    quote_delta: Optional[dict],
    sequence_num: int,
    duration_ms: int,
    idempotency_key: Optional[str] = None,
) -> None:
    """Log tool call for audit and idempotency."""
    log_entry = ToolCallLog(
        id=str(uuid.uuid4()),
        session_id=session_id,
        tool_name=tool_name,
        input_data=input_data,
        output_data=output_data,
        status=status,
        quote_delta=quote_delta,
        sequence_num=sequence_num,
        duration_ms=duration_ms,
        idempotency_key=idempotency_key,
    )
    db.add(log_entry)


async def _get_customer_segment(db: AsyncSession, customer_id: Optional[str]) -> str:
    """Get customer segment for discount calculation."""
    if not customer_id:
        return "standard"
    customer = await db.get(Customer, customer_id)
    if not customer:
        return "standard"
    return customer.segment.value if hasattr(customer.segment, "value") else str(customer.segment)


async def _get_discount(
    db: AsyncSession,
    product_id: str,
    category: str,
    segment: str,
    quantity: int,
    quote_products: List[str] = None,
    sku: str = None,
) -> float:
    """
    Calculate discount based on price rules.
    Supports:
    - Partner category quantity discount (3+ items, 7%)
    - Accessory quantity discount (5+ items, 5%)
    - Bundle no discount
    - Software bundle discount (Pro + Module = 8%)
    - Plus variant volume discount (4+ items, 6%)
    """
    rule_stmt = (
        select(PriceRule)
        .where(
            PriceRule.is_active == True,
            or_(
                PriceRule.segment == segment,
                PriceRule.segment == None
            ),
            or_(
                PriceRule.product_id == product_id,
                PriceRule.product_id == None
            ),
            or_(
                func.lower(PriceRule.category) == category.lower(),
                PriceRule.category == None
            ),
        )
        .order_by(PriceRule.priority.desc())
    )
    result = await db.execute(rule_stmt)
    rules = list(result.scalars().all())
    
    highest_discount = 0.0
    
    for rule in rules:
        min_qty = getattr(rule, 'min_quantity', 1)
        if quantity < min_qty:
            continue
        
        condition = getattr(rule, 'condition', None) or getattr(rule, 'condition_text', '')
        
        # Partner discount
        if 'partner' in condition.lower() and 'category_qty >= 3' in condition.lower():
            if segment.lower() == 'partner':
                highest_discount = max(highest_discount, float(rule.discount_pct))
        
        # Accessory discount
        elif 'accessory' in condition.lower() and 'product_qty >= 5' in condition.lower():
            if category.lower() == 'accessory' and quantity >= 5:
                highest_discount = max(highest_discount, float(rule.discount_pct))
        
        # Bundle: no extra discount
        elif 'bundle' in condition.lower() or category.lower() == 'bundle':
            return 0.0
        
        # Software bundle
        elif 'software' in condition.lower() and 'prd-sw-520' in condition.lower():
            if quote_products and 'PRD-SW-520' in quote_products and 'PRD-SW-530' in quote_products:
                highest_discount = max(highest_discount, float(rule.discount_pct))
        
        # Plus variant volume discount
        elif 'plus' in condition.lower() and 'product_qty >= 4' in condition.lower():
            if sku and 'PLUS' in sku.upper() and quantity >= 4:
                highest_discount = max(highest_discount, float(rule.discount_pct))
        
        # Simple discount rule
        else:
            if quantity >= min_qty:
                highest_discount = max(highest_discount, float(rule.discount_pct))
    
    return highest_discount


async def _safe_rollback(db: AsyncSession) -> None:
    """Transaction bozuksa sessizce rollback yap."""
    try:
        await db.rollback()
    except Exception:
        pass
async def search_products(
    db: AsyncSession,
    params: SearchProductsInput,
    session_id: str,
    sequence_num: int = 0,
    skip_logging: bool = False,
) -> Dict[str, Any]:
    """
    Search products with:
    - Automatic category detection
    - Price limit extraction from natural language
    - Token-based matching with advanced scoring
    - Context-aware alternative suggestions
    - Same-category recommendations
    """
    await _safe_rollback(db)
    start_time = time.monotonic()

    try:
        search_query = params.query or ""
        if not search_query.strip():
            search_query = "ürün"
        
        # Extract price limit from query if not provided
        effective_price_limit = params.max_price_try
        if effective_price_limit is None:
            effective_price_limit = extract_price_limit_from_query(search_query)
            if effective_price_limit:
                logger.info(f"💰 Extracted price limit from query: {effective_price_limit}")
        
        logger.info(f"🔍 SEARCH_PRODUCTS - Query: '{search_query}', Max Price: {effective_price_limit}, Category: {params.category}")
        
        # ========== 1. KATEGORİ TESPİTİ ==========
        detected_category = params.category
        if not detected_category:
            detected_category = detect_category_from_query(search_query)
            if detected_category:
                logger.info(f"🎯 Detected category: {detected_category}")
        
        # ========== 2. FİYAT LİMİTİ OLMADAN ARA (KATEGORİ VARSA) ==========
        # Eğer kategori varsa, önce fiyat limiti olmadan bul ve filtrele
        products = []
        
        if detected_category and effective_price_limit:
            # İlk önce fiyat limiti olmadan kategori ürünlerini bul
            stmt_no_limit = select(Product).where(
                Product.is_active == True,
                func.lower(Product.category) == detected_category.lower()
            )
            
            if params.in_stock_only:
                stmt_no_limit = stmt_no_limit.where(Product.stock > 0)
            
            result_no_limit = await db.execute(stmt_no_limit.limit(200))
            all_category_products = list(result_no_limit.scalars().all())
            
            if all_category_products:
                logger.info(f"📊 Found {len(all_category_products)} products in category {detected_category}")
                
                # Fiyat limitine göre filtrele
                products = [p for p in all_category_products if p.price_try <= effective_price_limit]
                
                if products:
                    logger.info(f"✅ {len(products)} products within budget {effective_price_limit}")
                else:
                    # Fiyat limiti altında ürün yok, en yakınları göster
                    min_price = min(p.price_try for p in all_category_products)
                    logger.info(f"⚠️ No products under {effective_price_limit}. Min price in category: {min_price}")
        
        # Eğer kategori yoksa veya ürün bulunamadıysa, normal sorgu yap
        if not products:
            stmt = select(Product).where(Product.is_active == True)
            
            if effective_price_limit is not None:
                stmt = stmt.where(Product.price_try <= effective_price_limit)
            
            if detected_category:
                stmt = stmt.where(func.lower(Product.category) == detected_category.lower())
            
            if params.in_stock_only:
                stmt = stmt.where(Product.stock > 0)

            result = await db.execute(stmt.limit(200))
            products = list(result.scalars().all())
            
            logger.info(f"📊 Base query found: {len(products)} products")

        # ========== 3. TOKEN-BASED FILTERING ==========
        if search_query and products:
            tokens = _tokenize(_clean_query(search_query))
            logger.info(f"🔤 Tokens: {tokens}")
            
            if tokens:
                scored: list[tuple[Product, int]] = []
                for p in products:
                    score = _score_product(p, tokens)
                    if score > 0:
                        scored.append((p, score))
                        logger.debug(f"   Score for {p.name}: {score}")
                
                scored.sort(key=lambda x: x[1], reverse=True)
                products = [p for p, _ in scored[: params.limit]] if scored else []
                logger.info(f"📊 After scoring: {len(products)} products matched")
            else:
                products = products[: params.limit]

        # ========== 4. TAG FILTERING ==========
        if params.tags and products:
            target = [t.lower() for t in params.tags]
            products = [p for p in products if any(t.lower() in target for t in (p.tags or []))]

        serialized = [_serialize_product(p) for p in products]
        output = {
            "products": serialized, 
            "count": len(serialized),
            "detected_category": detected_category,
            "original_query": search_query,
            "price_limit_used": effective_price_limit
        }
        
        # ========== 5. AKILLI ALTERNATİF ÖNERİLER ==========
        if not products and effective_price_limit and effective_price_limit > 0:
            category_to_search = detected_category or params.category
            
            # Strategy 1: Aynı kategoride, limitin üstünde en yakın fiyatlı ürünler
            if category_to_search:
                stmt_same_category = select(Product).where(
                    Product.is_active == True,
                    Product.stock > 0,
                    func.lower(Product.category) == category_to_search.lower(),
                    Product.price_try > effective_price_limit
                ).order_by(Product.price_try.asc()).limit(5)
                
                result_same = await db.execute(stmt_same_category)
                same_category_products = list(result_same.scalars().all())
                
                if same_category_products:
                    min_price = min(p.price_try for p in same_category_products)
                    category_display = category_to_search.replace("_", " ").title()
                    
                    output["suggestions"] = {
                        "type": "same_category",
                        "category": category_to_search,
                        "message": f"{effective_price_limit:,.0f} TL bütçenizle {category_display} kategorisinde uygun ürün bulunamadı.",
                        "products": [_serialize_product(p) for p in same_category_products],
                        "price_limit": effective_price_limit,
                        "min_available_price": min_price,
                        "price_difference": round(min_price - effective_price_limit, 2),
                        "suggestion": f"Bütçenizi {min_price:,.0f} TL'ye çıkarmanızı öneririm."
                    }
                    logger.info(f"💡 Same category suggestions: {len(same_category_products)} products")
                
                # Strategy 2: Aynı kategoride tüm ürünler (bilgi amaçlı)
                if "suggestions" not in output:
                    stmt_all_category = select(Product).where(
                        Product.is_active == True,
                        Product.stock > 0,
                        func.lower(Product.category) == category_to_search.lower()
                    ).order_by(Product.price_try.asc()).limit(5)
                    
                    result_all = await db.execute(stmt_all_category)
                    all_category_products = list(result_all.scalars().all())
                    
                    if all_category_products:
                        min_price = min(p.price_try for p in all_category_products)
                        output["suggestions"] = {
                            "type": "category_info",
                            "category": category_to_search,
                            "message": f"{category_display} kategorisindeki en ucuz ürün {min_price:,.0f} TL'dir.",
                            "products": [_serialize_product(p) for p in all_category_products],
                            "min_available_price": min_price
                        }
                        logger.info(f"💡 Category info suggestions: {len(all_category_products)} products")
            
            # Strategy 3: Hiçbir kategori yoksa, genel yakın fiyatlı ürünler
            if "suggestions" not in output:
                stmt_nearby = select(Product).where(
                    Product.is_active == True,
                    Product.stock > 0,
                    Product.price_try > effective_price_limit,
                    Product.price_try <= effective_price_limit * 2
                ).order_by(Product.price_try.asc()).limit(5)
                
                result_nearby = await db.execute(stmt_nearby)
                nearby_products = list(result_nearby.scalars().all())
                
                if nearby_products:
                    output["suggestions"] = {
                        "type": "nearby_price",
                        "message": f"{effective_price_limit:,.0f} TL altında ürün bulunamadı. Bütçenize en yakın ürünler:",
                        "products": [_serialize_product(p) for p in nearby_products],
                        "price_limit": effective_price_limit,
                        "min_available_price": min(p.price_try for p in nearby_products)
                    }
                    logger.info(f"💡 Nearby price suggestions: {len(nearby_products)} products")
        
        # ========== 6. FİYAT LİMİTİ OLMADAN SONUÇ ==========
        if not products and not effective_price_limit:
            stmt_top = select(Product).where(
                Product.is_active == True,
                Product.stock > 0
            ).order_by(Product.price_try.asc()).limit(params.limit)
            
            result_top = await db.execute(stmt_top)
            top_products = list(result_top.scalars().all())
            
            if top_products:
                output["products"] = [_serialize_product(p) for p in top_products]
                output["count"] = len(top_products)
                output["message"] = "En uygun fiyatlı ürünler:"

        # ========== 7. LOGGING ==========
        logger.info(f"📦 Final result: {output['count']} products returned")
        for p in output.get("products", [])[:3]:
            logger.info(f"   -> {p['name']} - {p['price_try']} TRY")
        
        if "suggestions" in output:
            logger.info(f"💡 Suggestions type: {output['suggestions']['type']}")

        duration_ms = int((time.monotonic() - start_time) * 1000)
        if not skip_logging:
            await _log_tool_call(
                db, session_id, "search_products", params.model_dump(), output,
                ToolCallStatus.success, None, sequence_num, duration_ms,
            )
            await db.commit()
        return output

    except Exception as e:
        logger.error(f"❌ Search products error: {e}")
        await _safe_rollback(db)
        return {"products": [], "count": 0, "error": str(e)}


async def get_knowledge_entries(
    db: AsyncSession,
    params: GetKnowledgeInput,
    session_id: str,
    sequence_num: int = 0,
    skip_logging: bool = False,
) -> Dict[str, Any]:
    """Get knowledge entries with topic and category filtering."""
    await _safe_rollback(db)
    start_time = time.monotonic()

    try:
        search_query = params.query or ""
        if not search_query.strip():
            search_query = "bilgi"
        
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.is_active == True)
        
        if hasattr(params, 'topic') and params.topic:
            stmt = stmt.where(KnowledgeEntry.topic == params.topic)
        
        if params.category:
            stmt = stmt.where(func.lower(KnowledgeEntry.category) == params.category.lower())

        result = await db.execute(stmt.limit(100))
        entries: List[KnowledgeEntry] = list(result.scalars().all())

        if search_query:
            tokens = _tokenize(search_query)
            if tokens:
                scored: list[tuple[KnowledgeEntry, int]] = []
                for e in entries:
                    score = _score_knowledge(e, tokens)
                    if score > 0:
                        scored.append((e, score))
                scored.sort(key=lambda x: x[1], reverse=True)
                entries = [e for e, _ in scored[: params.limit]]
            else:
                entries = entries[: params.limit]
        else:
            entries = entries[: params.limit]

        if params.tags:
            target = [t.lower() for t in params.tags]
            entries = [e for e in entries if any(t.lower() in target for t in (e.tags or []))]

        serialized = [_serialize_knowledge(e) for e in entries]
        output = {"knowledge_entries": serialized, "count": len(serialized)}

        duration_ms = int((time.monotonic() - start_time) * 1000)
        if not skip_logging:
            await _log_tool_call(
                db, session_id, "get_knowledge_entries", params.model_dump(), output,
                ToolCallStatus.success, None, sequence_num, duration_ms,
            )
            await db.commit()
        return output

    except Exception as e:
        await _safe_rollback(db)
        return {"knowledge_entries": [], "count": 0, "error": str(e)}


async def get_quote(
    db: AsyncSession,
    params: GetQuoteInput,
    session_id: str,
    sequence_num: int = 0,
) -> Dict[str, Any]:
    """Get current quote state."""
    await _safe_rollback(db)
    start_time = time.monotonic()

    try:
        stmt = (
            select(Quote)
            .where(Quote.id == params.quote_id)
            .options(selectinload(Quote.items).selectinload(QuoteItem.product))
        )
        result = await db.execute(stmt)
        quote = result.scalar_one_or_none()

        if not quote:
            output = {"error": f"Quote {params.quote_id} not found"}
            status = ToolCallStatus.error
        else:
            product_names: Dict[str, str] = {}
            for item in quote.items:
                if item.product:
                    product_names[item.product_id] = item.product.name
            output = _serialize_quote(quote, product_names)
            status = ToolCallStatus.success

        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(
            db, session_id, "get_quote", params.model_dump(), output,
            status, None, sequence_num, duration_ms,
        )
        await db.commit()
        return output

    except Exception as e:
        await _safe_rollback(db)
        return {"error": str(e)}


async def add_to_quote(
    db: AsyncSession,
    params: Any,
    session_id: str,
    sequence_num: int = 0,
) -> Dict[str, Any]:
    """Add product to quote with idempotency support."""
    await _safe_rollback(db)
    start_time = time.monotonic()

    try:
        # Idempotency check
        if params.idempotency_key:
            existing_log = await db.execute(
                select(ToolCallLog).where(
                    ToolCallLog.idempotency_key == params.idempotency_key,
                    ToolCallLog.tool_name == "add_to_quote"
                )
            )
            existing = existing_log.scalar_one_or_none()
            if existing:
                logger.info(f"🔄 Idempotent request detected: {params.idempotency_key}")
                output = {
                    "idempotent": True, 
                    "message": "Duplicate request ignored",
                    "previous_result": existing.output_data
                }
                duration_ms = int((time.monotonic() - start_time) * 1000)
                await _log_tool_call(
                    db, session_id, "add_to_quote", params.model_dump(), output,
                    ToolCallStatus.success, existing.quote_delta, sequence_num, duration_ms,
                    idempotency_key=params.idempotency_key,
                )
                await db.commit()
                return output

        # Get or create quote
        if not params.quote_id or params.quote_id in ("null", "None"):
            stmt = select(Quote).where(Quote.session_id == session_id).order_by(Quote.id.desc())
            quote_res = await db.execute(stmt)
            existing_quote = quote_res.scalar_one_or_none()
            if existing_quote:
                params.quote_id = existing_quote.id
            else:
                new_quote = Quote(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    customer_id=getattr(params, 'customer_id', None),
                    status="draft",
                )
                db.add(new_quote)
                await db.flush()
                params.quote_id = new_quote.id

        product = await db.get(Product, params.product_id)
        if not product or not product.is_active:
            output = {"error": f"Product {params.product_id} not found or inactive"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "add_to_quote", params.model_dump(), output,
                                 ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        product_id = product.id
        product_name = product.name
        product_price = float(product.price_try)
        product_stock = product.stock
        product_category = product.category

        # Price limit check
        if params.max_price_try is not None and product_price > params.max_price_try:
            output = {"error": "Product price exceeds max_price_try", "rule_violated": "price_limit"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "add_to_quote", params.model_dump(), output,
                                 ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        quote = await db.get(Quote, params.quote_id)
        customer_id = quote.customer_id if quote else None
        segment = await _get_customer_segment(db, customer_id)

        existing_item_result = await db.execute(
            select(QuoteItem).where(
                QuoteItem.quote_id == params.quote_id,
                QuoteItem.product_id == params.product_id,
                QuoteItem.status == "active",
            )
        )
        curr_item = existing_item_result.scalar_one_or_none()

        curr_item_id = curr_item.id if curr_item else None
        curr_item_qty = curr_item.quantity if curr_item else 0
        simulated_qty = params.quantity + curr_item_qty

        # Get all product IDs in quote for bundle discount
        quote_products_result = await db.execute(
            select(QuoteItem.product_id).where(
                QuoteItem.quote_id == params.quote_id,
                QuoteItem.status == "active"
            )
        )
        quote_products = [p for p in quote_products_result.scalars().all()]

        applied_discount = await _get_discount(
            db, product_id, product_category, segment, simulated_qty, 
            quote_products, product.sku
        )

        is_backorder = False
        if product_stock <= 0 or product_stock < params.quantity:
            if not params.allow_backorder:
                output = {
                    "error": "Product is out of stock or insufficient stock",
                    "rule_violated": "out_of_stock",
                    "product_id": product_id,
                    "current_stock": product_stock,
                }
                duration_ms = int((time.monotonic() - start_time) * 1000)
                await _log_tool_call(db, session_id, "add_to_quote", params.model_dump(), output,
                                     ToolCallStatus.error, None, sequence_num, duration_ms)
                await db.commit()
                return output
            is_backorder = True

        if curr_item:
            curr_item.quantity = simulated_qty
            curr_item.discount_pct = applied_discount
            action = "update"
            item_id = curr_item_id
            final_qty = simulated_qty
        else:
            new_item = QuoteItem(
                id=str(uuid.uuid4()),
                quote_id=params.quote_id,
                product_id=product_id,
                quantity=params.quantity,
                unit_price_try=product_price,
                discount_pct=applied_discount,
                status="active",
                is_backorder=is_backorder,
                source_message_id=getattr(params, 'source_message_id', None),
                idempotency_key=params.idempotency_key,
            )
            db.add(new_item)
            action = "add"
            item_id = new_item.id
            final_qty = params.quantity

        if not is_backorder:
            product.stock -= params.quantity

        quote_delta = {
            "action": action,
            "item_id": item_id,
            "product_id": product_id,
            "product_name": product_name,
            "quantity": final_qty,
            "unit_price": product_price,
            "applied_discount_pct": applied_discount,
        }
        output = {"success": True, "quote_id": params.quote_id, **quote_delta}

        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(
            db, session_id, "add_to_quote", params.model_dump(), output,
            ToolCallStatus.success, quote_delta, sequence_num, duration_ms,
            idempotency_key=params.idempotency_key,
        )
        await db.commit()
        return output

    except Exception as e:
        await _safe_rollback(db)
        return {"error": str(e)}


async def update_quote_item(
    db: AsyncSession,
    params: UpdateQuoteItemInput,
    session_id: str,
    sequence_num: int = 0,
) -> Dict[str, Any]:
    """Update quote item quantity."""
    await _safe_rollback(db)
    start_time = time.monotonic()

    try:
        item = await db.get(QuoteItem, params.item_id)
        if not item or item.quote_id != params.quote_id:
            output = {"error": "Quote item not found"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "update_quote_item", params.model_dump(), output,
                                 ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        if item.status != QuoteItemStatus.active:
            output = {"error": "Cannot update non-active item"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "update_quote_item", params.model_dump(), output,
                                 ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        old_qty = item.quantity
        item_product_id = item.product_id
        item_is_backorder = item.is_backorder
        item_discount = float(item.discount_pct)

        product = await db.get(Product, item_product_id)
        product_stock = product.stock if product else 1
        product_category = product.category if product else ""

        if params.quantity == 0:
            item.status = QuoteItemStatus.removed
            action = "item_removed"
            new_qty = 0
            applied_discount = item_discount
        else:
            if product_stock <= 0 and not item_is_backorder:
                output = {"error": "Product is out of stock, cannot modify quantity",
                          "rule_violated": "out_of_stock"}
                duration_ms = int((time.monotonic() - start_time) * 1000)
                await _log_tool_call(db, session_id, "update_quote_item", params.model_dump(), output,
                                     ToolCallStatus.error, None, sequence_num, duration_ms)
                await db.commit()
                return output

            quote = await db.get(Quote, params.quote_id)
            customer_id = quote.customer_id if quote else None
            segment = await _get_customer_segment(db, customer_id)
            
            # Get all product IDs in quote for bundle discount
            quote_products_result = await db.execute(
                select(QuoteItem.product_id).where(
                    QuoteItem.quote_id == params.quote_id,
                    QuoteItem.status == "active"
                )
            )
            quote_products = [p for p in quote_products_result.scalars().all()]
            
            applied_discount = await _get_discount(
                db, item_product_id, product_category, segment, params.quantity, 
                quote_products, product.sku if product else None
            )
            item.quantity = params.quantity
            item.discount_pct = applied_discount
            action = "quantity_updated"
            new_qty = params.quantity

        quote_delta = {
            "action": action,
            "item_id": params.item_id,
            "old_quantity": old_qty,
            "new_quantity": new_qty,
            "applied_discount_pct": applied_discount,
        }
        output = {"success": True, "quote_id": params.quote_id, **quote_delta}

        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(
            db, session_id, "update_quote_item", params.model_dump(), output,
            ToolCallStatus.success, quote_delta, sequence_num, duration_ms,
        )
        await db.commit()
        return output

    except Exception as e:
        await _safe_rollback(db)
        return {"error": str(e)}


async def replace_with_alternative(
    db: AsyncSession,
    params: ReplaceWithAlternativeInput,
    session_id: str,
    sequence_num: int = 0,
) -> Dict[str, Any]:
    """
    Replace a quote item with an alternative product.
    Supports from_product_id and to_product_id parameters.
    """
    await _safe_rollback(db)
    start_time = time.monotonic()

    try:
        # Find the old item
        old_item = None
        old_product_id = None
        
        # Try to find by item_id first
        if params.item_id:
            old_item = await db.get(QuoteItem, params.item_id)
            if old_item:
                old_product_id = old_item.product_id
        
        # If not found by item_id, try by product_id
        if not old_item and hasattr(params, 'from_product_id') and params.from_product_id:
            stmt = select(QuoteItem).where(
                QuoteItem.quote_id == params.quote_id,
                QuoteItem.product_id == params.from_product_id,
                QuoteItem.status == "active"
            ).order_by(QuoteItem.created_at.desc()).limit(1)
            result = await db.execute(stmt)
            old_item = result.scalar_one_or_none()
            if old_item:
                old_product_id = params.from_product_id
        
        if not old_item:
            output = {"error": "Item not found in active quote"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                                 output, ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        if old_item.status != QuoteItemStatus.active:
            output = {"error": "Cannot replace non-active item"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                                 output, ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        old_item_id = old_item.id
        old_quantity = old_item.quantity
        old_product = await db.get(Product, old_product_id)

        # Determine alternative product
        alt_product_id = getattr(params, 'alternative_product_id', None) or getattr(params, 'to_product_id', None)
        
        if not alt_product_id and old_product:
            # First try product's own alternative
            alt_product_id = old_product.alternative_product_id
            
            # If not, search same category with similar price
            if not alt_product_id:
                stmt_alt = select(Product).where(
                    Product.is_active == True,
                    Product.stock > 0,
                    Product.category == old_product.category,
                    Product.id != old_product_id,
                    Product.price_try <= old_product.price_try * 1.2
                ).order_by(Product.price_try.asc()).limit(1)
                result_alt = await db.execute(stmt_alt)
                auto_alt = result_alt.scalar_one_or_none()
                if auto_alt:
                    alt_product_id = auto_alt.id
                    logger.info(f"🔄 Auto-selected alternative: {auto_alt.name}")

        if not alt_product_id:
            output = {"error": "No suitable alternative product found"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                                 output, ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        alt_product = await db.get(Product, alt_product_id)
        if not alt_product or not alt_product.is_active:
            output = {"error": "Alternative product not available"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                                 output, ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        alt_product_price = float(alt_product.price_try)

        # Check max price limit
        max_price = getattr(params, 'max_price_try', None)
        if max_price is not None and alt_product_price > max_price:
            output = {"error": f"Alternative price ({alt_product_price}) exceeds limit ({max_price})"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                                 output, ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        # Stock check
        if alt_product.stock <= 0:
            output = {"error": "Alternative out of stock"}
            duration_ms = int((time.monotonic() - start_time) * 1000)
            await _log_tool_call(db, session_id, "replace_with_alternative", params.model_dump(),
                                 output, ToolCallStatus.error, None, sequence_num, duration_ms)
            await db.commit()
            return output

        # Calculate discount
        quote = await db.get(Quote, params.quote_id)
        customer_id = quote.customer_id if quote else None
        segment = await _get_customer_segment(db, customer_id)
        
        # Get all product IDs in quote for bundle discount
        quote_products_result = await db.execute(
            select(QuoteItem.product_id).where(
                QuoteItem.quote_id == params.quote_id,
                QuoteItem.status == "active"
            )
        )
        quote_products = [p for p in quote_products_result.scalars().all()]
        
        applied_discount = await _get_discount(
            db, alt_product_id, alt_product.category, segment, old_quantity,
            quote_products, alt_product.sku
        )

        # Create new item
        new_item_id = str(uuid.uuid4())
        new_item = QuoteItem(
            id=new_item_id,
            quote_id=params.quote_id,
            product_id=alt_product_id,
            quantity=old_quantity,
            unit_price_try=alt_product_price,
            discount_pct=applied_discount,
            status=QuoteItemStatus.active,
            is_backorder=False,
            source_message_id=getattr(params, 'source_message_id', None),
            idempotency_key=getattr(params, 'idempotency_key', None),
        )
        db.add(new_item)

        # Mark old item as replaced
        old_item.status = QuoteItemStatus.replaced
        old_item.replaced_by_item_id = new_item_id

        # Update stock
        alt_product.stock -= old_quantity

        quote_delta = {
            "action": "item_replaced",
            "old_item_id": old_item_id,
            "new_item_id": new_item_id,
            "old_product_id": old_product_id,
            "new_product_id": alt_product_id,
            "new_product_name": alt_product.name,
            "quantity": old_quantity,
            "old_price": float(old_item.unit_price_try),
            "new_price": alt_product_price,
            "price_difference": round(alt_product_price - float(old_item.unit_price_try), 2),
            "applied_discount_pct": applied_discount,
        }
        
        reason = getattr(params, 'reason', 'user_requested')
        if reason == 'out_of_stock':
            quote_delta["reason"] = "Ürün stokta olmadığı için alternatif sunulmuştur."
        elif reason == 'price_optimization':
            quote_delta["reason"] = "Daha uygun fiyatlı alternatif sunulmuştur."
        
        output = {"success": True, "quote_id": params.quote_id, **quote_delta}

        duration_ms = int((time.monotonic() - start_time) * 1000)
        await _log_tool_call(
            db, session_id, "replace_with_alternative", params.model_dump(), output,
            ToolCallStatus.success, quote_delta, sequence_num, duration_ms,
        )
        await db.commit()
        return output

    except Exception as e:
        logger.error(f"❌ Replace with alternative error: {e}")
        await _safe_rollback(db)
        return {"error": str(e)}

