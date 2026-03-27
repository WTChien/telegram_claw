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
- 支援 macOS 多螢幕截圖
- /control 可將螢幕截圖送到本地 vision 模型分析
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
4. 啟動 API 或使用整合啟動腳本

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./run.sh
```

開啟：
- Dashboard: http://localhost:<API_PORT>
- API 文件: http://localhost:<API_PORT>/docs

如果只想啟動 API：

```bash
python start.py
```

如果只想啟動 Telegram Bot：

```bash
python -m telegram_bot.bot
```

## 環境變數

主要設定在 .env：

- API_HOST: FastAPI 綁定主機，預設為 0.0.0.0
- API_PORT: FastAPI 埠號，例如 8000 或 8080
- NANOCLAW_API_BASE: Telegram Bot 連到後端 API 的完整網址，例如 http://localhost:8080
- TELEGRAM_BOT_TOKEN: Telegram Bot token
- ADMIN_USER_ID: Telegram 管理員 user id；未設定時不限制管理命令
- KNOWN_SERVICES_JSON: 已知服務清單檔案，預設為 config/services.json
- OLLAMA_CONNECT_TIMEOUT: 連線到 Ollama 的 timeout（秒）
- OLLAMA_LIST_TIMEOUT: 讀取模型清單 timeout（秒）
- OLLAMA_CHAT_TIMEOUT: /ask 使用的 chat timeout（秒）
- OLLAMA_GENERATE_TIMEOUT: /control 使用的 generate timeout（秒）

注意：

- API_PORT 與 NANOCLAW_API_BASE 需要互相對齊
- docker-compose 會依 API_PORT 對應相同的 host/container port

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
python -m telegram_bot.bot
```

指令：
- /start
- /services
- /scan
- /current
- /screenshot
- /ask <問題>
- /control <指令>
- /run <shell 指令>
- /open <App名稱或網址>

### /screenshot

- 在 macOS 會依照顯示器數量分別擷取螢幕
- 每個螢幕會以 PNG 檔案分開傳送，避免 Telegram 壓縮圖片

### /control

- 會先截取目前螢幕，再將圖片送到本地 Ollama vision 模型分析
- 多螢幕環境下，會將各顯示器截圖一併送入模型
- 若模型不支援圖片或圖片 payload 過大，Ollama 可能回傳 500

建議使用支援視覺的模型，例如：

- qwen3.5
- llava
- llama3.2-vision

目前 /ask 與 /control 都是單次請求，預設不保存跨回合對話歷史。

## Docker

```bash
docker-compose up -d --build
```

如果 .env 內設定了 API_PORT=8080，容器也會對外暴露 8080。

## 開發指令

```bash
make dev
make test
make lint
make bot
```
