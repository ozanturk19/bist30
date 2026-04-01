#!/bin/bash
cd "$(dirname "$0")"
echo "Bağımlılıklar kontrol ediliyor..."
pip3 install -r requirements.txt -q
echo "Uygulama başlatılıyor → http://localhost:8003"
python3 app.py
