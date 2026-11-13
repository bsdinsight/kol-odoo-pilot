"""Quảng cáo trả phí trên sàn (Ads) + ROAS — demo dữ liệu mẫu.

Bổ sung luồng dữ liệu thứ 3 (Orders · KOL/Affiliate · **Ads**): đo chi phí
quảng cáo, doanh thu từ quảng cáo và ROAS theo sàn / sản phẩm / loại QC.
"""

from odoo import api, fields, models

from .kol_models import PLATFORMS

AD_TYPES = [
    ("search", "Search Ads (tìm kiếm)"),
    ("display", "Display / Khám phá"),
    ("video", "Video Shopping Ads"),
    ("live", "LIVE Ads"),
    ("shop", "Shop / Brand Ads"),
]


class KolAd(models.Model):
    _name = "kol.ad"
    _description = "Quảng cáo trả phí trên sàn (Ads)"
    _order = "date desc, platform"

    name = fields.Char(string="Chiến dịch QC", required=True)
    platform = fields.Selection(PLATFORMS, string="Nền tảng", required=True)
    shop_id = fields.Many2one("kol.shop", string="Shop")
    ad_type = fields.Selection(AD_TYPES, string="Loại quảng cáo", required=True, default="search")
    product_id = fields.Many2one("kol.product", string="Sản phẩm")
    date = fields.Date(string="Ngày", required=True, index=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.ref("base.VND")
    )

    cost = fields.Monetary(string="Chi phí QC")
    revenue = fields.Monetary(string="Doanh thu từ QC")
    impressions = fields.Integer(string="Hiển thị")
    clicks = fields.Integer(string="Lượt nhấp")
    orders = fields.Integer(string="Đơn từ QC")

    roas = fields.Float(
        string="ROAS", compute="_compute_kpis", store=True,
        help="Return On Ad Spend = Doanh thu QC / Chi phí QC (lần).",
    )
    acos = fields.Float(
        string="ACoS (%)", compute="_compute_kpis", store=True,
        help="Advertising Cost of Sales = Chi phí / Doanh thu.",
    )
    ctr = fields.Float(string="CTR (%)", compute="_compute_kpis", store=True)
    cpc = fields.Monetary(string="CPC", compute="_compute_kpis", store=True)
    cvr = fields.Float(string="Tỷ lệ chuyển đổi (%)", compute="_compute_kpis", store=True)

    @api.depends("cost", "revenue", "impressions", "clicks", "orders")
    def _compute_kpis(self):
        for r in self:
            r.roas = (r.revenue / r.cost) if r.cost else 0.0
            r.acos = (r.cost / r.revenue * 100.0) if r.revenue else 0.0
            r.ctr = (r.clicks / r.impressions * 100.0) if r.impressions else 0.0
            r.cpc = (r.cost / r.clicks) if r.clicks else 0.0
            r.cvr = (r.orders / r.clicks * 100.0) if r.clicks else 0.0
