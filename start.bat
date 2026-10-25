@echo off
chcp 65001 >nul
title AudioScribe AI - Multi-Speaker Transcriber & Meeting Summary

echo =====================================================================
echo           AudioScribe AI - Chuyển Âm Thanh & Tóm Tắt Đa Người Nói
echo =====================================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Đang khởi tạo môi trường ảo Python (.venv)...
    python -m venv .venv
    echo [2/3] Đang cài đặt thư viện cần thiết...
    call .venv\Scripts\pip install -r requirements.txt
) else (
    echo [*] Môi trường ảo đã sẵn sàng.
)

echo [*] Đang khởi động máy chủ AudioScribe AI...
start "" "http://127.0.0.1:8000"

.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause
