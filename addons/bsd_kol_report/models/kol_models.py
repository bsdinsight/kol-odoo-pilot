from datetime import timedelta

from odoo import api, fields, models

PLATFORMS = [
    ("shopee", "Shopee"),
    ("tiktok", "TikTok Shop"),
    ("lazada", "Lazada"),
]

SYNC_INTERVALS = [
    ("manual", "Thủ công"),
    ("hourly", "Mỗi giờ"),
    ("every_4h", "Mỗi 4 giờ"),
    ("daily", "Hằng ngày"),
    ("weekly", "Hằng tuần"),
]

ORDER_STATES = [
    ("confirmed", "Hoàn tất"),
    ("partial", "Hoàn một phần"),
    ("returned", "Hoàn toàn bộ"),
    ("cancelled", "Đã huỷ"),
]


class KolShop(models.Model):
    _name = "kol.shop"
    _description = "Shop sàn TMĐT"
    _order = "platform, name"

    name = fields.Char(string="Tên shop", required=True)
    platform = fields.Selection(PLATFORMS, string="Nền tảng", required=True)


class KolInfluencer(models.Model):
    _name = "kol.influencer"
    _description = "KOL / Người tiếp thị liên kết"
    _order = "name"

    name = fields.Char(string="Tên KOL", required=True)
    note = fields.Text(string="Ghi chú")
    account_ids = fields.One2many("kol.account", "influencer_id", string="Tài khoản sàn")
    account_count = fields.Integer(string="Số tài khoản", compute="_compute_account_count")

    @api.depends("account_ids")
    def _compute_account_count(self):
        for rec in self:
            rec.account_count = len(rec.account_ids)


class KolAccount(models.Model):
    _name = "kol.account"
    _description = "Tài khoản KOL trên sàn"
    _order = "platform, handle"

    name = fields.Char(compute="_compute_name", store=True)
    influencer_id = fields.Many2one(
        "kol.influencer", string="KOL", required=True, ondelete="cascade"
    )
    platform = fields.Selection(PLATFORMS, string="Nền tảng", required=True)
    handle = fields.Char(string="Định danh trên sàn", required=True)

    @api.depends("platform", "handle")
    def _compute_name(self):
        labels = dict(PLATFORMS)
        for rec in self:
            rec.name = "%s · %s" % (labels.get(rec.platform) or "", rec.handle or "")


class KolProduct(models.Model):
    _name = "kol.product"
    _description = "Sản phẩm"
    _order = "name"

    name = fields.Char(string="Tên sản phẩm", required=True)
    sku = fields.Char(string="Mã SKU")
    category = fields.Char(string="Ngành hàng")


class KolOrder(models.Model):
    _name = "kol.order"
    _description = "Đơn hàng theo KOL"
    _order = "order_date desc, name desc"

    name = fields.Char(string="Mã đơn", required=True, index=True)
    platform = fields.Selection(PLATFORMS, string="Nền tảng", required=True)
    shop_id = fields.Many2one("kol.shop", string="Shop", required=True)
    order_date = fields.Date(string="Ngày đặt", required=True, index=True)
    state = fields.Selection(
        ORDER_STATES, string="Trạng thái", required=True, default="confirmed"
    )

    kol_account_id = fields.Many2one("kol.account", string="Tài khoản KOL")
    kol_influencer_id = fields.Many2one(
        "kol.influencer",
        string="KOL",
        related="kol_account_id.influencer_id",
        store=True,
        readonly=True,
    )
    is_attributed = fields.Boolean(
        string="Đã gắn KOL", compute="_compute_is_attributed", store=True
    )
    campaign_id = fields.Many2one(
        "kol.campaign", string="Chiến dịch", ondelete="set null", index=True
    )

    line_ids = fields.One2many("kol.order.line", "order_id", string="Dòng sản phẩm")
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.ref("base.VND")
    )

    amount_gross = fields.Monetary(
        string="Doanh số phát sinh", compute="_compute_amounts", store=True
    )
    amount_net = fields.Monetary(
        string="Doanh số sau huỷ/hoàn", compute="_compute_amounts", store=True
    )
    units_gross = fields.Integer(
        string="SL phát sinh", compute="_compute_amounts", store=True
    )
    units_net = fields.Integer(
        string="SL sau huỷ/hoàn", compute="_compute_amounts", store=True
    )
    commission_rate = fields.Float(string="Tỷ lệ hoa hồng")
    commission = fields.Monetary(
        string="Hoa hồng", compute="_compute_amounts", store=True
    )

    @api.depends("kol_account_id")
    def _compute_is_attributed(self):
        for rec in self:
            rec.is_attributed = bool(rec.kol_account_id)

    @api.depends(
        "line_ids.amount_gross",
        "line_ids.amount_net",
        "line_ids.qty",
        "line_ids.qty_net",
        "state",
        "commission_rate",
    )
    def _compute_amounts(self):
        for rec in self:
            rec.amount_gross = sum(rec.line_ids.mapped("amount_gross"))
            rec.amount_net = sum(rec.line_ids.mapped("amount_net"))
            rec.units_gross = sum(rec.line_ids.mapped("qty"))
            rec.units_net = sum(rec.line_ids.mapped("qty_net"))
            rec.commission = rec.amount_net * rec.commission_rate


