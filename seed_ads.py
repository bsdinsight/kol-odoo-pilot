# -*- coding: utf-8 -*-
"""Seed dữ liệu quảng cáo (kol.ad) T7–T10/2026, 3 sàn — ROAS ~ 1.8–6x.
Idempotent: xoá kol.ad cũ rồi tạo lại.
Chạy: docker exec -i odoo odoo shell -d demo --no-http < /Users/bsd/odoo/seed_ads.py
"""
import random
from datetime import date

random.seed(5050)

Ad = env["kol.ad"]
Shop = env["kol.shop"]
products = env["kol.product"].search([])

PLATS = ["shopee", "tiktok", "lazada"]
PLAT_LABEL = {"shopee": "Shopee Ads", "tiktok": "TikTok Ads", "lazada": "Lazada Sponsored"}
# Loại QC đặc trưng theo sàn
AD_TYPES_BY_PLAT = {
    "shopee": ["search", "display", "shop"],
    "tiktok": ["video", "live", "display"],
    "lazada": ["search", "display", "shop"],
}
TYPE_LABEL = {
    "search": "Search", "display": "Khám phá", "video": "Video Shopping",
    "live": "LIVE", "shop": "Shop Ads",
}
MONTHS = [(2026, 7), (2026, 8), (2026, 9), (2026, 10)]

# dọn cũ
Ad.search([]).unlink()

rows = []
for p in PLATS:
    shop = Shop.search([("platform", "=", p)], limit=1)
    for (yy, mm) in MONTHS:
        for at in AD_TYPES_BY_PLAT[p]:
            # 1–3 dòng mỗi (sàn, tháng, loại) gắn sản phẩm ngẫu nhiên
            for _ in range(random.randint(1, 3)):
                prod = random.choice(products)
                d = date(yy, mm, random.randint(1, 27))
                cost = random.randint(2, 30) * 1_000_000          # 2–30 triệu
                roas = random.uniform(1.8, 6.0)
                revenue = int(cost * roas)
                impressions = random.randint(50_000, 900_000)
                clicks = int(impressions * random.uniform(0.008, 0.03))
                orders = max(1, int(clicks * random.uniform(0.02, 0.08)))
                rows.append({
                    "name": "%s · %s · T%02d" % (PLAT_LABEL[p], TYPE_LABEL[at], mm),
                    "platform": p,
                    "shop_id": shop.id if shop else False,
                    "ad_type": at,
                    "product_id": prod.id,
                    "date": d,
                    "cost": cost,
                    "revenue": revenue,
                    "impressions": impressions,
                    "clicks": clicks,
                    "orders": orders,
                })

recs = Ad.create(rows)
env.cr.commit()
tot_cost = sum(recs.mapped("cost"))
tot_rev = sum(recs.mapped("revenue"))
print("ADS_SEED rows=%d cost=%s revenue=%s ROAS=%.2f" % (
    len(recs), tot_cost, tot_rev, (tot_rev / tot_cost) if tot_cost else 0))
