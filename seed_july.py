# Seed bù đơn đầu tháng 7 (1–20/07/2026) để July thành tháng ĐẦY ĐỦ,
# phục vụ báo cáo theo tháng & quý (Q3 = 7+8+9 trọn vẹn).
# Chạy SAU seed_demo.py + seed_lazada.py.
# docker exec -i odoo odoo shell -d demo --no-http < /Users/bsd/odoo/seed_july.py
import random
from datetime import date, timedelta

random.seed(2028)

Shop = env["kol.shop"]
Acc = env["kol.account"]
Prod = env["kol.product"]
Order = env["kol.order"]

start = date(2026, 7, 1)
end = date(2026, 7, 20)

if Order.search_count([("order_date", ">=", start), ("order_date", "<=", end)]) > 0:
    print("== Đã có đơn 1-20/7, bỏ qua. ==")
else:
    shops = {s.platform: s for s in Shop.search([])}
    accs = {p: Acc.search([("platform", "=", p)]) for p in ("shopee", "tiktok", "lazada")}
    products = list(Prod.search([]))
    if not products:
        raise Exception("Chưa có sản phẩm — chạy seed_demo.py trước.")

    states = (["confirmed"] * 80) + (["partial"] * 7) + (["returned"] * 5) + (["cancelled"] * 8)
    prices = [49000, 89000, 129000, 199000, 259000, 349000, 499000, 690000, 990000, 1290000, 1990000]
    rates = {"shopee": 0.08, "tiktok": 0.10, "lazada": 0.09}
    prefix = {"shopee": "SP", "tiktok": "TT", "lazada": "LZ"}

    seq = 0
    d = start
    while d <= end:
        for platform in ("shopee", "tiktok", "lazada"):
            shop = shops.get(platform)
            acc_list = accs.get(platform)
            if not shop:
                continue
            for _ in range(random.randint(1, 3)):
                seq += 1
                if random.random() < 0.12 or not acc_list:
                    acc = False
                else:
                    acc = random.choice(acc_list)
                state = random.choice(states)
                lines = []
                for _l in range(random.randint(1, 4)):
                    qty = random.randint(1, 5)
                    qret = random.randint(1, qty) if state == "partial" else 0
                    lines.append((0, 0, {
                        "product_id": random.choice(products).id,
                        "qty": qty,
                        "qty_returned": qret,
                        "unit_price": random.choice(prices),
                    }))
                Order.create({
                    "name": "%sJ%05d" % (prefix[platform], seq),
                    "platform": platform,
                    "shop_id": shop.id,
                    "order_date": d,
                    "state": state,
                    "kol_account_id": acc.id if acc else False,
                    "commission_rate": rates[platform],
                    "line_ids": lines,
                })
        d += timedelta(days=1)

    env.cr.commit()
    print("== Bù tháng 7 xong:",
          Order.search_count([("order_date", ">=", start), ("order_date", "<=", end)]),
          "đơn (1-20/7); tổng:", Order.search_count([]), "==")