class KolOrderLine(models.Model):
    _name = "kol.order.line"
    _description = "Dòng sản phẩm của đơn"
    _order = "order_id"

    order_id = fields.Many2one("kol.order", string="Đơn hàng", required=True, ondelete="cascade")
    product_id = fields.Many2one("kol.product", string="Sản phẩm", required=True)
    qty = fields.Integer(string="Số lượng", default=1)
    qty_returned = fields.Integer(string="SL hoàn", default=0)
    unit_price = fields.Monetary(string="Đơn giá")

    currency_id = fields.Many2one(related="order_id.currency_id", store=True)
    # Chiều phân tích (lấy từ đơn) để pivot/graph gom nhóm được ở cấp dòng
    platform = fields.Selection(related="order_id.platform", store=True)
    shop_id = fields.Many2one(related="order_id.shop_id", store=True)
    order_date = fields.Date(related="order_id.order_date", store=True)
    order_state = fields.Selection(related="order_id.state", string="Trạng thái đơn", store=True)
    kol_influencer_id = fields.Many2one(related="order_id.kol_influencer_id", store=True)
    kol_account_id = fields.Many2one(related="order_id.kol_account_id", store=True)
    campaign_id = fields.Many2one(related="order_id.campaign_id", store=True)

    qty_net = fields.Integer(string="SL thực", compute="_compute_line", store=True)
    amount_gross = fields.Monetary(string="Thành tiền", compute="_compute_line", store=True)
    amount_net = fields.Monetary(string="Thành tiền thực", compute="_compute_line", store=True)

    @api.depends("qty", "qty_returned", "unit_price", "order_id.state")
    def _compute_line(self):
        for rec in self:
            state = rec.order_id.state
            rec.amount_gross = rec.qty * rec.unit_price
            if state in ("cancelled", "returned"):
                rec.qty_net = 0
                rec.amount_net = 0.0
            elif state == "partial":
                net_qty = max(rec.qty - rec.qty_returned, 0)
                rec.qty_net = net_qty
                rec.amount_net = net_qty * rec.unit_price
            else:  # confirmed
                rec.qty_net = rec.qty
                rec.amount_net = rec.qty * rec.unit_price


class KolSyncStatus(models.Model):
    _name = "kol.sync.status"
    _description = "Trạng thái cập nhật dữ liệu nguồn"
    _order = "platform"

    name = fields.Char(compute="_compute_name", store=True)
    platform = fields.Selection(PLATFORMS, string="Nền tảng", required=True)
    shop_id = fields.Many2one("kol.shop", string="Shop")
    last_success = fields.Datetime(string="Cập nhật thành công gần nhất")
    state = fields.Selection(
        [("ok", "OK"), ("stale", "Trễ"), ("error", "Lỗi")],
        string="Trạng thái",
        default="ok",
    )
    message = fields.Char(string="Ghi chú")

    @api.depends("platform", "shop_id")
    def _compute_name(self):
        labels = dict(PLATFORMS)
        for rec in self:
            suffix = (" · " + rec.shop_id.name) if rec.shop_id else ""
            rec.name = "%s%s" % (labels.get(rec.platform) or "", suffix)


