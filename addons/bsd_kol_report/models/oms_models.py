"""Lớp OMS: xác nhận đơn từ sàn → tạo sale.order của Odoo để lên kế hoạch giao hàng.

Đây là bước demo→sản phẩm theo §2 ROADMAP: đơn sàn (kol.order, chỉ để báo cáo)
được 'chuyển' thành sale.order thật; lớp KOL/chiến dịch gắn lên sale.order.
"""

from odoo import api, fields, models

from .kol_models import PLATFORMS


class SaleOrder(models.Model):
    """Gắn lớp sàn/KOL/chiến dịch lên đơn bán của Odoo."""

    _inherit = "sale.order"

    marketplace_platform = fields.Selection(PLATFORMS, string="Sàn TMĐT", index=True)
    marketplace_shop_id = fields.Many2one("kol.shop", string="Shop sàn")
    marketplace_order_ref = fields.Char(string="Mã đơn trên sàn", index=True)
    kol_account_id = fields.Many2one("kol.account", string="Tài khoản KOL")
    kol_influencer_id = fields.Many2one(
        "kol.influencer",
        string="KOL",
        related="kol_account_id.influencer_id",
        store=True,
        readonly=True,
    )
    kol_campaign_id = fields.Many2one("kol.campaign", string="Chiến dịch")
    kol_order_id = fields.Many2one(
        "kol.order", string="Đơn sàn nguồn", index=True, copy=False
    )


class DeliveryCarrier(models.Model):
    """Gắn nhãn sàn cho nhà cung cấp vận chuyển (ĐVVC của sàn vs 3PL dùng chung)."""

    _inherit = "delivery.carrier"

    marketplace_platform = fields.Selection(
        PLATFORMS,
        string="Sàn áp dụng",
        help="ĐVVC riêng của sàn (để trống = 3PL dùng chung mọi sàn).",
    )


OMS_STATES = [
    ("received", "Mới nhận từ sàn"),
    ("confirmed", "Đã tạo đơn Odoo"),
]


class KolOrder(models.Model):
    """Bổ sung luồng OMS cho đơn sàn: xác nhận → sale.order."""

    _inherit = "kol.order"

    oms_state = fields.Selection(
        OMS_STATES, string="Xử lý đơn", default="received", required=True, copy=False
    )
    sale_order_id = fields.Many2one(
        "sale.order", string="Đơn Odoo", readonly=True, copy=False
    )
    partner_id = fields.Many2one(
        "res.partner", string="Khách hàng", readonly=True, copy=False
    )
    picking_count = fields.Integer(
        string="Số phiếu giao", compute="_compute_picking_count"
    )

    @api.depends("sale_order_id.picking_ids")
    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = len(rec.sale_order_id.picking_ids)

    # ---- helpers (master data demo) -------------------------------------
    def _mp_partner(self):
        """Khách đại diện cho mỗi sàn (demo: 1 partner/sàn — xem §2.4 ROADMAP)."""
        self.ensure_one()
        label = dict(PLATFORMS).get(self.platform) or (self.platform or "")
        name = "Khách %s" % label
        Partner = self.env["res.partner"].sudo()
        partner = Partner.search(
            [("name", "=", name), ("is_company", "=", True)], limit=1
        )
        if not partner:
            partner = Partner.create(
                {"name": name, "is_company": True, "customer_rank": 1}
            )
        return partner

    def _mp_product(self, kol_product):
        """Tìm/khởi tạo product.product (hàng lưu kho) từ sản phẩm sàn."""
        Product = self.env["product.product"].sudo()
        if kol_product.sku:
            domain = [("default_code", "=", kol_product.sku)]
        else:
            domain = [("name", "=", kol_product.name)]
        product = Product.search(domain, limit=1)
        if not product:
            product = Product.create(
                {
                    "name": kol_product.name,
                    "default_code": kol_product.sku or False,
                    "type": "consu",
                    "is_storable": True,
                    "list_price": 0.0,
                }
            )
        return product

    def _mp_carrier(self):
        """ĐVVC theo sàn (SPX / TikTok Logistics / LEX...)."""
        self.ensure_one()
        return (
            self.env["delivery.carrier"]
            .sudo()
            .search([("marketplace_platform", "=", self.platform)], limit=1)
        )

    def _notify(self, title, message, kind="warning"):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": kind,
                "sticky": False,
            },
        }

    # ---- actions --------------------------------------------------------
    def action_confirm_to_sale(self):
        """Xác nhận đơn sàn và tạo sale.order (đã xác nhận → sinh phiếu giao)."""
        self.ensure_one()
        if self.sale_order_id:
            return self.action_view_sale_order()
        if self.state in ("cancelled", "returned"):
            return self._notify(
                "Không tạo được đơn giao",
                "Đơn đã huỷ / hoàn toàn bộ nên không chuyển sang giao hàng.",
            )
        if not self.line_ids:
            return self._notify("Thiếu dòng hàng", "Đơn chưa có dòng sản phẩm.")

        partner = self._mp_partner()
        carrier = self._mp_carrier()
        order_lines = []
        for line in self.line_ids:
            product = self._mp_product(line.product_id)
            order_lines.append(
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom_qty": line.qty,
                        "price_unit": line.unit_price,
                    },
                )
            )

        vals = {
            "partner_id": partner.id,
            "origin": self.name,
            "date_order": fields.Datetime.to_datetime(self.order_date),
            "marketplace_platform": self.platform,
            "marketplace_shop_id": self.shop_id.id,
            "marketplace_order_ref": self.name,
            "kol_account_id": self.kol_account_id.id,
            "kol_campaign_id": self.campaign_id.id,
            "kol_order_id": self.id,
            "order_line": order_lines,
        }
        if carrier:
            vals["carrier_id"] = carrier.id
        so = self.env["sale.order"].create(vals)
        # Bảo đảm đơn giá giữ đúng giá sàn (tránh pricelist ghi đè về 0)
        for so_line, src in zip(so.order_line, self.line_ids):
            if so_line.price_unit != src.unit_price:
                so_line.price_unit = src.unit_price
        so.action_confirm()  # sinh phiếu giao (delivery) qua sale_stock
        if carrier and so.picking_ids:
            so.picking_ids.write({"carrier_id": carrier.id})
        self.write(
            {
                "sale_order_id": so.id,
                "partner_id": partner.id,
                "oms_state": "confirmed",
            }
        )
        return self.action_view_sale_order()

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Đơn Odoo",
            "res_model": "sale.order",
            "res_id": self.sale_order_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_view_pickings(self):
        self.ensure_one()
        pickings = self.sale_order_id.picking_ids
        action = {
            "type": "ir.actions.act_window",
            "name": "Phiếu giao",
            "res_model": "stock.picking",
            "domain": [("id", "in", pickings.ids)],
            "view_mode": "list,form",
        }
        if len(pickings) == 1:
            action.update(view_mode="form", res_id=pickings.id)
        return action
