# -*- coding: utf-8 -*-
"""Seed tồn kho cho sản phẩm demo (idempotent).
- Tạo trước product.product cho mọi kol.product (consu + is_storable), khớp logic _mp_product.
- Đặt tồn on-hand = TARGET tại WH/Stock để phiếu giao reserve được → Check Availability/Validate chạy.
Chạy: docker exec -i odoo odoo shell -d demo --no-http < /Users/bsd/odoo/seed_stock.py
"""
TARGET = 100000.0
loc = env.ref("stock.stock_location_stock")
Product = env["product.product"]
Quant = env["stock.quant"].with_context(inventory_mode=True)

created = 0
seeded = 0
for kp in env["kol.product"].search([]):
    domain = [("default_code", "=", kp.sku)] if kp.sku else [("name", "=", kp.name)]
    product = Product.search(domain, limit=1)
    if not product:
        product = Product.create(
            {
                "name": kp.name,
                "default_code": kp.sku or False,
                "type": "consu",
                "is_storable": True,
                "list_price": 0.0,
            }
        )
        created += 1
    quant = Quant.search(
        [("product_id", "=", product.id), ("location_id", "=", loc.id)], limit=1
    )
    if quant:
        quant.inventory_quantity = TARGET
        quant.action_apply_inventory()
    else:
        Quant.create(
            {
                "product_id": product.id,
                "location_id": loc.id,
                "inventory_quantity": TARGET,
            }
        ).action_apply_inventory()
    seeded += 1

env.cr.commit()
print("STOCK_SEED created_products=%d seeded=%d target=%s" % (created, seeded, TARGET))
sample = Product.search([("type", "=", "consu")], limit=1)
print("sample:", sample.display_name, "on-hand=", sample.qty_available)
