#!/bin/bash

# 切換到腳本所在的資料夾路徑
cd "$(dirname "$0")"

# 確保能讀取到 scrcpy 的環境變數
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH

# 在背景執行 scrcpy
scrcpy  --window-title=note --turn-screen-off --power-off-on-close --stay-awake 