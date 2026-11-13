#!/usr/bin/env bash
# Deploy the KOL–TikTok Odoo pilot on a fresh Ubuntu server.
# Idempotent-ish: safe to re-run; it recreates the demo DB only on first init.
set -euo pipefail
cd "$(cd "$(dirname "$0")" && pwd)"

log(){ echo -e "\n>>> $*"; }

# 1) Docker ---------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker…"
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
fi
if docker info >/dev/null 2>&1; then DC="docker"; else DC="sudo docker"; fi
$DC compose version >/dev/null 2>&1 || { echo "ERROR: docker compose plugin missing"; exit 1; }

# 2) Secrets: replace placeholders (only if still placeholders) ------------
if grep -q "__ADMIN_PASSWD__" config/odoo.conf; then
  ADMIN_MASTER=$(openssl rand -hex 16)
  DB_PASSWD=$(openssl rand -hex 12)
  sed -i "s|__ADMIN_PASSWD__|${ADMIN_MASTER}|g; s|__DB_PASSWD__|${DB_PASSWD}|g" config/odoo.conf docker-compose.yml
  echo "${ADMIN_MASTER}" > .master_passwd
else
  ADMIN_MASTER=$(cat .master_passwd 2>/dev/null || echo "(already set)")
fi
ADMIN_LOGIN_PW=$(openssl rand -hex 6)

# 3) Up -------------------------------------------------------------------
log "Starting containers (pulling images on first run)…"
$DC compose up -d
log "Waiting for Odoo web on :8075…"
for i in $(seq 1 120); do
  curl -sf -o /dev/null http://localhost:8075/web/login 2>/dev/null && { echo "web up"; break; }
  sleep 3
done

# 4) Create DB 'demo' + install module (deps auto, no Odoo demo data) -----
log "Initializing DB 'demo' with bsd_kol_report…"
$DC exec odoo odoo -d demo -i bsd_kol_report --without-demo=all --stop-after-init --no-http

# 5) Company VND + strip default tax + set admin login password -----------
log "Configuring company (VND, no default tax) + admin password…"
$DC exec -i odoo odoo shell -d demo --no-http <<PY
vnd = env.ref('base.VND'); vnd.active = True
env.company.currency_id = vnd.id
env.company.account_sale_tax_id = False
env.company.account_purchase_tax_id = False
for p in env['product.pricelist'].search([]): p.currency_id = vnd.id
env.ref('base.user_admin').password = '${ADMIN_LOGIN_PW}'
env.cr.commit()
print('currency=', env.company.currency_id.name, 'admin_pw_set=yes')
PY

# 6) Seed demo data -------------------------------------------------------
for f in seed_demo seed_lazada seed_july seed_stock seed_ads seed_payout seed_campaign_orders; do
  log "Seeding ${f}…"
  $DC exec -i odoo odoo shell -d demo --no-http < "${f}.py" || echo "WARN: ${f} had issues"
done

# 7) Restart + verify -----------------------------------------------------
log "Restarting Odoo…"
$DC restart odoo
sleep 10
curl -sf -o /dev/null http://localhost:8075/web/login && echo "web OK after restart" || echo "WARN: web not responding"

IP=$(hostname -I 2>/dev/null | awk '{print $1}')
cat <<EOT

==================  PILOT ĐÃ CÀI XONG  ==================
  URL      : http://${IP}:8075   (public: http://125.253.121.80:8075)
  Database : demo
  Login    : admin
  Password : ${ADMIN_LOGIN_PW}
  Master (admin_passwd): ${ADMIN_MASTER}
  >> LƯU LẠI 2 mật khẩu trên. Mở cổng 8075 trên firewall/security group nếu chưa.
========================================================
EOT
