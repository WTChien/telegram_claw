# nanoclaw

統一的本機服務控制系統，提供三種互動通道：
- Web 儀表板
- Telegram Bot
- REST API

## 功能特色

- 依據已知本機端口進行動態服務掃描
- 一鍵連接任意正在運行的本機服務
- 將 HTTP 請求代理轉發到目前選擇的服務
- 依使用者儲存服務偏好
- FastAPI 文件位於 /docs

## 專案結構

- backend/: FastAPI 後端、服務掃描、代理轉發與 API
- frontend/: 原生 JavaScript 儀表板
- telegram_bot/: Telegram 指令處理
- tests/: pytest 測試套件
- config/: 已知服務定義

## 快速開始

1. 建立並啟用虛擬環境
2. 安裝相依套件
3. 複製環境變數範本並調整設定值
4. 執行啟動腳本

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python start.py
```

開啟：
- Dashboard: http://localhost:8000
- API 文件: http://localhost:8000/docs

## API 概覽

服務管理：
- GET /api/services/list
- GET /api/services/scan
- POST /api/services/connect
- GET /api/services/current
- POST /api/services/proxy

使用者偏好：
- GET /api/services/user/preference
- POST /api/services/user/preference

聊天：
- POST /api/chat/message
- GET /api/chat/models

系統：
- GET /health

## Telegram Bot

在 .env 設定 TELEGRAM_BOT_TOKEN，然後執行：

```bash
python telegram_bot/bot.py
```

指令：
- /start
- /services
- /scan
- /current

## Docker

```bash
docker-compose up -d --build
```

## 開發指令

```bash
make dev
make test
make lint
make bot
```
