@echo off
REM 台股分析儀表板 - Windows 啟動器（雙擊此檔案即可）
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo 找不到 Python，請先到 https://www.python.org/downloads/ 安裝後再試一次。
  echo 安裝時記得勾選「Add python.exe to PATH」。
  pause
  exit /b 1
)

if not exist venv (
  echo 第一次執行，正在建立環境（約需 1~2 分鐘，請耐心等候）...
  python -m venv venv
  call venv\Scripts\activate.bat
  pip install --upgrade pip -q
) else (
  call venv\Scripts\activate.bat
)

REM 每次啟動都同步套件清單，確保程式更新後新增的套件也會補裝（已安裝的套件不會重複下載，很快）
pip install -r requirements.txt -q

echo 啟動中，瀏覽器將自動開啟儀表板...
streamlit run app.py
pause
