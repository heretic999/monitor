# Pemantau Anak Krakatau — sistem semi-real-time

Cek otomatis 1× sehari: tarik data satelit terbuka terbaru → hitung metrik & ambang →
tentukan status (NORMAL / WATCH / WARNING / ERUPTION) → kirim notifikasi saat status
berubah → perbarui dashboard HTML.

> **BUKAN peringatan resmi.** Sumber resmi: <https://magma.esdm.go.id> (PVMBG / Badan Geologi).
> Sistem ini pelengkap analisis pribadi, bukan pengganti pemantauan seismik/deformasi resmi.

## Cara kerja

| Sensor | Sumber | Latensi | Peran |
|---|---|---|---|
| Termal FRP | VIIRS via NASA FIRMS API | ~3 jam | metrik utama |
| SO₂ | TROPOMI/Sentinel-5P via Google Earth Engine | ~jam–hari | konfirmasi degassing |
| Status resmi | scrape MAGMA Indonesia (best-effort) | menit | ground-truth |

**Mesin status** (ambang dari analisis rekaman 2018–2026, lihat `../LAPORAN_Krakatau2026.md`):

| Status | Pemicu |
|---|---|
| NORMAL | rata-rata 30 hari FRP < 3 MW/hari **dan** SO₂ < 3 DU |
| WATCH | onset termal dari kondisi tenang (rata-rata 7 hari FRP > 5 MW setelah ≥21 hari tenang) **atau** tren SO₂ 60 hari > +0,5 DU/bulan (p < 0,05) |
| WARNING | rata-rata 7 hari FRP > 40 MW **dan** (tren FRP/SO₂ positif signifikan **atau** SO₂ rata-rata 30 hari > 6 DU) |
| ERUPTION | FRP harian > 300 MW **atau** hotspot > 50/hari **atau** status MAGMA naik |

De-eskalasi memakai histeresis: status hanya turun setelah 30 hari tenang beruntun.

## File

```
monitor/
├── config.py           ambang, path, area studi, kredensial (via env var)
├── metrics.py           compute_metrics() — fungsi murni
├── state_machine.py     next_state() — logika NORMAL/WATCH/WARNING/ERUPTION + histeresis
├── fetch_thermal.py     VIIRS FIRMS -> data/thermal.csv
├── fetch_so2.py         TROPOMI via GEE -> data/so2.csv
├── fetch_magma.py       status MAGMA (best-effort)
├── notify.py            Discord webhook / Telegram / dry-run (cetak layar)
├── dashboard.py         render dashboard.html (grafik base64 + tabel)
├── run.py               ORKESTRATOR — panggil ini
├── seed.py              isi data/*.csv dari ../firms_kontinu.csv & ../s5p_so2_kontinu.csv
├── tests/               pytest untuk metrics & state_machine
├── run_local.bat        wrapper untuk Windows Task Scheduler
└── data/                thermal.csv, so2.csv, state.json, run.log (dibuat saat jalan)
```

## Pemasangan

### 1. Dependensi
```
pip install -r requirements.txt
```

### 2. Kredensial (satu kali)
- **FIRMS MAP_KEY:** ambil di <https://firms.modaps.eosdis.nasa.gov/api/map_key/> (sudah ada default di `config.py`, ganti dengan milikmu bila mau).
- **Google Earth Engine:** `earthengine authenticate` (pakai akun Google), lalu set `GEE_PROJECT`.

### 3. Isi riwayat (satu kali)
```
python seed.py
```
Mengisi `data/thermal.csv` (3127 hari) dan `data/so2.csv` (2396 hari) dari hasil pemindaian kontinu. **Wajib** agar metrik rata-rata 30 hari & tren 60 hari punya konteks.

### 4. Uji & jalankan sekali
```
python -m pytest tests/ -q
python run.py
```
Tanpa webhook, notifikasi hanya dicetak ke layar (mode dry-run). Buka `dashboard.html` di browser.

## Menjadwalkan (pilih satu)

### A. Windows Task Scheduler (paling mudah — pakai auth GEE lokal)
1. Edit `run_local.bat`, isi baris `set DISCORD_WEBHOOK=...` bila mau notifikasi.
2. Task Scheduler → **Create Basic Task** → nama "Pemantau Krakatau" → **Daily**, jam 08:15 → **Start a program** → telusuri ke `run_local.bat` → selesai.
3. Cek `data\run.log` keesokan harinya.

### B. GitHub Actions (jalan walau PC mati)

Repo ini adalah repo standalone (`heretic999/monitor`); isi folder ini = akar repo.

1. Push isi folder ini ke repo:
   ```
   git add -A && git commit -m "monitor awal" && git push -u origin main
   ```
2. Repo → Settings → **Secrets and variables → Actions** → **New repository secret**:
   | Secret | Isi |
   |---|---|
   | `FIRMS_MAP_KEY` | kunci dari firms.modaps.eosdis.nasa.gov |
   | `GEE_PROJECT` | id project GEE (mis. `latihan-481319`) |
   | `EE_SERVICE_ACCOUNT_JSON` | **seluruh isi** file JSON *service account* GEE (lihat di bawah) |
   | `DISCORD_WEBHOOK` | *(opsional)* URL webhook Discord |
   | `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` | *(opsional)* |
3. **Service account GEE** (agar GEE jalan tanpa `earthengine authenticate` di CI):
   Google Cloud Console → project GEE-mu → **IAM & Admin → Service Accounts → Create** →
   beri peran *Earth Engine Resource Viewer* → **Keys → Add key → JSON** → unduh.
   Daftarkan email SA di <https://code.earthengine.google.com/register> (pilih "Register a Service Account")
   ATAU tambahkan email SA sebagai anggota project GEE-mu. Tempel seluruh isi JSON ke secret `EE_SERVICE_ACCOUNT_JSON`.
4. Settings → **Pages** → Source: **GitHub Actions**. Dashboard live akan tayang di
   `https://heretic999.github.io/monitor/` setelah run pertama.
5. Actions → "Pemantau Anak Krakatau" → **Run workflow** untuk uji langsung. Setelah itu jalan otomatis 08:15 WIB tiap hari.

## Notifikasi

**Discord (paling simpel):** Server → Settings → Integrations → Webhooks → New Webhook → salin URL → set `DISCORD_WEBHOOK`.

**Telegram:** chat dengan `@BotFather` → `/newbot` → salin token → set `TELEGRAM_TOKEN`. Kirim satu pesan ke bot-mu, lalu buka `https://api.telegram.org/bot<TOKEN>/getUpdates` untuk melihat `chat.id` → set `TELEGRAM_CHAT_ID`.

## Batasan penting

- **Buta terhadap kolaps sektor.** Metode ini tidak mendeteksi longsoran flank (kejadian 2018 senyap di termal/SO₂). Untuk itu perlu modul InSAR/deformasi (belum dibuat — Fase 6).
- **Prekursor hanya untuk gaya eskalasi berlarut.** Ledakan mendadak (spt April 2020) beralih dari NORMAL langsung ke ERUPTION tanpa WATCH/WARNING.
- **Celah data.** Awan tropis & jarak lintasan bisa membuat data tertinggal; sistem mengirim notifikasi "GAP" bila data > 3 hari.
- **n kecil.** Ambang dikalibrasi dari 5 episode / 1 prekursor jelas — perlakukan WATCH/WARNING sebagai "perhatikan", bukan kepastian.
