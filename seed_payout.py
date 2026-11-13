# -*- coding: utf-8 -*-
"""Seed đối soát payout sàn (kol.payout + lines) — kỳ bán nguyệt T7–T10/2026.
Mỗi kỳ gom đơn thật của sàn, tính 4 phí (hoa hồng/thanh toán/vận chuyển/voucher),
payout_declared = đáng nhận (khớp) trừ vài kỳ cố ý lệch để minh hoạ đối soát.
Idempotent: xoá kol.payout cũ (cascade lines) rồi tạo lại.
Chạy: docker exec -i odoo odoo shell -d demo --no-http < /Users/bsd/odoo/seed_payout.py
"""
import calendar
import random
from datetime import date

random.seed(7001)

Payout = env["kol.payout"]
Order = env["kol.order"]
Shop = env["kol.shop"]

RATES = {
    "shopee": {"commission": 0.055, "payment": 0.04},
    "tiktok": {"commission": 0.060, "payment": 0.05},
    "lazada": {"commission": 0.040, "payment": 0.02},
}
PLAT_LABEL = {"shopee": "Shopee", "tiktok": "TikTok Shop", "lazada": "Lazada"}
YEAR = 2026
MONTHS = [7, 8, 9, 10]

Payout.search([]).unlink()

made = 0
mism = 0
for p in ["shopee", "tiktok", "lazada"]:
    shop = Shop.search([("platform", "=", p)], limit=1)
    rate = RATES[p]
    for mm in MONTHS:
        last = calendar.monthrange(YEAR, mm)[1]
        for (d1, d2) in [(1, 15), (16, last)]:
            start = date(YEAR, mm, d1)
            end = date(YEAR, mm, d2)
            orders = Order.search([
                ("platform", "=", p),
                ("order_date", ">=", start),
                ("order_date", "<=", end),
                ("amount_net", ">", 0),
            ])
            if not orders:
                continue
            lines = []
            for o in orders:
                net = o.amount_net
                commission = round(net * rate["commission"])
                payment = round(net * rate["payment"])
                shipping = random.choice([0, 0, 0, 0, 15000, 16500, 18000])
                voucher = round(net * 0.05) if random.random() < 0.25 else 0
                lines.append((0, 0, {
                    "order_id": o.id,
                    "gross": net,
                    "fee_commission": commission,
                    "fee_payment": payment,
                    "fee_shipping": shipping,
                    "fee_voucher": voucher,
                }))
            rec = Payout.create({
                "name": "%s · Kỳ %02d–%02d/%02d/%d" % (PLAT_LABEL[p], d1, d2, mm, YEAR),
                "platform": p,
                "shop_id": shop.id if shop else False,
                "statement_ref": "STM-%s-%d%02d%02d" % (p[:3].upper(), YEAR, mm, d1),
                "period_start": start,
                "period_end": end,
                "line_ids": lines,
                "state": "paid" if end < date(YEAR, 9, 1) else "draft",
            })
            exp = rec.payout_expected
            if random.random() < 0.18:
                rec.payout_declared = exp - round(exp * random.uniform(0.002, 0.006))
                mism += 1
            else:
                rec.payout_declared = exp
            made += 1

env.cr.commit()
print("PAYOUT_SEED statements=%d mismatched=%d" % (made, mism))