class KolConnection(models.Model):
    _name = "kol.connection"
    _description = "Cấu hình kết nối nguồn dữ liệu (Shopee / TikTok Shop / Lazada)"
    _order = "platform"

    name = fields.Char(compute="_compute_name", store=True)
    platform = fields.Selection(PLATFORMS, string="Nền tảng", required=True)
    shop_id = fields.Many2one("kol.shop", string="Shop")
    source_type = fields.Selection(
        [("api", "API"), ("file", "Nhập file (export AMS)")],
        string="Nguồn dữ liệu", default="api", required=True,
    )
    mode = fields.Selection(
        [("sample", "Dữ liệu mẫu (demo)"), ("live", "Chạy thật")],
        string="Chế độ", default="sample", required=True,
    )
    state = fields.Selection(
        [("draft", "Chưa cấu hình"), ("configured", "Đã nhập tham số"), ("connected", "Đã kết nối")],
        string="Trạng thái", default="draft",
    )
    region = fields.Char(string="Thị trường", default="VN")
    base_url = fields.Char(string="API base URL")
    history_days = fields.Integer(string="Lịch sử (ngày)", default=90)

    # Lịch đồng bộ (Schedule)
    sync_active = fields.Boolean(string="Bật lịch đồng bộ", default=True)
    sync_interval = fields.Selection(SYNC_INTERVALS, string="Tần suất", default="daily")
    sync_hour = fields.Float(string="Giờ chạy (hằng ngày)", default=2.0)
    next_sync = fields.Datetime(string="Lần chạy kế tiếp", compute="_compute_next_sync")

    # Shopee Open Platform
    shopee_partner_id = fields.Char(string="Partner ID")
    shopee_partner_key = fields.Char(string="Partner Key")
    shopee_shop_id = fields.Char(string="Shop ID")
    shopee_access_token = fields.Char(string="Access Token")
    shopee_refresh_token = fields.Char(string="Refresh Token")

    # TikTok Shop Partner API
    tiktok_app_key = fields.Char(string="App Key")
    tiktok_app_secret = fields.Char(string="App Secret")
    tiktok_shop_cipher = fields.Char(string="Shop Cipher")
    tiktok_service_id = fields.Char(string="Service ID")
    tiktok_access_token = fields.Char(string="Access Token")
    tiktok_refresh_token = fields.Char(string="Refresh Token")
    tiktok_affiliate_enabled = fields.Boolean(string="Đã được duyệt Affiliate API")

    # Lazada Open Platform
    lazada_app_key = fields.Char(string="App Key")
    lazada_app_secret = fields.Char(string="App Secret")
    lazada_seller_id = fields.Char(string="Seller ID")
    lazada_access_token = fields.Char(string="Access Token")
    lazada_refresh_token = fields.Char(string="Refresh Token")

    # Quảng cáo (Ads) — lấy chi phí/ROAS
    ads_enabled = fields.Boolean(string="Lấy dữ liệu quảng cáo (Ads)")
    shopee_ads_shop_id = fields.Char(string="Shopee Ads — Shop ID")
    tiktok_ads_advertiser_id = fields.Char(string="TikTok Ads — Advertiser ID")
    lazada_ads_account_id = fields.Char(string="Lazada Sponsored — Account ID")

    last_test = fields.Datetime(string="Lần kiểm tra gần nhất", readonly=True)
    last_test_message = fields.Char(string="Kết quả kiểm tra", readonly=True)
    last_sync = fields.Datetime(string="Đồng bộ gần nhất", readonly=True)
    note = fields.Text(string="Ghi chú")

    @api.depends("platform", "shop_id")
    def _compute_name(self):
        labels = dict(PLATFORMS)
        for rec in self:
            suffix = (" · " + rec.shop_id.name) if rec.shop_id else ""
            rec.name = "%s%s" % (labels.get(rec.platform) or "", suffix)

    @api.depends("sync_active", "sync_interval", "last_sync")
    def _compute_next_sync(self):
        now = fields.Datetime.now()
        deltas = {
            "hourly": timedelta(hours=1),
            "every_4h": timedelta(hours=4),
            "daily": timedelta(days=1),
            "weekly": timedelta(weeks=1),
        }
        for rec in self:
            delta = deltas.get(rec.sync_interval)
            if not rec.sync_active or not delta:
                rec.next_sync = False
                continue
            nxt = (rec.last_sync or now) + delta
            if nxt < now:
                nxt = now + delta
            rec.next_sync = nxt

    @api.model
    def _cron_sync_all(self):
        """Đồng bộ theo lịch. Bản demo: chỉ cập nhật mốc cho kết nối 'Chạy thật'
        (không có → no-op an toàn). Khi triển khai: gọi API từng sàn tại đây."""
        now = fields.Datetime.now()
        for conn in self.search([("sync_active", "=", True), ("mode", "=", "live")]):
            conn.last_sync = now
        return True

    def _missing_params(self):
        self.ensure_one()
        if self.source_type == "file":
            return []
        if self.platform == "shopee":
            checks = [
                ("Partner ID", self.shopee_partner_id),
                ("Partner Key", self.shopee_partner_key),
                ("Shop ID", self.shopee_shop_id),
            ]
        elif self.platform == "tiktok":
            checks = [
                ("App Key", self.tiktok_app_key),
                ("App Secret", self.tiktok_app_secret),
                ("Shop Cipher", self.tiktok_shop_cipher),
            ]
        else:  # lazada
            checks = [
                ("App Key", self.lazada_app_key),
                ("App Secret", self.lazada_app_secret),
                ("Access Token", self.lazada_access_token),
            ]
        return [label for label, val in checks if not val]

    def _notify(self, title, message, kind="info"):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": title, "message": message, "type": kind, "sticky": False},
        }

    def action_test_connection(self):
        self.ensure_one()
        plat = dict(PLATFORMS).get(self.platform) or ""
        if self.mode == "sample":
            return self._notify(
                "Chế độ dữ liệu mẫu",
                "Đang chạy DỮ LIỆU MẪU — ứng dụng chưa gọi API thật. "
                "Điền tham số tài khoản rồi chuyển Chế độ = 'Chạy thật' để kết nối %s." % plat,
                "info",
            )
        missing = self._missing_params()
        if missing:
            self.write({"state": "configured"})
            return self._notify("Thiếu tham số", "Cần nhập: " + ", ".join(missing), "warning")
        self.write({
            "state": "connected",
            "last_test": fields.Datetime.now(),
            "last_test_message": "Tham số hợp lệ (bản demo không gọi API thật).",
        })
        return self._notify(
            "Tham số hợp lệ",
            "Đã nhận đủ tham số cho %s. Khi chạy thật, ứng dụng dùng các tham số này để "
            "gọi API và đồng bộ đơn về báo cáo." % plat,
            "success",
        )

    def action_sync_now(self):
        self.ensure_one()
        if self.mode == "sample":
            return self._notify(
                "Chế độ dữ liệu mẫu",
                "Báo cáo đang hiển thị dữ liệu mẫu. Đồng bộ thật sẽ hoạt động sau khi "
                "cấu hình tài khoản và chuyển sang 'Chạy thật'.",
                "info",
            )
        if self._missing_params():
            return self._notify(
                "Chưa đủ tham số",
                "Hãy bấm 'Kiểm tra kết nối' và điền đủ tham số trước.",
                "warning",
            )
        self.write({"last_sync": fields.Datetime.now()})
        return self._notify("Đã kích hoạt đồng bộ", "Đã gửi yêu cầu đồng bộ (bản demo).", "success")


