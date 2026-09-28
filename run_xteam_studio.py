import sys
import os
import multiprocessing
from pathlib import Path
import threading
import time
import subprocess
import webbrowser

# Freeze support for PyInstaller on Windows
multiprocessing.freeze_support()

# Reconfigure stdout/stderr encoding safely
if hasattr(sys, 'stdout') and sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

# Ensure base dir and MEIPASS are in sys.path
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(BASE_DIR))

import uvicorn
import requests
from app.main import app

PORT = 8001
HOST = "127.0.0.1"
APP_URL = f"http://{HOST}:{PORT}"

def start_backend():
    """Chạy FastAPI server trực tiếp bằng app instance (tương thích 100% với PyInstaller)"""
    try:
        uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
    except Exception as e:
        print("Backend error:", e)

def wait_for_server():
    """Đợi server sẵn sàng"""
    for _ in range(40):
        try:
            r = requests.get(f"{APP_URL}/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False

def open_app_window():
    """Mở cửa sổ ứng dụng độc lập mượt mà"""
    wait_for_server()
    
    # 1. Thử mở cửa sổ Native PyWebView
    try:
        import webview
        window = webview.create_window(
            title="Xteam Voice Studio — Chuyển văn bản thành giọng nói AI",
            url=APP_URL,
            width=1320,
            height=860,
            min_size=(960, 640),
            background_color="#022c22",
            text_select=True
        )
        webview.start(private_mode=False)
        return
    except Exception as e:
        pass

    # 2. Fallback: Mở dạng App Window qua MS Edge hoặc Google Chrome
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")
    ]
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
    ]
    
    for browser in edge_paths + chrome_paths:
        if os.path.exists(browser):
            try:
                proc = subprocess.Popen([browser, f"--app={APP_URL}", "--window-size=1320,860"])
                proc.wait()
                return
            except Exception:
                pass

    # 3. Fallback cuối: Mở trình duyệt mặc định
    webbrowser.open(APP_URL)
    # Giữ tiến trình chạy cho đến khi tắt
    while True:
        time.sleep(2)

if __name__ == "__main__":
    # Khởi chạy backend ở luồng riêng
    server_thread = threading.Thread(target=start_backend, daemon=True)
    server_thread.start()

    # Mở cửa sổ giao diện chính
    open_app_window()
    
    sys.exit(0)
