@echo off
REM Dijalankan oleh Windows Task Scheduler sekali sehari.
REM Sesuaikan path Python bila perlu (cek: where python).

cd /d "%~dp0"

REM --- kredensial: WAJIB isi FIRMS_MAP_KEY ---
set FIRMS_MAP_KEY=taruh_kunci_firms_di_sini
set GEE_PROJECT=latihan-481319
REM --- opsional: notifikasi ---
REM set DISCORD_WEBHOOK=https://discord.com/api/webhooks/xxx/yyy
REM set TELEGRAM_TOKEN=123:abc
REM set TELEGRAM_CHAT_ID=123456

python run.py >> data\run.log 2>&1
