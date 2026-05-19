"""
IDS ESP32 - Honeypot Container
Membuka port tipuan IoT: 1883 (MQTT), 5683 (CoAP), 23 (Telnet)
Setiap koneksi masuk dikirim ke server Flask untuk dianalisis ESP32
"""
import socket
import threading
import requests
import os
import json
from datetime import datetime

SERVER_URL = os.environ.get("SERVER_URL", "http://ids-server:5000/log")

# Counter koneksi per IP (untuk deteksi brute force)
ip_counter = {}

# ============================================
# KIRIM LOG KE SERVER
# ============================================
def kirim_log(ip, port, protokol, payload=""):
    # Update counter IP
    key = f"{ip}:{protokol}"
    ip_counter[key] = ip_counter.get(key, 0) + 1

    data = {
        "ip":       ip,
        "port":     port,
        "protokol": protokol,
        "payload":  payload[:200] if payload else "(kosong)",
        "total":    ip_counter[key],
        "waktu":    datetime.now().strftime("%H:%M:%S"),
        "tanggal":  datetime.now().strftime("%Y-%m-%d")
    }

    print(f"[{data['waktu']}] ⚠ {protokol} dari {ip}:{port} — percobaan ke-{data['total']}")

    try:
        requests.post(SERVER_URL, json=data, timeout=3)
    except Exception as e:
        print(f"Gagal kirim ke server: {e}")

# ============================================
# HANDLER PER KONEKSI
# ============================================
def handle_client(conn, addr, port, protokol, respon_palsu):
    ip = addr[0]
    try:
        # Baca payload (tunggu max 1 detik)
        conn.settimeout(1.0)
        payload = ""
        try:
            raw = conn.recv(512)
            payload = raw.decode('utf-8', errors='replace').strip()
        except:
            pass

        # Kirim respon palsu
        try:
            conn.send(respon_palsu)
        except:
            pass

        # Kirim log ke server
        kirim_log(ip, port, protokol, payload)

    except Exception as e:
        print(f"Error handle {protokol}: {e}")
    finally:
        conn.close()

# ============================================
# SERVER PER PORT
# ============================================
def jalankan_server(port, protokol, respon_palsu):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', port))
    server.listen(50)
    print(f"[*] Honeypot {protokol} aktif di port {port}")

    while True:
        try:
            conn, addr = server.accept()
            t = threading.Thread(
                target=handle_client,
                args=(conn, addr, port, protokol, respon_palsu),
                daemon=True
            )
            t.start()
        except Exception as e:
            print(f"Error accept {protokol}: {e}")

# ============================================
# RESPON PALSU PER PROTOKOL
# ============================================

# MQTT CONNACK palsu (berpura-pura terima koneksi)
MQTT_CONNACK = bytes([
    0x20, 0x02,  # CONNACK packet type + length
    0x00,        # Session present = 0
    0x00         # Return code = 0 (accepted)
])

# CoAP ACK palsu
COAP_ACK = bytes([
    0x60, 0x00, 0x00, 0x00  # ACK, empty response
])

# Telnet welcome palsu (berpura-pura jadi perangkat IoT)
TELNET_WELCOME = b"Welcome to IoT Device v1.0\r\nLogin: "

# ============================================
# MAIN — Jalankan semua port
# ============================================
if __name__ == '__main__':
    print("=================================")
    print("  IDS Honeypot Container")
    print("=================================")
    print(f"Server URL: {SERVER_URL}")
    print("=================================")

    configs = [
        (1883, "MQTT",   MQTT_CONNACK),
        (5683, "CoAP",   COAP_ACK),
        (23,   "Telnet", TELNET_WELCOME),
    ]

    threads = []
    for port, protokol, respon in configs:
        t = threading.Thread(
            target=jalankan_server,
            args=(port, protokol, respon),
            daemon=True
        )
        t.start()
        threads.append(t)

    print("\nSemua port honeypot aktif. Menunggu serangan...")
    print("Port 1883 → MQTT tipuan")
    print("Port 5683 → CoAP tipuan")
    print("Port 23   → Telnet tipuan")
    print("=================================")

    # Keep main thread hidup
    for t in threads:
        t.join()
