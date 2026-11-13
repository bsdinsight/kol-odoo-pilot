# Seed dữ liệu MẪU cho demo báo cáo KOL (Shopee + TikTok Shop).
# Chạy: docker exec -i odoo odoo shell -d demo --no-http < /Users/bsd/odoo/seed_demo.py
# Idempotent: đã có đơn thì bỏ qua.
import random
from datetime import date, datetime, timedelta

random.seed(2026)

Shop = env["kol.shop"]
Inf = env["kol.influencer"]
Acc = env["kol.account"]
Prod = env["kol.product"]
Order = env["kol.order"]
Sync = env["kol.sync.status"]

# --- tài khoản đăng nhập demo ---
admin = env.ref("base.user_admin")
admin.write({"password": "admin"})
ugf = "group_ids" if "group_ids" in env["res.users"]._fields else "groups_id"
if not env["res.users"].search([("login", "=", "viewer")]):
    env["res.users"].create({
        "name": "Người xem demo",
        "login": "viewer",
        "password": "viewer",
        ugf: [(6, 0, [env.ref("base.group_user").id])],
    })

# --- cấu hình kết nối nguồn (idempotent, chạy mỗi lần) ---
Conn = env["kol.connection"]
_shp = Shop.search([("platform", "=", "shopee")], limit=1)
_tkt = Shop.search([("platform", "=", "tiktok")], limit=1)
if _shp and not Conn.search([("platform", "=", "shopee")]):
    Conn.create({"platform": "shopee", "shop_id": _shp.id, "source_type": "api",
                 "mode": "sample", "state": "draft", "history_days": 90,
                 "base_url": "https://partner.shopeemobile.com"})
if _tkt and not Conn.search([("platform", "=", "tiktok")]):
    Conn.create({"platform": "tiktok", "shop_id": _tkt.id, "source_type": "api",
                 "mode": "sample", "state": "draft", "history_days": 90,
                 "base_url": "https://open-api.tiktokglobalshop.com"})
_laz = Shop.search([("platform", "=", "lazada")], limit=1)
if not _laz:
    _laz = Shop.create({"name": "BSD Official Store (Lazada)", "platform": "lazada"})
if not Conn.search([("platform", "=", "lazada")]):
    Conn.create({"platform": "lazada", "shop_id": _laz.id, "source_type": "api",
                 "mode": "sample", "state": "draft", "history_days": 90,
                 "base_url": "https://api.lazada.vn/rest"})
env.cr.commit()

# --- chiến dịch mẫu (idempotent) để minh hoạ "đẩy lên sàn" ---
Campaign = env["kol.campaign"]
if Campaign.search_count([]) == 0:
    _shp = Shop.search([("platform", "=", "shopee")], limit=1)
    _tkt = Shop.search([("platform", "=", "tiktok")], limit=1)
    _prods = Prod.search([], limit=6)
    _tkt_accs = Acc.search([("platform", "=", "tiktok")], limit=3)
    if _prods:
        Campaign.create({"name": "Mở hoa hồng TikTok Q4", "campaign_type": "affiliate_open",
                         "platform": "tiktok", "shop_id": _tkt.id if _tkt else False,
                         "commission_rate": 12.0, "product_ids": [(6, 0, _prods.ids)]})
        Campaign.create({"name": "Mời KOL TikTok ra mắt SP", "campaign_type": "affiliate_target",
                         "platform": "tiktok", "shop_id": _tkt.id if _tkt else False,
                         "commission_rate": 18.0, "product_ids": [(6, 0, _prods.ids[:3])],
                         "kol_account_ids": [(6, 0, _tkt_accs.ids)]})
        Campaign.create({"name": "Flash Sale Shopee cuối tuần", "campaign_type": "promo_discount",
                         "platform": "shopee", "shop_id": _shp.id if _shp else False,
                         "discount_percent": 25.0, "product_ids": [(6, 0, _prods.ids)]})
        Campaign.create({"name": "AMS Shopee mở hoa hồng", "campaign_type": "affiliate_open",
                         "platform": "shopee", "shop_id": _shp.id if _shp else False,
                         "commission_rate": 8.0, "product_ids": [(6, 0, _prods.ids[:4])]})
        env.cr.commit()
        print("== Seed chiến dịch:", Campaign.search_count([]), "==")

