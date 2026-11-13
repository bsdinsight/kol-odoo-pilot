/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

const PLATFORM_LABELS = { shopee: "Shopee", tiktok: "TikTok Shop", lazada: "Lazada" };
const PLATFORM_COLORS = { shopee: "#ee4d2d", tiktok: "#111827", lazada: "#0f146d" };

function fmtVnd(n) {
    n = n || 0;
    if (Math.abs(n) >= 1e9) return (n / 1e9).toLocaleString("vi-VN", { maximumFractionDigits: 2 }) + " tỷ";
    if (Math.abs(n) >= 1e6) return (n / 1e6).toLocaleString("vi-VN", { maximumFractionDigits: 1 }) + " tr";
    return n.toLocaleString("vi-VN");
}
function platKey(v) { return Array.isArray(v) ? v[0] : v; }
function labelOf(v) {
    if (!v) return "Chưa gắn KOL";
    if (Array.isArray(v)) return v[1];
    if (typeof v === "object") return v.display_name || v.name || String(v.id);
    return String(v);
}
// Gom dữ liệu groupby [kỳ, platform] thành {labels, lazada[], shopee[], tiktok[]}
function pivotByPeriod(rows, periodKey) {
    const labels = [];
    const idx = {};
    const series = { shopee: {}, tiktok: {}, lazada: {} };
    for (const r of rows) {
        const lbl = labelOf(r[periodKey]);
        const p = platKey(r["platform"]);
        if (!(lbl in idx)) { idx[lbl] = labels.length; labels.push(lbl); }
        if (series[p]) series[p][lbl] = r["amount_net:sum"] || 0;
    }
    const arr = (p) => labels.map((l) => series[p][l] || 0);
    return { labels, lazada: arr("lazada"), shopee: arr("shopee"), tiktok: arr("tiktok") };
}
function platformDatasets(pv) {
    return [
        { label: "Lazada", data: pv.lazada, backgroundColor: PLATFORM_COLORS.lazada, borderRadius: 4 },
        { label: "Shopee", data: pv.shopee, backgroundColor: PLATFORM_COLORS.shopee, borderRadius: 4 },
        { label: "TikTok Shop", data: pv.tiktok, backgroundColor: PLATFORM_COLORS.tiktok, borderRadius: 4 },
    ];
}

