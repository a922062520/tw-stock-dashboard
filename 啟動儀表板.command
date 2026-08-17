#!/bin/bash
# 台股分析儀表板 - Mac 啟動器（雙擊此檔案即可）
cd "$(dirname "$0")"

if ! command -v python3 &> /dev/null; then
  echo "找不到 Python3，請先到 https://www.python.org/downloads/ 安裝後再試一次。"
  read -p "按 Enter 鍵結束..."
  exit 1
fi

if [ ! -d "venv" ]; then
  echo "第一次執行，正在建立環境（約需 1~2 分鐘，請耐心等候）..."
  python3 -m venv venv
  source venv/bin/activate
  pip install --upgrade pip -q
else
  source venv/bin/activate
fi

# 每次啟動都同步套件清單，確保程式更新後新增的套件也會補裝（已安裝的套件不會重複下載，很快）
pip install -r requirements.txt -q

echo "啟動中，瀏覽器將自動開啟儀表板..."
streamlit run app.py