if Order.search_count([]) > 0:
    print("== Đã có dữ liệu, bỏ qua seed. ==")
else:
    shop_shopee = Shop.create({"name": "BSD Official Store (Shopee)", "platform": "shopee"})
    shop_tiktok = Shop.create({"name": "BSD Official Shop (TikTok)", "platform": "tiktok"})

    # KOL + tài khoản sàn; vài KOL có mặt ở CẢ hai sàn (để demo ghép danh tính chéo sàn)
    inf_defs = [
        ("Mai Chi", [("shopee", "@maichi.review"), ("tiktok", "@maichi.official")]),
        ("Hoàng Nam", [("shopee", "@namhoang.deals"), ("tiktok", "@namhoang")]),
        ("Thu Trang", [("tiktok", "@trang.beauty"), ("shopee", "@trangbeauty.sp")]),
        ("Gia Hân", [("shopee", "@giahan.pick"), ("tiktok", "@giahan")]),
        ("Quốc Bảo", [("tiktok", "@baoquoc.tech")]),
        ("Linh Đan", [("shopee", "@linhdan.home")]),
        ("Phương Vy", [("tiktok", "@vyphuong.daily")]),
        ("Đức Anh", [("shopee", "@ducanh.store")]),
        ("Khánh Huyền", [("tiktok", "@huyenkhanh.style")]),
        ("Tuấn Kiệt", [("tiktok", "@kiettuan.gadget")]),
    ]
    acc_by_platform = {"shopee": [], "tiktok": []}
    for name, accs in inf_defs:
        inf = Inf.create({"name": name})
        for plat, handle in accs:
            a = Acc.create({"influencer_id": inf.id, "platform": plat, "handle": handle})
            acc_by_platform[plat].append(a)

    cats = ["Mỹ phẩm", "Thời trang", "Gia dụng", "Điện tử", "Thực phẩm", "Mẹ & Bé"]
    products = []
    for i in range(60):
        cat = random.choice(cats)
        products.append(Prod.create({
            "name": "%s mẫu %02d" % (cat, i + 1),
            "sku": "SKU%04d" % (i + 1),
            "category": cat,
        }))

    # phân phối trạng thái: 80% hoàn tất, 7% hoàn một phần, 5% hoàn toàn bộ, 8% huỷ
    states = (["confirmed"] * 80) + (["partial"] * 7) + (["returned"] * 5) + (["cancelled"] * 8)
    prices = [49000, 89000, 129000, 199000, 259000, 349000, 499000, 690000, 990000, 1290000, 1990000]

    today = date.today()
    seq = 0
    for d in range(90):
        day = today - timedelta(days=d)
        for _ in range(random.randint(3, 8)):
            seq += 1
            platform = random.choice(["shopee", "tiktok"])
            shop = shop_shopee if platform == "shopee" else shop_tiktok
            # ~12% đơn CHƯA gắn được KOL -> để bucket riêng, không gán bừa
            if random.random() < 0.12:
                acc = False
            else:
                acc = random.choice(acc_by_platform[platform])
            state = random.choice(states)
            rate = 0.08 if platform == "shopee" else 0.10
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
            code = ("SP" if platform == "shopee" else "TT") + "%06d" % seq
            Order.create({
                "name": code,
                "platform": platform,
                "shop_id": shop.id,
                "order_date": day,
                "state": state,
                "kol_account_id": acc.id if acc else False,
                "commission_rate": rate,
                "line_ids": lines,
            })

    now = datetime.now()
    Sync.create({"platform": "shopee", "shop_id": shop_shopee.id,
                 "last_success": now - timedelta(hours=2), "state": "ok",
                 "message": "Đồng bộ đơn + hoa hồng OK"})
    Sync.create({"platform": "tiktok", "shop_id": shop_tiktok.id,
                 "last_success": now - timedelta(hours=30), "state": "stale",
                 "message": "Chờ cấp lại quyền Affiliate API — dữ liệu dừng ở T-30h"})

    env.cr.commit()
    print("== Seed xong:", Order.search_count([]), "đơn,",
          Acc.search_count([]), "tài khoản KOL,",
          Prod.search_count([]), "sản phẩm ==")
