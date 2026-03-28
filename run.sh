#!/usr/bin/env bash

# 杀掉旧进程
pkill -f "streamlit run"
pkill -f "uvicorn"
pkill -f "ngrok"

# 1️⃣ 后端：FastAPI
nohup uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4 > api.log 2>&1 &

# 2️⃣ 前端：Streamlit
nohup streamlit run app.py --server.address 0.0.0.0 --server.port 6006 > streamlit.log 2>&1 &

echo "✅ FastAPI on :8000"
echo "✅ Streamlit on :6006"