export class KolDashboard extends Component {
    static template = "bsd_kol_report.KolDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            kpi: { gross: 0, net: 0, commission: 0, orders: 0, kols: 0, unattributed: 0, adCost: 0, adRevenue: 0, roas: 0 },
        });
        this.platformRef = useRef("platformChart");
        this.kolRef = useRef("kolChart");
        this.monthRef = useRef("monthChart");
        this.quarterRef = useRef("quarterChart");
        this.trendRef = useRef("trendChart");
        this.campaignRef = useRef("campaignChart");
        this.roasRef = useRef("roasChart");
        this.adsTrendRef = useRef("adsTrendChart");
        this.charts = [];
        this.fmtVnd = fmtVnd;

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.loadData();
        });
        onMounted(() => this.renderCharts());
        onWillUnmount(() => this.charts.forEach((c) => c.destroy()));
    }

    async loadData() {
        const AG = ["amount_gross:sum", "amount_net:sum", "commission:sum", "__count"];
        const [byPlatform, byKol, byMonth, byMonthPlat, byQuarterPlat, byCampaign] = await Promise.all([
            this.orm.formattedReadGroup("kol.order", [], ["platform"], AG),
            this.orm.formattedReadGroup("kol.order", [], ["kol_influencer_id"], ["amount_net:sum", "__count"]),
            this.orm.formattedReadGroup("kol.order", [], ["order_date:month"], ["amount_net:sum"]),
            this.orm.formattedReadGroup("kol.order", [], ["order_date:month", "platform"], ["amount_net:sum"]),
            this.orm.formattedReadGroup("kol.order", [], ["order_date:quarter", "platform"], ["amount_net:sum"]),
            this.orm.formattedReadGroup("kol.order", [["campaign_id", "!=", false]], ["campaign_id"], ["amount_net:sum"]),
        ]);

        let gross = 0, net = 0, commission = 0, orders = 0;
        this.platformData = [];
        for (const g of byPlatform) {
            const key = platKey(g["platform"]);
            gross += g["amount_gross:sum"] || 0;
            net += g["amount_net:sum"] || 0;
            commission += g["commission:sum"] || 0;
            orders += g["__count"] || 0;
            this.platformData.push({
                label: PLATFORM_LABELS[key] || key || "—",
                color: PLATFORM_COLORS[key] || "#9ca3af",
                net: g["amount_net:sum"] || 0,
            });
        }

        let unattributed = 0, kols = 0;
        const kolRows = [];
        for (const g of byKol) {
            const v = g["kol_influencer_id"];
            const count = g["__count"] || 0;
            const n = g["amount_net:sum"] || 0;
            if (!v || (Array.isArray(v) && !v[0])) {
                unattributed += count;
            } else {
                kols += 1;
                kolRows.push({ label: labelOf(v), net: n });
            }
        }
        kolRows.sort((a, b) => b.net - a.net);
        this.kolData = kolRows.slice(0, 10);

        this.trendData = byMonth.map((g) => ({
            label: labelOf(g["order_date:month"]),
            net: g["amount_net:sum"] || 0,
        }));
        this.monthByPlat = pivotByPeriod(byMonthPlat, "order_date:month");
        this.quarterByPlat = pivotByPeriod(byQuarterPlat, "order_date:quarter");
        this.campaignData = byCampaign
            .map((g) => ({ label: labelOf(g["campaign_id"]), net: g["amount_net:sum"] || 0 }))
            .sort((a, b) => b.net - a.net);

        // --- Ads / ROAS (luồng dữ liệu thứ 3) ---
        const [adByPlatform, adByMonth] = await Promise.all([
            this.orm.formattedReadGroup("kol.ad", [], ["platform"], ["cost:sum", "revenue:sum"]),
            this.orm.formattedReadGroup("kol.ad", [], ["date:month"], ["cost:sum", "revenue:sum"]),
        ]);
        let adCost = 0, adRevenue = 0;
        this.roasByPlatform = [];
        for (const g of adByPlatform) {
            const key = platKey(g["platform"]);
            const c = g["cost:sum"] || 0;
            const rv = g["revenue:sum"] || 0;
            adCost += c;
            adRevenue += rv;
            this.roasByPlatform.push({
                label: PLATFORM_LABELS[key] || key || "—",
                color: PLATFORM_COLORS[key] || "#9ca3af",
                roas: c ? rv / c : 0,
            });
        }
        this.adMonthly = {
            labels: adByMonth.map((g) => labelOf(g["date:month"])),
            cost: adByMonth.map((g) => g["cost:sum"] || 0),
            revenue: adByMonth.map((g) => g["revenue:sum"] || 0),
        };

        this.state.kpi = {
            gross, net, commission, orders, kols, unattributed,
            adCost, adRevenue, roas: adCost ? adRevenue / adCost : 0,
        };
        this.state.loading = false;
    }

    renderCharts() {
        const Chart = window.Chart;
        if (!Chart) { return; }
        const moneyY = { ticks: { callback: (v) => fmtVnd(v) } };

        if (this.platformRef.el && this.platformData) {
            this.charts.push(new Chart(this.platformRef.el, {
                type: "doughnut",
                data: {
                    labels: this.platformData.map((d) => d.label),
                    datasets: [{ data: this.platformData.map((d) => d.net), backgroundColor: this.platformData.map((d) => d.color) }],
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
            }));
        }
        if (this.kolRef.el && this.kolData) {
            this.charts.push(new Chart(this.kolRef.el, {
                type: "bar",
                data: {
                    labels: this.kolData.map((d) => d.label),
                    datasets: [{ label: "Doanh số sau huỷ/hoàn", data: this.kolData.map((d) => d.net), backgroundColor: "#4f46e5", borderRadius: 4 }],
                },
                options: { indexAxis: "y", responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } },
            }));
        }
        // So sánh theo THÁNG — cột chồng theo sàn
        if (this.monthRef.el && this.monthByPlat) {
            this.charts.push(new Chart(this.monthRef.el, {
                type: "bar",
                data: { labels: this.monthByPlat.labels, datasets: platformDatasets(this.monthByPlat) },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: "bottom" } },
                    scales: { x: { stacked: true }, y: { stacked: true, ...moneyY } },
                },
            }));
        }
        // So sánh theo QUÝ — cột nhóm theo sàn
        if (this.quarterRef.el && this.quarterByPlat) {
            this.charts.push(new Chart(this.quarterRef.el, {
                type: "bar",
                data: { labels: this.quarterByPlat.labels, datasets: platformDatasets(this.quarterByPlat) },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: "bottom" } },
                    scales: { y: moneyY },
                },
            }));
        }
        if (this.campaignRef.el && this.campaignData) {
            this.charts.push(new Chart(this.campaignRef.el, {
                type: "bar",
                data: {
                    labels: this.campaignData.map((d) => d.label),
                    datasets: [{ label: "Doanh số sau huỷ/hoàn", data: this.campaignData.map((d) => d.net), backgroundColor: "#7c3aed", borderRadius: 4 }],
                },
                options: {
                    indexAxis: "y", responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { x: moneyY },
                },
            }));
        }
        if (this.trendRef.el && this.trendData) {
            this.charts.push(new Chart(this.trendRef.el, {
                type: "line",
                data: {
                    labels: this.trendData.map((d) => d.label),
                    datasets: [{ label: "Doanh số sau huỷ/hoàn", data: this.trendData.map((d) => d.net), borderColor: "#0ea5e9", backgroundColor: "rgba(14,165,233,.15)", fill: true, tension: 0.3 }],
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: moneyY } },
            }));
        }
        // ROAS theo sàn (lần)
        if (this.roasRef.el && this.roasByPlatform) {
            this.charts.push(new Chart(this.roasRef.el, {
                type: "bar",
                data: {
                    labels: this.roasByPlatform.map((d) => d.label),
                    datasets: [{ label: "ROAS (lần)", data: this.roasByPlatform.map((d) => d.roas), backgroundColor: this.roasByPlatform.map((d) => d.color), borderRadius: 4 }],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { ticks: { callback: (v) => v + "x" } } },
                },
            }));
        }
        // Chi phí vs Doanh thu quảng cáo theo tháng
        if (this.adsTrendRef.el && this.adMonthly) {
            this.charts.push(new Chart(this.adsTrendRef.el, {
                type: "bar",
                data: {
                    labels: this.adMonthly.labels,
                    datasets: [
                        { label: "Chi phí QC", data: this.adMonthly.cost, backgroundColor: "#f59e0b", borderRadius: 4 },
                        { label: "Doanh thu QC", data: this.adMonthly.revenue, backgroundColor: "#10b981", borderRadius: 4 },
                    ],
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { position: "bottom" } },
                    scales: { y: moneyY },
                },
            }));
        }
    }
}

registry.category("actions").add("bsd_kol_report.dashboard", KolDashboard);
