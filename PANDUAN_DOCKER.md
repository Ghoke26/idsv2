# PANDUAN SETUP DOCKER DI VPS
## IDS ESP32 — Versi Docker

---

## STRUKTUR FOLDER

```
ids-docker/
├── docker-compose.yml       ← Orkestrasi semua container
├── server/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── server.py            ← Dashboard + API
└── honeypot/
    ├── Dockerfile
    ├── requirements.txt
    └── honeypot.py          ← Port tipuan IoT
```

---

## LANGKAH 1 — Install Docker di VPS

SSH ke VPS dulu:
```bash
ssh root@202.10.34.35
```

Install Docker:
```bash
curl -fsSL https://get.docker.com | sh
```

Install Docker Compose:
```bash
apt install docker-compose -y
```

Cek berhasil:
```bash
docker --version
docker-compose --version
```

---

## LANGKAH 2 — Upload File ke VPS

Di laptop, buka CMD di folder ids-docker lalu:
```bash
scp -r ids-docker root@202.10.34.35:/root/
```

Atau di VPS, clone dari GitHub:
```bash
git clone https://github.com/USERNAME_KAMU/ids-esp32-server.git
cd ids-esp32-server
```

---

## LANGKAH 3 — Buka Port di Firewall VPS

```bash
ufw allow 22      # SSH (jangan sampai terkunci!)
ufw allow 5000    # Dashboard web
ufw allow 1883    # MQTT honeypot
ufw allow 5683    # CoAP honeypot
ufw allow 23      # Telnet honeypot
ufw enable
ufw status
```

---

## LANGKAH 4 — Jalankan Docker Compose

```bash
cd /root/ids-docker
docker-compose up -d
```

Cek semua container jalan:
```bash
docker-compose ps
```

Harus muncul:
```
NAME            STATUS
ids-server      Up
ids-honeypot    Up
```

Lihat log:
```bash
docker-compose logs -f
```

---

## LANGKAH 5 — Test

Buka browser:
```
http://202.10.34.35:5000
```
Dashboard harus muncul.

Test honeypot dari laptop:
```bash
# MQTT
curl http://202.10.34.35:1883

# Telnet
telnet 202.10.34.35 23

# Port scan
nmap -p 1883,5683,23 202.10.34.35
```

---

## PERINTAH DOCKER BERGUNA

```bash
# Lihat semua container
docker-compose ps

# Lihat log real-time
docker-compose logs -f

# Restart semua
docker-compose restart

# Stop semua
docker-compose down

# Rebuild setelah ada perubahan kode
docker-compose up -d --build

# Masuk ke dalam container
docker exec -it ids-server bash
docker exec -it ids-honeypot bash

# Lihat database SQLite
docker exec -it ids-server sqlite3 /app/data/ids.db "SELECT * FROM serangan ORDER BY id DESC LIMIT 10;"
```

---

## UPDATE FIRMWARE ESP32

Setelah Docker jalan di VPS, update SERVER_URL di ids_esp32.ino:
```cpp
const char* SERVER_URL = "http://202.10.34.35:5000/log";
```
Upload ulang ke ESP32 (Ctrl+U di Arduino IDE).

---

## CATATAN

- Database SQLite tersimpan di Docker volume — tidak hilang walau container restart
- Dashboard auto-refresh setiap 5 detik
- Semua log serangan tersimpan permanen di /app/data/ids.db
- VPS jatuh tempo: 2026-06-18 — ingat perpanjang!
