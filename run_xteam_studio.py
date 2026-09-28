import sys
import os
import multiprocessing
import socket
from pathlib import Path
import threading
import time
import subprocess
import webbrowser

# Khởi tạo freeze_support cho PyInstaller trên Windows
multiprocessing.freeze_support()

# Xử lý an toàn luồng output console khi chạy ở chế độ no-window
if hasattr(sys, 'stdout') and sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

# Đảm bảo đường dẫn gốc chính xác trong môi trường PyInstaller MEIPASS
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(BASE_DIR))

import uvicorn
import requests
from app.main import app

def find_available_port(preferred_ports=[8001, 8080, 8088, 8888, 8000]):
    """Tìm cổng mạng khả dụng và an toàn nhất để tránh xung đột"""
    for port in preferred_ports + list(range(8002, 8050)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return 8080

HOST = "127.0.0.1"
PORT = find_available_port()
APP_URL = f"http://{HOST}:{PORT}"

server_instance = None

def start_backend():
    """Khởi chạy FastAPI Local TTS Backend với log_config=None (an toàn 100% trong PyInstaller windowed)"""
    global server_instance
    try:
        config = uvicorn.Config(
            app=app,
            host=HOST,
            port=PORT,
            log_config=None,
            loop="asyncio"
        )
        server_instance = uvicorn.Server(config)
        # Vô hiệu hóa signal handlers để uvicorn chạy ổn định trong background thread
        server_instance.install_signal_handlers = lambda: None
        server_instance.run()
    except Exception as e:
        try:
            with open("xteam_debug.log", "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Server error: {str(e)}\n")
        except Exception:
            pass

def wait_for_server(max_attempts=60):
    """Đợi backend khởi động và phản hồi mã 200 trước khi mở cửa sổ"""
    for _ in range(max_attempts):
        try:
            r = requests.get(f"{APP_URL}/health", timeout=1)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False

def open_app_window():
    """Mở giao diện ứng dụng dưới dạng cửa sổ Desktop độc lập"""
    # Đợi server sẵn sàng 100%
    is_ready = wait_for_server()
    if not is_ready:
        time.sleep(1)

    # 1. Mở dưới dạng App Window qua Microsoft Edge hoặc Google Chrome (Mượt mà nhất trên Windows)
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe")
    ]
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe")
    ]
    
    for browser in edge_paths + chrome_paths:
        if os.path.exists(browser):
            try:
                proc = subprocess.Popen([browser, f"--app={APP_URL}", "--window-size=1360,880"])
                proc.wait()
                return
            except Exception:
                pass

    # 2. Mở qua Native PyWebView nếu có
    try:
        import webview
        window = webview.create_window(
            title="Xteam Voice Studio — Chuyển văn bản thành giọng nói AI",
            url=APP_URL,
            width=1360,
            height=880,
            min_size=(960, 640),
            background_color="#022c22",
            text_select=True
        )
        webview.start(private_mode=False)
        return
    except Exception:
        pass

    # 3. Fallback: Mở trình duyệt mặc định của máy
    webbrowser.open(APP_URL)
    while True:
        time.sleep(3)

if __name__ == "__main__":
    # Khởi chạy backend ở background thread
    server_thread = threading.Thread(target=start_backend, daemon=True)
    server_thread.start()

    # Mở cửa sổ giao diện chính
    open_app_window()
    
    # Đóng server khi tắt cửa sổ
    if server_instance:
        server_instance.should_exit = True
        
    sys.exit(0)