CAMPAIGN_TYPES = [
    ("affiliate_open", "Affiliate – Mở hoa hồng (mọi KOL)"),
    ("affiliate_target", "Affiliate – Mời KOL cụ thể"),
    ("promo_discount", "Khuyến mãi – Giảm giá / Flash sale"),
    ("promo_voucher", "Khuyến mãi – Voucher"),
]

CAMPAIGN_STATES = [
    ("draft", "Nháp"),
    ("pushed", "Đã đẩy lên sàn"),
    ("active", "Đang chạy"),
    ("closed", "Đã đóng"),
]


class KolCampaign(models.Model):
    _name = "kol.campaign"
    _description = "Chiến dịch đẩy lên sàn"
    _order = "date_start desc, name"

    name = fields.Char(string="Tên chiến dịch", required=True)
    campaign_type = fields.Selection(
        CAMPAIGN_TYPES, string="Loại", required=True, default="affiliate_open"
    )
    platform = fields.Selection(PLATFORMS, string="Sàn đích", required=True)
    shop_id = fields.Many2one("kol.shop", string="Shop")
    date_start = fields.Date(string="Bắt đầu")
    date_end = fields.Date(string="Kết thúc")
    product_ids = fields.Many2many("kol.product", string="Sản phẩm")
    kol_account_ids = fields.Many2many("kol.account", string="KOL được mời")
    commission_rate = fields.Float(string="Hoa hồng (%)", default=10.0)
    discount_percent = fields.Float(string="Giảm giá (%)", default=10.0)
    state = fields.Selection(CAMPAIGN_STATES, string="Trạng thái", default="draft")
    push_channel = fields.Char(string="Cách đẩy", compute="_compute_push_channel")
    is_api_push = fields.Boolean(compute="_compute_push_channel")
    last_push = fields.Datetime(string="Lần đẩy gần nhất", readonly=True)
    push_note = fields.Char(string="Ghi chú đẩy", readonly=True)
    order_ids = fields.One2many("kol.order", "campaign_id", string="Đơn hàng")
    order_count = fields.Integer(string="Số đơn", compute="_compute_order_count")

    @api.depends("order_ids")
    def _compute_order_count(self):
        for rec in self:
            rec.order_count = len(rec.order_ids)

    def action_view_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Đơn hàng – %s" % self.name,
            "res_model": "kol.order",
            "view_mode": "list,form,pivot,graph",
            "domain": [("campaign_id", "=", self.id)],
        }

    def _push_plan(self):
        """Khả năng đẩy theo (sàn, loại) — phản ánh thực tế API từng sàn."""
        self.ensure_one()
        p, t = self.platform, self.campaign_type
        if t in ("promo_discount", "promo_voucher"):
            if p == "shopee":
                return True, "API – Shopee Discount/Promotion"
            if p == "tiktok":
                return True, "API – TikTok Promotion"
            return False, "Cần xác minh – Lazada Seller Center"
        # affiliate_open / affiliate_target
        if p == "tiktok":
            return True, "API – TikTok Affiliate Seller (Open/Target Collaboration)"
        if p == "shopee":
            return False, "Thủ công – Shopee Seller Centre (AMS)"
        return False, "Cần xác minh – Lazada Affiliate"

    @api.depends("platform", "campaign_type")
    def _compute_push_channel(self):
        for rec in self:
            if not rec.platform or not rec.campaign_type:
                rec.push_channel = ""
                rec.is_api_push = False
                continue
            is_api, desc = rec._push_plan()
            rec.push_channel = desc
            rec.is_api_push = is_api

    def _notify(self, title, message, kind="info"):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": title, "message": message, "type": kind, "sticky": False},
        }

    def action_push(self):
        self.ensure_one()
        is_api, desc = self._push_plan()
        plat = dict(PLATFORMS).get(self.platform) or ""
        self.write({
            "state": "pushed",
            "last_push": fields.Datetime.now(),
            "push_note": desc,
        })
        if is_api:
            return self._notify(
                "Đã đẩy (demo)",
                "Bản demo KHÔNG gọi API thật. Khi chạy thật: %s sẽ tạo chiến dịch này trên %s." % (desc, plat),
                "success",
            )
        return self._notify(
            "Cần thao tác thủ công",
            "%s chưa có API tạo loại chiến dịch này. Khi triển khai: soạn sẵn trong hệ thống rồi áp thủ công trên Seller Centre (%s)." % (plat, desc),
            "warning",
        )
