{
    "name": "BSD KOL Sales Report (Demo)",
    "version": "19.0.1.0.0",
    "summary": "Báo cáo hiệu quả bán hàng theo KOL trên Shopee & TikTok Shop — bản demo dữ liệu mẫu",
    "description": """
Báo cáo hiệu quả bán hàng theo KOL (demo)
=========================================
Trình diễn mô hình báo cáo hiệu quả KOL/tiếp thị liên kết trên Shopee và
TikTok Shop theo đúng bộ chỉ tiêu trong scope: doanh số phát sinh vs sau
huỷ/hoàn, số đơn vs số lượng sản phẩm, hoa hồng, ghép danh tính KOL chéo
sàn, bucket đơn chưa gắn KOL, và trạng thái cập nhật từng nguồn.

Bản demo chạy trên DỮ LIỆU MẪU, chưa kết nối API thật.
""",
    "author": "BSD",
    "website": "https://bsdinsight.com",
    "license": "LGPL-3",
    "category": "Sales/Reporting",
    "depends": [
        "base", "web", "sale_management", "stock", "sale_stock",
        "delivery", "stock_delivery",
    ],
    "data": [
        "security/kol_security.xml",
        "security/ir.model.access.csv",
        "views/kol_views.xml",
        "views/ads_views.xml",
        "views/payout_views.xml",
        "views/oms_views.xml",
        "data/delivery_carriers.xml",
        "data/kol_cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "bsd_kol_report/static/src/dashboard/kol_dashboard.scss",
            "bsd_kol_report/static/src/dashboard/kol_dashboard.js",
            "bsd_kol_report/static/src/dashboard/kol_dashboard.xml",
        ],
    },
    "application": True,
    "installable": True,
}
