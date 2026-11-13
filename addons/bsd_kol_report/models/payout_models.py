"""Đối soát payout sàn (Tầng 2) — khớp payout ↔ đơn ↔ phí.

Sàn giữ tiền, trừ hàng loạt phí (hoa hồng · thanh toán · vận chuyển · voucher)
rồi chi trả theo kỳ. Model đối soát: số sàn báo chi trả (payout_declared) so với
số đáng nhận tính từ đơn − phí (payout_expected) → bắt chênh lệch.
"""

from odoo import api, fields, models

from .kol_models import PLATFORMS

PAYOUT_TOLERANCE = 1000.0  # đồng — ngưỡng coi là khớp

MATCH_STATES = [("ok", "Khớp"), ("diff", "Lệch")]
PAYOUT_WF = [("draft", "Chờ nhận tiền"), ("paid", "Đã nhận tiền")]


class KolPayout(models.Model):
    _name = "kol.payout"
    _description = "Kỳ đối soát payout sàn"
    _order = "period_start desc, platform"

    name = fields.Char(string="Kỳ đối soát", required=True)
    platform = fields.Selection(PLATFORMS, string="Nền tảng", required=True)
    shop_id = fields.Many2one("kol.shop", string="Shop")
    statement_ref = fields.Char(string="Mã sao kê sàn")
    period_start = fields.Date(string="Từ ngày", required=True)
    period_end = fields.Date(string="Đến ngày", required=True)
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.ref("base.VND")
    )
    state = fields.Selection(PAYOUT_WF, string="Trạng thái", default="draft", copy=False)

    line_ids = fields.One2many("kol.payout.line", "payout_id", string="Dòng đối soát")
    order_count = fields.Integer(string="Số đơn", compute="_compute_amounts", store=True)

    gross_amount = fields.Monetary(string="Doanh thu đơn", compute="_compute_amounts", store=True)
    fee_commission = fields.Monetary(string="Hoa hồng sàn", compute="_compute_amounts", store=True)
    fee_payment = fields.Monetary(string="Phí thanh toán", compute="_compute_amounts", store=True)
    fee_shipping = fields.Monetary(string="Phí vận chuyển", compute="_compute_amounts", store=True)
    fee_voucher = fields.Monetary(string="Voucher/Xu", compute="_compute_amounts", store=True)
    total_fees = fields.Monetary(string="Tổng phí", compute="_compute_amounts", store=True)
    payout_expected = fields.Monetary(
        string="Đáng nhận (đơn − phí)", compute="_compute_amounts", store=True
    )
    payout_declared = fields.Monetary(string="Sàn báo chi trả")
    diff = fields.Monetary(string="Chênh lệch", compute="_compute_amounts", store=True)
    match_state = fields.Selection(
        MATCH_STATES, string="Đối soát", compute="_compute_amounts", store=True
    )

    @api.depends(
        "payout_declared",
        "line_ids.gross",
        "line_ids.fee_commission",
        "line_ids.fee_payment",
        "line_ids.fee_shipping",
        "line_ids.fee_voucher",
        "line_ids.net_payout",
    )
    def _compute_amounts(self):
        for rec in self:
            lines = rec.line_ids
            rec.order_count = len(lines)
            rec.gross_amount = sum(lines.mapped("gross"))
            rec.fee_commission = sum(lines.mapped("fee_commission"))
            rec.fee_payment = sum(lines.mapped("fee_payment"))
            rec.fee_shipping = sum(lines.mapped("fee_shipping"))
            rec.fee_voucher = sum(lines.mapped("fee_voucher"))
            rec.total_fees = (
                rec.fee_commission + rec.fee_payment + rec.fee_shipping + rec.fee_voucher
            )
            rec.payout_expected = sum(lines.mapped("net_payout"))
            rec.diff = rec.payout_declared - rec.payout_expected
            rec.match_state = "ok" if abs(rec.diff) <= PAYOUT_TOLERANCE else "diff"

    def _notify(self, title, message, kind="info"):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": title, "message": message, "type": kind, "sticky": False},
        }

    def action_reconcile(self):
        self.ensure_one()
        if self.match_state == "ok":
            return self._notify(
                "Khớp đối soát",
                "Sàn báo chi trả khớp số đáng nhận (%s đơn, tổng phí %s đ)."
                % (self.order_count, "{:,.0f}".format(self.total_fees)),
                "success",
            )
        return self._notify(
            "Lệch đối soát",
            "Chênh lệch %s đ giữa số sàn báo và số đáng nhận — cần rà lại phí/đơn trong kỳ."
            % "{:,.0f}".format(self.diff),
            "warning",
        )

    def action_mark_paid(self):
        self.write({"state": "paid"})

    def action_view_orders(self):
        self.ensure_one()
        orders = self.line_ids.mapped("order_id")
        return {
            "type": "ir.actions.act_window",
            "name": "Đơn trong kỳ — %s" % self.name,
            "res_model": "kol.order",
            "view_mode": "list,form,pivot,graph",
            "domain": [("id", "in", orders.ids)],
        }


class KolPayoutLine(models.Model):
    _name = "kol.payout.line"
    _description = "Dòng đối soát payout (theo đơn)"
    _order = "payout_id"

    payout_id = fields.Many2one(
        "kol.payout", string="Kỳ đối soát", required=True, ondelete="cascade"
    )
    order_id = fields.Many2one("kol.order", string="Đơn hàng")
    platform = fields.Selection(related="payout_id.platform", store=True)
    currency_id = fields.Many2one(related="payout_id.currency_id", store=True)

    gross = fields.Monetary(string="Doanh thu đơn")
    fee_commission = fields.Monetary(string="Hoa hồng sàn")
    fee_payment = fields.Monetary(string="Phí thanh toán")
    fee_shipping = fields.Monetary(string="Phí vận chuyển")
    fee_voucher = fields.Monetary(string="Voucher/Xu")
    net_payout = fields.Monetary(
        string="Thực nhận", compute="_compute_net", store=True
    )

    @api.depends("gross", "fee_commission", "fee_payment", "fee_shipping", "fee_voucher")
    def _compute_net(self):
        for line in self:
            line.net_payout = (
                line.gross
                - line.fee_commission
                - line.fee_payment
                - line.fee_shipping
                - line.fee_voucher
            )
