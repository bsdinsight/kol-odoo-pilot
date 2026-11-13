# Gắn đơn hàng mẫu vào các chiến dịch (để báo cáo lọc theo campaign).
# Chạy SAU seed_demo.py (đã có campaign + đơn).
# docker exec -i odoo odoo shell -d demo --no-http < /Users/bsd/odoo/seed_campaign_orders.py
import random

random.seed(2029)

Order = env["kol.order"]
Campaign = env["kol.campaign"]

if Order.search_count([("campaign_id", "!=", False)]) > 0:
    print("== Đơn đã gắn chiến dịch, bỏ qua. ==")
else:
    # ưu tiên gắn campaign 'mời KOL cụ thể' trước, rồi 'mở hoa hồng', rồi khuyến mãi
    pri = {"affiliate_target": 0, "affiliate_open": 1, "promo_discount": 2, "promo_voucher": 3}
    camps = Campaign.search([]).sorted(lambda c: pri.get(c.campaign_type, 9))
    total = 0
    for camp in camps:
        dom = [("platform", "=", camp.platform), ("campaign_id", "=", False)]
        if camp.campaign_type in ("affiliate_open", "affiliate_target"):
            dom.append(("kol_account_id", "!=", False))
        if camp.campaign_type == "affiliate_target" and camp.kol_account_ids:
            dom.append(("kol_account_id", "in", camp.kol_account_ids.ids))
        cands = Order.search(dom)
        if not cands:
            continue
        n = min(len(cands), random.randint(40, 80))
        picks = random.sample(cands.ids, n)
        Order.browse(picks).write({"campaign_id": camp.id})
        total += n
        print("  -", camp.name, "->", n, "đơn")
    env.cr.commit()
    print("== Gắn tổng", total, "đơn vào", len(camps), "chiến dịch ==")
