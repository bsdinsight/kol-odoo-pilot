# KOL–TikTok Odoo pilot

Bộ cài nhanh **Odoo 19 + module `bsd_kol_report`** (báo cáo hiệu quả KOL bán qua sàn
Shopee · TikTok Shop · Lazada: OMS/giao hàng, Ads/ROAS, đối soát payout) — chạy **dữ liệu mẫu**.

Đây là **ống chuyển code** để cài lên server pilot. Dữ liệu là mẫu, không chứa thông tin thật.

## Cài trên Ubuntu

```bash
git clone https://github.com/bsdinsight/kol-odoo-pilot.git
cd kol-odoo-pilot
bash deploy.sh
```

Script sẽ: cài Docker (nếu thiếu) → sinh mật khẩu mạnh → dựng Odoo + Postgres →
tạo DB `demo` + cài module (kèm phụ thuộc) → đặt company VND, gỡ thuế mặc định →
nạp dữ liệu mẫu (≈884 đơn, 10 KOL, Ads, đối soát) → in ra URL + tài khoản.

Truy cập: `http://<server-ip>:8075` (DB `demo`). Nhớ **mở cổng 8075** trên firewall.

> Bảo mật: không mở cổng Postgres ra ngoài; mật khẩu master + admin được sinh ngẫu nhiên khi deploy.
