# Seed thêm đơn MẪU cho Lazada (chạy SAU seed_demo.py; không đụng dữ liệu Shopee/TikTok).
# Chạy: docker exec -i odoo odoo shell -d demo --no-http < /Users/bsd/odoo/seed_lazada.py
# Idempotent: đã có đơn Lazada thì bỏ qua.
import random
from datetime import date, datetime, timedelta

random.seed(2027)

Shop = env["kol.shop"]
Inf = env["kol.influencer"]
Acc = env["kol.account"]
Prod = env["kol.product"]
Order = env["kol.order"]
Sync = env["kol.sync.status"]

if Order.search_count([("platform", "=", "lazada")]) > 0:
    print("== Đã có đơn Lazada, bỏ qua. ==")
else:
    shop_laz = Shop.search([("platform", "=", "lazada")], limit=1)
    if not shop_laz:
        shop_laz = Shop.create({"name": "BSD Official Store (Lazada)", "platform": "lazada"})

    # Tài khoản Lazada cho một số KOL đã có -> nhiều KOL phủ cả 3 sàn (câu chuyện ghép danh tính)
    laz_defs = [
        ("Mai Chi", "@maichi.laz"),
        ("Gia Hân", "@giahan.laz"),
        ("Hoàng Nam", "@namhoang.laz"),
        ("Thu Trang", "@trang.laz"),
        ("Linh Đan", "@linhdan.laz"),
    ]
    laz_accounts = []
    for name, handle in laz_defs:
        inf = Inf.search([("name", "=", name)], limit=1)
        if not inf:
            inf = Inf.create({"name": name})
        acc = Acc.search([("platform", "=", "lazada"), ("handle", "=", handle)], limit=1)
        if not acc:
            acc = Acc.create({"influencer_id": inf.id, "platform": "lazada", "handle": handle})
        laz_accounts.append(acc)

    products = list(Prod.search([]))
    if not products:
        raise Exception("Chưa có sản phẩm — hãy chạy seed_demo.py trước.")

    states = (["confirmed"] * 80) + (["partial"] * 7) + (["returned"] * 5) + (["cancelled"] * 8)
    prices = [49000, 89000, 129000, 199000, 259000, 349000, 499000, 690000, 990000, 1290000, 1990000]

    today = date.today()
    seq = 0
    for d in range(90):
        day = today - timedelta(days=d)
        for _ in range(random.randint(2, 4)):
            seq += 1
            acc = False if random.random() < 0.12 else random.choice(laz_accounts)
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
                "name": "LZ%06d" % seq,
                "platform": "lazada",
                "shop_id": shop_laz.id,
                "order_date": day,
                "state": state,
                "kol_account_id": acc.id if acc else False,
                "commission_rate": 0.09,
                "line_ids": lines,
            })

    if not Sync.search([("platform", "=", "lazada")]):
        Sync.create({"platform": "lazada", "shop_id": shop_laz.id,
                     "last_success": datetime.now() - timedelta(hours=5),
                     "state": "ok", "message": "Đồng bộ đơn Lazada OK"})

    env.cr.commit()
    print("== Lazada xong:", Order.search_count([("platform", "=", "lazada")]), "đơn Lazada;",
          "tổng tất cả:", Order.search_count([]), "đơn ==")
