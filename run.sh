#!/bin/zsh
# nanoclaw 一鍵啟動腳本
# 依序啟動 FastAPI 後端 + Telegram Bot

cd "$(dirname "$0")"

# 啟用虛擬環境
source venv/bin/activate

echo "=============================="
echo "  nanoclaw 啟動中..."
echo "=============================="

# 啟動 FastAPI 後端（背景執行）
echo "[1/2] 啟動後端 API..."
python start.py &
API_PID=$!

# 等待後端就緒
sleep 2

# 確認後端是否成功啟動
if ! kill -0 $API_PID 2>/dev/null; then
    echo "❌ 後端啟動失敗，請檢查錯誤訊息"
    exit 1
fi

echo "✅ 後端已啟動 (http://localhost:8000)"
echo ""

# 啟動 Telegram Bot（前景執行，log 直接顯示）
echo "[2/2] 啟動 Telegram Bot..."
echo "=============================="

# 捕捉 Ctrl+C，關閉時一起停掉後端
trap "echo ''; echo '正在關閉...' ; kill $API_PID 2>/dev/null; exit 0" INT TERM

python -m telegram_bot.bot

# Bot 結束時也關閉後端
kill $API_PID 2>/dev/null
