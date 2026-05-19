"""
IDS ESP32 - Server Dashboard
Versi Docker + SQLite permanen
"""
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
from collections import Counter
import sqlite3
import os

app = Flask(__name__)
DB_PATH = "/app/data/ids.db"

# ============================================
# SETUP DATABASE
# ============================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS serangan (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            waktu     TEXT,
            tanggal   TEXT,
            ip        TEXT,
            port      INTEGER,
            protokol  TEXT,
            payload   TEXT,
            total     INTEGER
        )
    """)
    conn.commit()
    conn.close()

def simpan_log(data):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO serangan (waktu, tanggal, ip, port, protokol, payload, total)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('waktu'),
        data.get('tanggal'),
        data.get('ip'),
        data.get('port'),
        data.get('protokol'),
        data.get('payload', ''),
        data.get('total', 0)
    ))
    conn.commit()
    conn.close()

def ambil_log(limit=50):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM serangan ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def ambil_statistik():
    conn = sqlite3.connect(DB_PATH)
    total     = conn.execute("SELECT COUNT(*) FROM serangan").fetchone()[0]
    ip_unik   = conn.execute("SELECT COUNT(DISTINCT ip) FROM serangan").fetchone()[0]
    port_top  = conn.execute(
        "SELECT protokol, COUNT(*) as c FROM serangan GROUP BY protokol ORDER BY c DESC LIMIT 1"
    ).fetchone()
    terakhir  = conn.execute(
        "SELECT waktu FROM serangan ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return {
        "total": total,
        "ip_unik": ip_unik,
        "port_terbanyak": port_top[0] if port_top else "-",
        "terakhir": terakhir[0] if terakhir else "-"
    }

# ============================================
# DASHBOARD HTML
# ============================================
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="5">
  <title>IDS ESP32 - Dashboard</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', sans-serif; background: #0f1117; color: #e0e0e0; padding: 24px; }
    h1 { font-size: 22px; margin-bottom: 4px; color: #fff; }
    .subtitle { font-size: 13px; color: #888; margin-bottom: 24px; }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 24px; }
    .stat { background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 10px; padding: 16px 20px; }
    .stat-label { font-size: 12px; color: #888; margin-bottom: 6px; }
    .stat-val { font-size: 28px; font-weight: 600; }
    .merah { color: #ff5c5c; }
    .hijau { color: #4caf82; }
    .kuning { color: #f0b429; }
    h2 { font-size: 15px; margin-bottom: 12px; color: #ccc; }
    table { width: 100%; border-collapse: collapse; background: #1a1d27; border-radius: 10px; overflow: hidden; }
    th { background: #22263a; padding: 10px 14px; text-align: left; font-size: 12px; color: #888; }
    td { padding: 10px 14px; font-size: 13px; border-top: 1px solid #2a2d3a; }
    tr:hover td { background: #1f2235; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
    .badge-mqtt   { background: #1a3a2a; color: #4caf82; }
    .badge-coap   { background: #1a2a3a; color: #5bc0eb; }
    .badge-telnet { background: #3a1a1a; color: #ff5c5c; }
    .empty { text-align: center; padding: 40px; color: #555; }
    .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #4caf82; margin-right: 6px; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
    .header-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
    .live { font-size: 12px; color: #4caf82; display: flex; align-items: center; }
    .port-info { font-size: 12px; color: #555; margin-bottom: 20px; }
    .port-info span { background: #1a1d27; border: 1px solid #2a2d3a; border-radius: 6px; padding: 4px 10px; margin-right: 8px; }
  </style>
</head>
<body>
  <div class="header-row">
    <div>
      <h1>🛡 IDS ESP32 — Dashboard</h1>
      <p class="subtitle">Monitoring serangan real-time • Auto-refresh 5 detik</p>
    </div>
    <div class="live"><span class="dot"></span> LIVE</div>
  </div>

  <div class="port-info">
    Port dimonitor:
    <span>1883 MQTT</span>
    <span>5683 CoAP</span>
    <span>23 Telnet</span>
  </div>

  <div class="stats">
    <div class="stat"><div class="stat-label">Total Serangan</div><div class="stat-val merah">{{ stat.total }}</div></div>
    <div class="stat"><div class="stat-label">IP Unik</div><div class="stat-val kuning">{{ stat.ip_unik }}</div></div>
    <div class="stat"><div class="stat-label">Port Terbanyak</div><div class="stat-val hijau">{{ stat.port_terbanyak }}</div></div>
    <div class="stat"><div class="stat-label">Serangan Terakhir</div><div class="stat-val" style="font-size:14px;padding-top:6px">{{ stat.terakhir }}</div></div>
  </div>

  <h2>Log Serangan Terbaru</h2>
  {% if logs %}
  <table>
    <thead><tr><th>#</th><th>Waktu</th><th>IP Penyerang</th><th>Protokol</th><th>Port</th><th>Payload</th></tr></thead>
    <tbody>
      {% for log in logs %}
      <tr>
        <td style="color:#555">{{ log.id }}</td>
        <td>{{ log.waktu }}</td>
        <td style="font-family:monospace;color:#f0b429">{{ log.ip }}</td>
        <td><span class="badge badge-{{ log.protokol | lower }}">{{ log.protokol }}</span></td>
        <td style="font-family:monospace">{{ log.port }}</td>
        <td style="color:#888;font-size:12px">{{ log.payload[:60] if log.payload else '-' }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <div class="empty">Belum ada serangan terdeteksi.<br>Menunggu koneksi dari ESP32 dan honeypot...</div>
  {% endif %}
</body>
</html>
"""

# ============================================
# ROUTES
# ============================================
@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/log', methods=['POST'])
def terima_log():
    data = request.get_json()
    if not data:
        return jsonify({"status": "error"}), 400

    data['waktu']   = datetime.now().strftime("%H:%M:%S")
    data['tanggal'] = datetime.now().strftime("%Y-%m-%d")

    simpan_log(data)
    print(f"[{data['waktu']}] ⚠ SERANGAN: {data['ip']} → port {data['port']} ({data['protokol']})")

    return jsonify({"status": "ok"})

@app.route('/')
def dashboard():
    init_db()
    logs = ambil_log(50)
    stat = ambil_statistik()
    return render_template_string(DASHBOARD_HTML, logs=logs, stat=stat)

@app.route('/api/logs')
def api_logs():
    logs = ambil_log(20)
    stat = ambil_statistik()
    return jsonify({"statistik": stat, "logs": logs})

# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

init_db()
