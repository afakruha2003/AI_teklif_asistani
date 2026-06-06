from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Product, KnowledgeEntry, Customer, Quote, QuoteItem, PriceRule,
    QuoteItemStatus, QuoteStatus, CustomerSegment,
)

logger = logging.getLogger(__name__)

SEED_DIR = Path(__file__).parent.parent.parent / "seed_data"


def _load_json(filename: str) -> List[Dict[str, Any]]:

    path = SEED_DIR / filename
    if not path.exists():
        logger.warning(f"Seed source resource '{filename}' not found. Skipping entry insertion.")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


async def seed_database(db: AsyncSession) -> None:

    logger.info("Initiating system data seeding pipeline...")

    # --- 1. Products Processing ---
    products_data = _load_json("products.json")
    if products_data:
        p_ids = [p["product_id"] for p in products_data]
        existing_p_stmt = await db.execute(select(Product.id).where(Product.id.in_(p_ids)))
        existing_p_ids: Set[str] = set(existing_p_stmt.scalars().all())

        new_products = []
        for p in products_data:
            if p["product_id"] not in existing_p_ids:
                # Parse aliases - handle nested {"tr": [...]} format
                aliases = p.get("aliases", [])
                if isinstance(aliases, dict):
                    aliases = aliases.get("tr", [])
                elif not isinstance(aliases, list):
                    aliases = []
                
                new_products.append(Product(
                    id=p["product_id"],
                    name=p.get("name_tr", p.get("name", "")),
                    description=p.get("description"),
                    category=p.get("category", ""),
                    price_try=float(p.get("price_try", 0)),
                    stock=int(p.get("stock_qty", p.get("stock", 0))),
                    sku=p.get("sku"),
                    aliases=aliases,
                    tags=p.get("tags", []),
                    is_active=p.get("active", p.get("is_active", True)),
                    alternative_product_id=p.get("alternative_product_id"),
                ))
        if new_products:
            db.add_all(new_products)
            await db.commit()
        logger.info(f"Products baseline aligned. Records inspected: {len(products_data)}, Inserted: {len(new_products)}")

    # --- 2. Knowledge Entries Processing ---
    knowledge_data = _load_json("knowledge_entries.json")
    if knowledge_data:
        k_ids = [k["knowledge_id"] for k in knowledge_data]
        existing_k_stmt = await db.execute(select(KnowledgeEntry.id).where(KnowledgeEntry.id.in_(k_ids)))
        existing_k_ids: Set[str] = set(existing_k_stmt.scalars().all())

        new_entries = []
        for k in knowledge_data:
            if k["knowledge_id"] not in existing_k_ids:
                new_entries.append(KnowledgeEntry(
                    id=k["knowledge_id"],
                    title=k.get("title", ""),
                    content=k.get("content", ""),
                    category=k.get("category", "general"),
                    tags=k.get("tags", []),
                    is_active=k.get("is_active", True),
                ))
        if new_entries:
            db.add_all(new_entries)
            await db.commit()
        logger.info(f"Knowledge documentation baseline aligned. Records inspected: {len(knowledge_data)}, Inserted: {len(new_entries)}")

    # --- 3. Customers Processing ---
    customers_data = _load_json("customers.json")
    if customers_data:
        c_ids = [c["customer_id"] for c in customers_data]
        existing_c_stmt = await db.execute(select(Customer.id).where(Customer.id.in_(c_ids)))
        existing_c_ids: Set[str] = set(existing_c_stmt.scalars().all())

        new_customers = []
        for c in customers_data:
            if c["customer_id"] not in existing_c_ids:
                # Map JSON segment values to CustomerSegment enum
                segment_raw = c.get("segment", "standard")
                segment_mapping = {
                    "retail": "standard",
                    "wholesale": "partner",
                    "food_retail": "standard",
                    "standard": "standard",
                    "partner": "partner",
                    "enterprise": "enterprise",
                }
                segment_value = segment_mapping.get(segment_raw, "standard")
                segment_enum = CustomerSegment[segment_value]
                
                # Map JSON price_tier to price_level
                price_level = c.get("price_tier", c.get("price_level", "standard"))
                
                new_customers.append(Customer(
                    id=c["customer_id"],
                    name=c.get("name", ""),
                    email=c.get("email"),
                    segment=segment_enum,
                    allow_backorder=c.get("allow_backorder", False),
                    price_level=price_level,
                ))
        if new_customers:
            db.add_all(new_customers)
            await db.commit()
        logger.info(f"Customer profiles aligned. Records inspected: {len(customers_data)}, Inserted: {len(new_customers)}")

    # --- 4. Price Rules Processing ---
    price_rules_data = _load_json("price_rules.json")
    if price_rules_data:
        pr_ids = [pr["rule_id"] for pr in price_rules_data]
        existing_pr_stmt = await db.execute(select(PriceRule.id).where(PriceRule.id.in_(pr_ids)))
        existing_pr_ids: Set[str] = set(existing_pr_stmt.scalars().all())

        new_rules = []
        for pr in price_rules_data:
            if pr["rule_id"] not in existing_pr_ids:
                new_rules.append(PriceRule(
                    id=pr["rule_id"],
                    name=pr.get("name", ""),
                    segment=pr.get("segment"),
                    category=pr.get("category"),
                    product_id=pr.get("product_id"),
                    min_quantity=pr.get("min_quantity", 1),
                    discount_pct=float(pr.get("discount_pct", 0)),
                    is_active=pr.get("is_active", True),
                ))
        if new_rules:
            db.add_all(new_rules)
            await db.commit()
        logger.info(f"B2B pricing matrix aligned. Records inspected: {len(price_rules_data)}, Inserted: {len(new_rules)}")

    # --- 5. Quotes Processing ---
    quotes_data = _load_json("quotes.json")
    if quotes_data:
        q_ids = [q["quote_id"] for q in quotes_data]
        existing_q_stmt = await db.execute(select(Quote.id).where(Quote.id.in_(q_ids)))
        existing_q_ids: Set[str] = set(existing_q_stmt.scalars().all())

        new_quotes = []
        for q in quotes_data:
            if q["quote_id"] not in existing_q_ids:
                status_raw = q.get("status", "draft")
                status_enum = QuoteStatus[status_raw] if hasattr(QuoteStatus, status_raw) else QuoteStatus.draft

                new_quotes.append(Quote(
                    id=q["quote_id"],
                    customer_id=q.get("customer_id"),
                    status=status_enum,
                    notes=q.get("notes"),
                ))
        if new_quotes:
            db.add_all(new_quotes)
            await db.commit()
        logger.info(f"Quote documents aligned. Records inspected: {len(quotes_data)}, Inserted: {len(new_quotes)}")

    # --- 6. Quote Items Processing ---
    quote_items_data = _load_json("quote_items.json")
    if quote_items_data:
        qi_ids = [qi["quote_item_id"] for qi in quote_items_data]
        existing_qi_stmt = await db.execute(select(QuoteItem.id).where(QuoteItem.id.in_(qi_ids)))
        existing_qi_ids: Set[str] = set(existing_qi_stmt.scalars().all())

        new_items = []
        for qi in quote_items_data:
            if qi["quote_item_id"] not in existing_qi_ids:
                item_status_raw = qi.get("status", "active")
                item_status_enum = QuoteItemStatus[item_status_raw] if hasattr(QuoteItemStatus, item_status_raw) else QuoteItemStatus.active

                new_items.append(QuoteItem(
                    id=qi["quote_item_id"],
                    quote_id=qi["quote_id"],
                    product_id=qi["product_id"],
                    quantity=int(qi.get("quantity", 1)),
                    unit_price_try=float(qi.get("unit_price_try", 0)),
                    discount_pct=float(qi.get("discount_pct", 0)),
                    status=item_status_enum,
                    is_backorder=qi.get("is_backorder", False),
                ))
        if new_items:
            db.add_all(new_items)
            await db.commit()
        logger.info(f"Quote items aligned. Records inspected: {len(quote_items_data)}, Inserted: {len(new_items)}")

    logger.info("Database seeding lifecycle finalized successfully.")
